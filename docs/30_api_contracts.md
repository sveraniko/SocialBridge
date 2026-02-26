# 30_api_contracts — API контракты SocialBridge (v1)

## 0) Цель
Зафиксировать **строгий, проверяемый контракт** между:
- ManyChat → SocialBridge (resolve)
- Пользователь → SocialBridge (shortlink redirect)
- Админ → SocialBridge (content_map CRUD/import/export)

Это уменьшает “магические” зависимости и делает интеграцию предсказуемой.

---

## 1) Общие правила API
### 1.1 Base URL
- Production: `https://go.DOMAIN` (пример)
- Local dev: `http://localhost:8000`

### 1.2 Versioning
Все API, кроме `/health` и `/t/{slug}`, имеют префикс:
- `/v1/...`

### 1.3 Content-Type
- Request: `Content-Type: application/json` (где применимо)
- Response: `application/json; charset=utf-8`

### 1.4 Корреляция запросов
Рекомендуемые заголовки:
- `X-Request-Id: <uuid>` — если не задан, сервис генерирует сам
- `X-Request-Source: manychat|manual|admin|...` — опционально

### 1.5 Тайминги (SLO)
- `POST /v1/mc/resolve`: p95 ≤ 200 ms (1–2 DB запроса)
- `GET /t/{slug}`: p95 ≤ 80 ms

---

## 2) Аутентификация и безопасность
### 2.1 ManyChat token (shared secret) — рекомендуем включить
- Header: `X-MC-Token: <secret>`
- Проверяется на `/v1/mc/*` (минимум на resolve)
- При неверном токене: `403`

> Зачем: чтобы любой “левый” клиент не мог спамить тебе resolve и жечь БД.

### 2.2 Admin token (обязательно)
- Header: `X-Admin-Token: <secret>`
- Проверяется на `/v1/admin/*`
- При неверном токене: `403`

### 2.3 HTTPS
Production только через HTTPS.

---

## 3) Идемпотентность и дедупликация
ManyChat и другие системы любят ретраи. Мы должны:
- не плодить события,
- не ломать статистику,
- быть устойчивыми к повторной доставке.

### 3.1 inbound_events dedup
Сервис вычисляет `payload_hash = sha256(canonical_json(raw_payload))`
и вставляет в `inbound_events` с уникальным индексом:
- `(channel, payload_hash)`

Поведение:
- если insert OK → считаем событие “новым”
- если conflict → считаем событие “повторным”, но **ответ resolve всё равно возвращаем**

> Клиенту не нужно знать, было это повтором или нет. Мы просто стабильно отвечаем.

---

## 4) Endpoint: Health
### 4.1 GET /health
**Назначение:** liveness/readiness минимум.

**Request:** нет

**Response 200:**
```json
{
  "status": "ok",
  "service": "socialbridge",
  "version": "v1"
}
```

---

## 5) Endpoint: Resolve (ManyChat External Request)
### 5.1 POST /v1/mc/resolve
**Назначение:** получить **текст + shortlink** на основе `content_ref`/текста/контекста.

#### 5.1.1 Headers
- `Content-Type: application/json`
- `X-MC-Token: ...` (если включено)
- `X-Request-Id: ...` (опционально)

#### 5.1.2 Request body (tolerant)
Мы принимаем любой JSON, но контракт рекомендует минимум:

```json
{
  "channel": "ig",
  "content_ref": "campaign:dress001",
  "text": "хочу купить",
  "mc": {
    "contact_id": "123",
    "flow_id": "F_abc",
    "trigger": "comment_to_dm"
  },
  "meta": {
    "locale": "uk",
    "source_post_url": "https://..."
  }
}
```

#### 5.1.3 Поля (семантика)
- `channel` *(string, required)*: `ig|tt|generic|...`
- `content_ref` *(string, optional)*: универсальный ключ (см. docs/20_manychat.md)
- `text` *(string, optional)*: пользовательский текст/комментарий
- `mc` *(object, optional)*: диагностический блок (contact/flow/trigger)
- `meta` *(object, optional)*: любые доп. поля

**Валидация:**
- `channel` обязателен; если нет → `400`
- Если `content_ref` пустой и `text` пустой → fallback на каталог (200 OK)

#### 5.1.4 Response 200 (основной)
```json
{
  "reply_text": "Готово. Вот ссылка 👇",
  "url": "https://go.DOMAIN/t/dress001",
  "start_param": "DRESS001",
  "slug": "dress001",
  "tag": "ig|campaign:dress001",
  "result": "hit"
}
```

`result`:
- `hit` — найдено по content_map
- `fallback_payload` — извлекли start_param из текста
- `fallback_catalog` — отправили в каталог

Операционный guardrail: при превышении дневного лимита на динамические маппинги (`DYNAMIC_MAPPING_MAX_PER_DAY`) сервис деградирует в `fallback_catalog` для новых payload-only запросов.

#### 5.1.5 Ошибки
- `400 Bad Request`
  - нет `channel` или некорректный тип
- `403 Forbidden`
  - неверный `X-MC-Token`
- `500 Internal Server Error`
  - неожиданная ошибка

**Единый формат ошибок:**
```json
{
  "error": {
    "code": "bad_request",
    "message": "channel is required",
    "request_id": "...."
  }
}
```

---

## 6) Endpoint: Shortlink redirect
### 6.1 GET /t/{slug}
**Назначение:** записать клик и редиректнуть в SIS через Telegram deeplink.

