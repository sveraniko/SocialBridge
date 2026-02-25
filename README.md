# SocialBridge
**ManyChat → Shortlink → SIS (Telegram) deeplink**

## 0) Зачем это
Мы автоматизируем воронку **«соцсети → продажа»** без ручных переписок:

- **Вход:** ManyChat (Instagram сейчас; TikTok — *если/когда доступно в регионе/аккаунте*)
- **Мозг:** SocialBridge (наши правила + маппинг контента на товар/лук + трекинг)
- **Выход:** ссылка на конкретный товар/лук/каталог в SIS через Telegram deeplink  
- **Плюс:** shortlink (красивый URL), аналитика кликов, идемпотентность входящих событий

**Принцип:** SIS не модифицируем. SocialBridge — отдельный сервис/репозиторий, чтобы не рисковать ядром магазина.

---

## 1) Важные ограничения и допущения (чтобы не жить в иллюзиях)
### 1.1 TikTok
Подключение TikTok через ManyChat зависит от:
- доступности интеграции в регионе,
- типа аккаунта (обычно нужен Business),
- правил TikTok/партнёра.

**Решение:** архитектура SocialBridge должна быть *канал-агностик*.  
Если TikTok не подключается — TikTok остаётся источником трафика через **bio link / закреп / shortlink**, а автоматика DM включится позже без переписывания сервиса.

### 1.2 Telegram deeplink
Telegram `start` параметр имеет ограничение **до 64 символов**.  
**Правило:** держим payload коротким (целимся в ≤ 50 символов) и в безопасном алфавите (`A-Za-z0-9_-`).

---

## 2) SIS deeplink: что поддерживается (факты из кода SIS)
### 2.1 Парсинг /start
SIS парсит параметр после `/start` (если пусто → открывается главная каталога).

### 2.2 Поддерживаемые payload (важно: коллизии)
**Зарезервированные префиксы (не использовать в наших ссылках):**
- `pfm_` — PayForMe (перехватывается первым)
- `ao_` — админ просмотр заказа
- `order_` — пользовательский заказ
- `key_` и `club_` — ключи доступа/клуб
- `prod_` — товар по ID (разрешено использовать, но осторожно)
- `LOOK_` — луки (разрешено использовать)

**Рекомендуемые payload для SocialBridge:**
- **Товар:** `{PRODUCT_CODE}` (без префикса) — это fallback SIS
- **Лук:** `LOOK_{CODE}` (uppercase `LOOK_`)
- **Каталог:** пустой параметр (`/start` без payload, или `start=` пустой)

**Товар по ID:** `prod_{id}` — только если реально нужен ID-шный путь.

### 2.3 Ограничения доступа к скрытым товарам
В SIS есть настройка `allow_open_hidden_product_by_deeplink` — это влияет на то, откроется ли скрытый товар по deeplink.  
**Решение:** SocialBridge не должен “пытаться умничать” и обходить это. Если товар скрыт — решает SIS.

### 2.4 Аналитика SIS
SIS уже проставляет `source="deeplink"` в событиях открытия карточек (луки/товары).  
**Важно:** поля `campaign` в SIS сейчас нет → кампании/источник мы трекаем в SocialBridge через `slug` shortlink-а.

---

## 3) Архитектура (в одну картинку, без философии)

```
[Social Network] ─┐
                  │ (trigger: comment/story/keyword)
                  ▼
             [ManyChat Flow]
                  │  (External Request)
                  ▼
           POST /v1/mc/resolve  ───────────────┐
                  │                             │
                  │ reply_text + shortlink       │
                  ▼                             │
         [ManyChat sends message]                │
                  │                             │
                  ▼                             │
          GET /t/{slug} (user click)             │
                  │  log click_event             │
                  ▼                             │
     302 → https://t.me/{SIS_BOT}?start={payload}│
                  │                             │
                  ▼                             │
                 [SIS]  (source="deeplink") ─────┘
```

**Ключевой принцип:** любая нестабильность соцсетей/партнёров не должна ломать SIS.

---

## 4) Каналы, триггеры, и как мы “находим” правильную ссылку
SocialBridge работает на основе **content_map**:

- **content_ref** — ссылка на контент или идентификатор триггера
  - пример: `ig:media:1789...`
  - пример: `ig:story:...`
  - пример: `mc:keyword:SIZE`
  - пример: `campaign:spring_drop_2026`
- **start_param** — SIS payload (код товара / `LOOK_` / пусто)
- **slug** — shortlink

### 4.1 Решение задачи “ответ на конкретный пост → конкретный товар”
В ManyChat для каждого поста/ключа заводится flow, который передаёт `content_ref` → SocialBridge отдаёт соответствующий `slug`.

**Это снимает ад:** не нужен парсинг текста, LLM, и прочая магия. Нужен маппинг.

---

