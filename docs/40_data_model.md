# 40_data_model — Postgres schema, baseline + migrations

## 0) Цель
Спроектировать БД так, чтобы:
- **в разработке** можно было спокойно пересобирать проект “с нуля” (baseline),
- **в проде** не ломать живые данные (миграции Alembic),
- схема была **читаемой и профессиональной**: понятные имена, ограничения, индексы, история изменений.

Принцип: *в dev мы можем пересоздавать БД, в prod мы никогда не “обнуляем”*.

---

## 1) Стратегия baseline + migrations (наша “фишка”)

### 1.1 Baseline (v0)
**Baseline** = минимальный “слепок” схемы, которым можно поднять чистую БД.

Рекомендуемая реализация (проверенная и удобная):
- `alembic/versions/0001_baseline_init.py` — первая миграция, которая создаёт все таблицы
- при поднятии с нуля: `alembic upgrade head`
- в dev: допускается `docker compose down -v` → поднять заново → `alembic upgrade head`

Это уже baseline, но оформленный “правильно” через Alembic.

### 1.2 Миграции (после старта проекта)
Когда проект становится живым:
- **никогда не пересоздаём БД**
- делаем обычные Alembic миграции: `alembic revision --autogenerate -m "..."` → `alembic upgrade head`

### 1.3 Правила изменения схемы (чтобы данные не падали)
1) **Не удаляем колонку/таблицу** сразу. Сначала:
   - помечаем “deprecated”,
   - перестаём использовать,
   - через 1–2 релиза удаляем миграцией.
2) **Добавляем колонки безопасно**:
   - `NULL` допустим на 1 релиз,
   - потом backfill (скрипт/миграция),
   - потом `NOT NULL`.
3) **Меняем типы осторожно** (особенно `text → int`, `jsonb`).
4) **Индексы**: создаём осмысленно и по запросам, не “на всякий случай”.

---

## 2) Нейминг и стандарты

### 2.1 Имена таблиц
- Префикс `sb_` (SocialBridge): чтобы в общей БД было понятно, чьи это таблицы.
- `snake_case`.

Пример: `sb_content_map`, `sb_inbound_event`, `sb_click_event`.

### 2.2 Имена колонок
- `snake_case`
- время: `created_at`, `updated_at`
- идентификаторы: `..._id`

### 2.3 Времена и зоны
- только `timestamptz` (UTC)

### 2.4 PK и типы
- PK: `uuid` (генерация на стороне приложения или в Postgres)
- `jsonb` только там, где реально нужно расширение без миграций (`meta`)

---

## 3) Ограничения по payload/slug (Telegram + здравый смысл)
### 3.1 start_param
Telegram `start` ограничен 64 символами.

Рекомендуем:
- `start_param` **nullable**: `NULL` означает “каталог” (deeplink без параметра)
- `start_param` длина: `<= 64`
- символы: `A-Za-z0-9_-` (и только)
- если нужно хранить что-то “сложнее” — хранить в DB, а в `start_param` только короткий ключ.

### 3.2 slug
Slug используем как “публичный ключ” shortlink-а:
- храним **в lowercase**
- длина: `1..64` (лучше `<= 32`)
- символы: `a-z0-9_-`
- уникален глобально

> Для “красоты” можно включить проверку `slug = lower(slug)` (через CHECK).

---

## 4) Таблицы (MVP)

## 4.1 sb_content_map
**Назначение:** маппинг `content_ref → start_param → slug` (и статус активности).

### Поля
| field | type | constraints | note |
|---|---|---|---|
| id | uuid | PK | |
| channel | text | NOT NULL | `ig`, `tt`, `generic`, … |
| content_ref | text | NOT NULL | `campaign:dress001`, `mc:flow:F1`, … |
| start_param | text | NULL | `NULL` = каталог, иначе SIS payload |
| slug | text | NOT NULL | lowercase, уникальный |
| is_active | bool | NOT NULL DEFAULT true | мягкое выключение |
| meta | jsonb | NOT NULL DEFAULT '{}' | campaign/tags/notes |
| created_at | timestamptz | NOT NULL | |
| updated_at | timestamptz | NOT NULL | |

### Constraints
- `UNIQUE (channel, content_ref)`
- `UNIQUE (slug)`
- `CHECK (char_length(slug) BETWEEN 1 AND 64)`
- `CHECK (slug ~ '^[a-z0-9_-]+$')`
- `CHECK (slug = lower(slug))`
- `CHECK (start_param IS NULL OR char_length(start_param) <= 64)`
- `CHECK (start_param IS NULL OR start_param ~ '^[A-Za-z0-9_-]+$')`

### Индексы
- `(channel, is_active)` — быстрый фильтр по каналу
- `(updated_at)` — удобно для админки/экспорта

### Комментарий
**Почему `start_param NULL`:** это красиво и логично: отсутствие параметра = каталог. Не надо хранить пустые строки.

---

## 4.2 sb_inbound_event
**Назначение:** лог входящих запросов resolve (для диагностики и статистики), устойчивость к ретраям.

