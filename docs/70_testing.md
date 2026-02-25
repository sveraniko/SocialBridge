# 70_testing — Тестирование (чтобы “работает” ≠ “кажется работает”)

## 0) Цель
Тесты в этом проекте нужны не ради ритуалов, а чтобы:
- не ломать resolve/redirect при мелких правках,
- гарантировать стабильный контракт ManyChat ↔ SocialBridge,
- не раздувать проект “как SIS”, но и не быть студентами “без тестов”.

Принцип: **маленький набор, но железный** (unit + интеграционные smoke).

---

## 1) Что тестируем в MVP (обязательное)
### 1.1 Resolve (核心)
- `hit`: есть запись в content_map → вернули правильный slug/url/start_param
- `fallback_payload`: нет записи, но в `text` есть валидный payload → вернули payload
- `fallback_catalog`: нет записи, нет payload → вернули каталог
- безопасность: неверный `X-MC-Token` → `403` (если включено)
- идемпотентность: одинаковый payload два раза → 1 запись inbound_event (или conflict), но оба раза 200 OK

### 1.2 Redirect
- slug найден → 302 и правильный Location
- slug не найден → (по выбранной политике) 302 на каталог или 404
- click_event создается (или логируется miss)

### 1.3 Admin content_map (минимум)
- upsert create
- upsert update
- import partial success (не валится весь пакет)
- export

---

## 2) Уровни тестов (строго)
### 2.1 Unit tests (быстрые)
**Цель:** тестировать use-cases без HTTP, без реальной БД.

Проверяем:
- `resolve_service.resolve()` на разных входах
- `redirect_service.redirect()`
- валидаторы slug/start_param
- canonical_json + hash

**Как:**
- fake/in-memory repos
- фиксированные данные

### 2.2 Integration tests (реальная БД)
**Цель:** проверить, что SQLAlchemy + Alembic + репозитории живые.

Проверяем:
- миграции поднимают схему
- CRUD работает
- unique constraints работают (slug, channel+content_ref)
- идемпотентность inbound_event (unique on hash)

### 2.3 API contract tests (через TestClient)
**Цель:** убедиться, что эндпоинты и формат ответа не поплыли.

Проверяем:
- `/health` 200
- `/v1/mc/resolve` возвращает JSON со всеми полями
- `/t/{slug}` возвращает 302

---

## 3) Инструменты и конфигурация
### 3.1 pytest
- `pytest` как основной фреймворк
- `pytest-asyncio` для async
- `httpx` или FastAPI TestClient для API тестов

### 3.2 Структура тестов
```
tests/
  unit/
    test_validators.py
    test_hashing.py
    test_resolve_service.py
    test_redirect_service.py
  integration/
    test_migrations.py
    test_repos_content_map.py
    test_repos_events.py
  api/
    test_health.py
    test_resolve_endpoint.py
    test_redirect_endpoint.py
    test_admin_endpoints.py
```

### 3.3 Важные правила
- unit тесты не ходят в сеть и не требуют Postgres
- integration тесты используют отдельную тестовую БД/контейнер
- тесты независимы: каждый тест сам готовит данные

---

## 4) Тестовые данные (fixtures)
### 4.1 Базовые fixtures
- `settings` — конфиг для тестов (in-memory или test DB)
- `db_session` — async session для интеграционных тестов
- `content_map_catalog` — запись `campaign:catalog` → `slug=catalog`, `start_param=NULL`
- `content_map_dress001` — `campaign:dress001` → `slug=dress001`, `start_param=DRESS001`

### 4.2 Фикстуры для resolve payload
- `payload_hit`
- `payload_fallback_payload`
- `payload_fallback_catalog`
- `payload_invalid_channel`
- `payload_long_start_param`

---

## 5) Golden cases (обязательные сценарии)
### 5.1 Resolve hit
**Given:** content_map has `(ig, campaign:dress001)`  
**When:** POST /v1/mc/resolve with that content_ref  
**Then:**
- `result == "hit"`
- `slug == "dress001"`
- `start_param == "DRESS001"`
- `url == BASE_URL + "/t/dress001"`

### 5.2 Resolve fallback_payload
**Given:** content_ref miss  
**When:** text contains `LOOK_SPRING2026`  
**Then:**
- `result == "fallback_payload"`
- `start_param == "LOOK_SPRING2026"`
- `slug` может быть `catalog` или `generated` (зависит от решения), но url должен вести в /t/...

**Рекомендация реализации:** в fallback_payload лучше отдавать **прямой deeplink** через shortlink “dynamic” (см. ниже).

### 5.3 Resolve fallback_catalog
**Given:** content_ref miss, text empty  
**Then:**
- `result == "fallback_catalog"`
- `start_param == null`
- `url == BASE_URL + "/t/catalog"`

### 5.4 Redirect found
**When:** GET /t/dress001  
**Then:**
- 302
- Location `https://t.me/{SIS_BOT_USERNAME}?start=DRESS001`

### 5.5 Redirect miss
**When:** GET /t/unknown  
**Then:** (по политике)
- 302 to catalog OR 404
- фиксируется `redirect_miss` (лог/метрика)

### 5.6 Dedup inbound event
**When:** одинаковый payload дважды  
**Then:**
- в sb_inbound_event только 1 запись по (channel, payload_hash)
- оба ответа 200 OK

---

## 6) Важный нюанс: “dynamic shortlinks” (если захотим)
Иногда fallback_payload (payload из текста) не должен требовать записи в content_map.

Варианты:
1) **Не делать dynamic:** просто отправлять каталог. (самый простой)
2) **Dynamic slug:** например `/t/_/LOOK_SPRING2026`  
   - тогда таблица content_map не нужна
   - но появляется риск сканирования payload
   - потребуются строгие валидаторы

Если используем dynamic:
- тестируем валидаторы символов/длины
- тестируем, что `/_/` формат не пересекается с обычными slug

**MVP рекомендация:** без dynamic. Только content_map + каталог. Потом добавим.

---

## 7) Тестирование миграций (baseline)
### 7.1 test_migrations.py
Сценарий:
1) поднять пустую БД
2) `alembic upgrade head`
3) проверить что таблицы существуют
4) проверить индексы/constraints (минимально)

Это ловит ситуацию “код есть, миграции забыли/сломали”.

---

## 8) CI (минимум)
Если есть GitHub Actions:
- шаг: поднять postgres service container
- шаг: установить deps
- шаг: `alembic upgrade head`
- шаг: `pytest -q`

**Идея:** любые PR не сливаются без green.

---

## 9) Coverage (без фетиша, но адекватно)
Цель для MVP:
- 70%+ на `services/` и `domain/`
- покрытие endpoints можно ниже, но ключевые сценарии должны быть.

---

## 10) Smoke tests для прод (ручные, но обязательные)
Перед включением ManyChat flows:
1) `GET /health`
2) `POST /v1/mc/resolve` на `campaign:catalog`
3) `GET /t/catalog` → редирект в Telegram
4) `upsert` test mapping → `resolve` hit → `t/{slug}`

Это занимает 2 минуты и экономит часы паники.

---

## 11) Чек-лист “тесты не превращаем в SIS”
- тестируем только то, что может сломаться и ударит по продажам
- не пишем 500 тестов на “форматирование строк”
- держим тесты быстрыми
- unit тесты максимально без инфраструктуры