## 5) Контракт API (v0)
### 5.1 Health
`GET /health` → `200 OK`

### 5.2 Resolve (ManyChat External Request)
`POST /v1/mc/resolve`

#### Input
Мы принимаем **любой JSON**, но рекомендуем слать такой минимум:

```json
{
  "channel": "ig",
  "content_ref": "ig:media:17890000000000000",
  "text": "хочу купить",
  "mc": {
    "contact_id": "123",
    "flow_id": "abc",
    "trigger": "comment_to_dm"
  }
}
```

#### Output (пример)
```json
{
  "reply_text": "Готово. Вот ссылка на товар 👇",
  "url": "https://go.DOMAIN/t/abc123",
  "start_param": "DRESS001",
  "tag": "ig:media:1789..."
}
```

### 5.3 Redirect (shortlink)
`GET /t/{slug}`
- пишет `click_event`
- делает `302` на Telegram deeplink

---

## 6) Fallback стратегия (железная)
Если `content_ref` не найден в `content_map`:

1) если `text` содержит явный payload:
   - `LOOK_XXXX` → используем
   - `prod_123` → используем
   - `CODE123` (валидный код) → используем
2) иначе → отдаём **каталог** (`/start` без payload), и в тексте просим выбрать товар/написать код

**Почему так:** не ломаем продажи из-за дырявого маппинга. Лучше отправить в каталог, чем молчать.

---

## 7) Data model (минимум, Postgres)
### 7.1 content_map
| field | type | note |
|---|---|---|
| id | uuid | pk |
| channel | text | `ig`, `tt`, `generic` |
| content_ref | text | уникально в рамках channel |
| start_param | text | SIS payload |
| slug | text | уникальный |
| is_active | bool | |
| meta | jsonb | произвольные поля (campaign, tags, etc.) |
| created_at / updated_at | timestamptz | |

**Indexes:**
- unique `(channel, content_ref)`
- unique `slug`
- index `(channel, is_active)`

### 7.2 inbound_events
| field | type | note |
|---|---|---|
| id | uuid | pk |
| channel | text | |
| payload_hash | text | sha256(raw_payload) |
| raw_payload | jsonb | |
| created_at | timestamptz | |

**Indexes:**
- unique `(channel, payload_hash)` (идемпотентность)

### 7.3 click_events
| field | type | note |
|---|---|---|
| id | uuid | pk |
| slug | text | |
| user_agent | text | optional |
| ip_hash | text | optional (если очень надо) |
| referer | text | optional |
| created_at | timestamptz | |

**GDPR-позиция:** по умолчанию **не хранить IP**. Если нужно антифрод/рейты — хранить `ip_hash` (sha256(ip + salt)).

---

## 8) Admin API (минимум)
Auth: `X-Admin-Token: ...`

- `GET  /v1/admin/content-map?channel=ig`
- `POST /v1/admin/content-map/upsert`
- `POST /v1/admin/content-map/import` (JSON/CSV)
- `POST /v1/admin/content-map/export`

### 8.1 Формат import JSON (рекомендуемый)
```json
[
  {
    "channel": "ig",
    "content_ref": "ig:media:17890000000000000",
    "start_param": "DRESS001",
    "slug": "dress001"
  },
  {
    "channel": "ig",
    "content_ref": "campaign:spring_drop_2026",
    "start_param": "LOOK_SPRING2026",
    "slug": "spring2026"
  }
]
```

---

## 9) Конфигурация (env)
Минимум:

- `BASE_URL=https://go.DOMAIN`
- `SIS_BOT_USERNAME=YourSISBot`
- `DATABASE_URL=postgresql+asyncpg://...`
- `ADMIN_TOKEN=...`
- `CLICK_LOG_IP=false` (default)
- `LOG_LEVEL=INFO`

---

## 10) Deploy / Runbook (v0)
### Docker Compose
`docker compose up -d --build`

### Migrations
`docker compose exec api alembic upgrade head`

### Smoke test
- `curl http://localhost:8000/health`
- `curl -X POST http://localhost:8000/v1/mc/resolve -H 'Content-Type: application/json' -d '{"channel":"ig","content_ref":"demo","text":"hi"}'`

---

## 11) KPI (чтобы понимать, работает ли это вообще)
- `inbound_events/day` по каналам
- `resolve_success_rate = resolved / inbound`
- `CTR = clicks / resolved`
- `top slugs by clicks`
- (будущее) `click_to_purchase` через SIS events/корреляцию по slug/campaign

---

## 12) Backlog (следующая итерация)
- HMAC подпись для входящих запросов ManyChat (если понадобится)
- Rate-limit по contact_id / ip_hash
- UI-админка (простая) вместо сырых endpoint-ов
- Экспорт отчётов по slug/campaign
- Интеграция “campaign” в SIS events (если решим трогать SIS, но это отдельный проект)