### Поля
| field | type | constraints | note |
|---|---|---|---|
| id | uuid | PK | |
| channel | text | NOT NULL | |
| payload_hash | char(64) | NOT NULL | sha256 canonical_json |
| content_ref | text | NULL | то, что пришло |
| mc_contact_id | text | NULL | диагностично |
| mc_flow_id | text | NULL | диагностично |
| mc_trigger | text | NULL | диагностично |
| text_preview | text | NULL | *обрезанный* текст (например, 256) |
| result | text | NOT NULL | `hit|fallback_payload|fallback_catalog|error` |
| resolved_slug | text | NULL | что отдали пользователю |
| resolved_start_param | text | NULL | |
| latency_ms | int | NULL | полезно |
| request_id | text | NULL | корреляция |
| payload_min | jsonb | NOT NULL DEFAULT '{}' | **санитизированное** подмножество |
| created_at | timestamptz | NOT NULL | |

### Constraints
- `UNIQUE (channel, payload_hash)` — идемпотентность (dedup)
- `CHECK (payload_hash ~ '^[0-9a-f]{64}$')`
- `CHECK (resolved_start_param IS NULL OR char_length(resolved_start_param) <= 64)`
- `CHECK (resolved_slug IS NULL OR resolved_slug ~ '^[a-z0-9_-]+$')`

### Индексы
- `(created_at DESC)` — быстрые просмотры логов
- `(channel, created_at DESC)`
- `(result, created_at DESC)`

### Комментарий по данным (GDPR)
- **Не хранить** сырой payload целиком (или хранить только маску).
- `payload_min` должен содержать минимум:
  - channel, content_ref, flow_id (если нужно), но без персональных “лишних” данных.
- `text_preview` ограничить по длине, без “романов”.

### Retention
Рекомендуем:
- `sb_inbound_event`: 30–90 дней (зависит от объёма), затем авто‑чистка.

---

## 4.3 sb_click_event
**Назначение:** клики по shortlink (основа KPI).

### Поля
| field | type | constraints | note |
|---|---|---|---|
| id | uuid | PK | |
| content_map_id | uuid | FK → sb_content_map(id) | nullable (если slug не найден) |
| slug | text | NOT NULL | тот, что в URL |
| user_agent | text | NULL | можно обрезать до 512 |
| ip_hash | char(64) | NULL | только если включили |
| referer | text | NULL | optional |
| meta | jsonb | NOT NULL DEFAULT '{}' | channel_guess, utm, etc. |
| created_at | timestamptz | NOT NULL | |

### Constraints
- `CHECK (slug ~ '^[a-z0-9_-]+$')`
- `CHECK (ip_hash IS NULL OR ip_hash ~ '^[0-9a-f]{64}$')`

### Индексы
- `(created_at DESC)`
- `(slug, created_at DESC)` — отчёты по slug
- `(content_map_id, created_at DESC)` — быстрый join

### Retention
- `sb_click_event`: 180–365 дней (в зависимости от трафика)
- если трафик большой: вводим агрегации (см. backlog ниже)

---

## 5) Опциональные таблицы (позже, если понадобится)
### 5.1 sb_daily_aggregate
Если кликов много, и таблица разрастается:
- ежедневные агрегации по `slug/channel/date`
- raw клики храним меньше, агрегаты дольше

### 5.2 sb_admin_audit
Если админка будет активно использоваться:
- кто и что менял в content_map (upsert/import/disable)
- удобно для контроля и отката

---

## 6) ERD (текстовая)
```
sb_content_map (1) ────< sb_click_event (many)
        │
        └─── (логически) используется в resolve → sb_inbound_event (many)
```
`sb_inbound_event` хранит результат resolve и ссылки на slug/start_param (без FK, чтобы лог был независимым).

---

## 7) Baseline: как “красиво” оформить в репозитории
Рекомендуем хранить:
- `alembic/versions/0001_baseline_init.py` — источник истины схемы
- `docs/40_data_model.md` — человеческое объяснение
- (опционально) `sql/baseline.sql` — **экспорт** схемы для “быстрого поднятия”, но не как единственный источник

### Почему Alembic baseline лучше чистого SQL
- единый механизм для baseline и миграций
- CI проще (поднять DB → прогнать миграции → тесты)
- меньше риска “SQL и модели разъехались”

---

## 8) Рекомендации по реализации (чтобы не разъехалось)
### 8.1 Обновление updated_at
- делаем на уровне приложения (SQLAlchemy events) или в repo (явно)
- без триггеров, пока не надо

### 8.2 Canonical JSON для payload_hash
- сортировка ключей
- без пробелов
- UTF-8
- одинаковая сериализация (иначе dedup не сработает)

### 8.3 Ограничение размеров
- `text_preview`: max 256–512
- `user_agent`: max 512
- `payload_min`: только нужные поля

---

## 9) Backlog по БД (когда будет прод и трафик)
1) TTL/Retention job (cron/apscheduler) для inbound/click events
2) Агрегации по дням/кампаниям
3) Нормализация campaign:
   - добавить `campaign` в `sb_content_map.meta` (уже есть)
   - опционально вынести в отдельное поле `campaign` (тогда миграция)
4) Внешний ключ `resolved_content_map_id` в inbound_event (если понадобится “строгая” связка)