#### 6.1.1 Path params
- `slug` *(string, required)*: shortlink slug

#### 6.1.2 Behavior
1) найти `slug → start_param` (только активные записи)
2) вставить `click_event`
3) вернуть `302` на:
`https://t.me/{SIS_BOT_USERNAME}?start={start_param}`

#### 6.1.3 Response
- `302 Found` + Header `Location: ...`

#### 6.1.4 Not found
Если slug не найден или неактивен:
- вариант A (строгий): `404 Not Found`
- вариант B (продажный): `302` на каталог

**Рекомендация:** в v0 сделать **вариант B** (всегда куда‑то ведём), но логировать `redirect_miss`.

Если делаем вариант B:
- `302 Location: https://t.me/{SIS_BOT_USERNAME}` (без start)

---

## 7) Admin API (token)
### 7.1 Общие правила
- Все admin endpoints: `/v1/admin/*`
- Header: `X-Admin-Token` обязателен
- Content-Type: json (кроме возможного CSV)
- Ошибки в едином формате (см. выше)

---

## 8) Endpoint: List content_map
### 8.1 GET /v1/admin/content-map
**Query params:**
- `channel` (optional)
- `is_active` (optional, default true)
- `limit` (optional, default 200, max 1000)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "channel": "ig",
      "content_ref": "campaign:dress001",
      "start_param": "DRESS001",
      "slug": "dress001",
      "is_active": true,
      "meta": {"campaign": "dress001"},
      "created_at": "2026-02-26T00:00:00Z",
      "updated_at": "2026-02-26T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 200,
  "offset": 0
}
```

---

## 9) Endpoint: Upsert content_map
### 9.1 POST /v1/admin/content-map/upsert
**Назначение:** создать или обновить запись по `(channel, content_ref)`.

**Request:**
```json
{
  "channel": "ig",
  "content_ref": "campaign:dress001",
  "start_param": "DRESS001",
  "slug": "dress001",
  "is_active": true,
  "meta": {"campaign": "dress001"}
}
```

**Валидация:**
- `channel` required
- `content_ref` required
- `start_param` может быть пустым только для каталога (если выбран такой режим)
- `slug` required (или генерируется автоматически сервером, если разрешим режим auto-slug)

**Response 200:**
```json
{
  "item": { "...fields..." },
  "result": "created|updated"
}
```

**Ошибки:**
- `409 Conflict` — slug уже занят другой записью

---

## 10) Endpoint: Import content_map
### 10.1 POST /v1/admin/content-map/import
**Назначение:** массовая загрузка маппинга.

**Request (JSON array):**
```json
[
  {"channel":"ig","content_ref":"campaign:dress001","start_param":"DRESS001","slug":"dress001"},
  {"channel":"ig","content_ref":"campaign:catalog","start_param":"","slug":"catalog"}
]
```

**Response 200:**
```json
{
  "created": 10,
  "updated": 2,
  "failed": 1,
  "errors": [
    {"index": 12, "code": "invalid_slug", "message": "slug too long"}
  ]
}
```

**Правило:** импорт *частично успешен* (не валим весь батч из‑за одной плохой строки).

---

## 11) Endpoint: Export content_map
### 11.1 GET /v1/admin/content-map/export
**Query params:**
- `channel` (optional)
- `is_active` (optional)

**Response 200:** JSON array (как в import)

---

## 12) Endpoint: Disable content_map (мягкое выключение)
### 12.1 POST /v1/admin/content-map/disable
**Request:**
```json
{
  "channel": "ig",
  "content_ref": "campaign:dress001"
}
```

**Response 200:**
```json
{"result":"disabled"}
```

---

## 13) Нормализация и fallback: формальная логика resolve
### 13.1 Порядок
1) `content_ref` → lookup content_map
2) если miss:
   - попытка извлечь start_param из `text`:
     - `LOOK_...`
     - `prod_...`
     - “похоже на PRODUCT_CODE” (валидатором)
3) если снова miss → каталог

### 13.2 Валидация start_param
**Разрешённые символы:** `A-Za-z0-9_-`  
**Макс длина:** 64 (лучше ≤ 50)

Если пришёл start_param с плохими символами → fallback на каталог и `result="fallback_catalog"`.

---

## 14) Совместимость и расширение
### 14.1 Новые поля в request/response
Разрешены: клиент должен игнорировать неизвестные поля.

### 14.2 Новые каналы
Добавление канала = новый `channel` + новые `content_ref` типы, ядро не меняется.

---

## 15) Примеры (готовые для копипаста)

### 15.1 resolve — hit
```bash
curl -sS -X POST http://localhost:8000/v1/mc/resolve   -H 'Content-Type: application/json'   -H 'X-MC-Token: dev'   -d '{"channel":"ig","content_ref":"campaign:dress001","text":"хочу","mc":{"contact_id":"1","flow_id":"F1","trigger":"test"}}'
```

### 15.2 resolve — fallback catalog
```bash
curl -sS -X POST http://localhost:8000/v1/mc/resolve   -H 'Content-Type: application/json'   -d '{"channel":"ig"}'
```

### 15.3 redirect
```bash
curl -I http://localhost:8000/t/dress001
```

---

## 16) Примечания для реализации (чтобы не разъехалось)
- canonical_json для hash: сортировка ключей, без пробелов, UTF-8
- error format всегда один
- redirect miss логировать как отдельный счетчик/метрика
- admin import делать транзакционно по строкам (savepoint), чтобы частично продолжать

