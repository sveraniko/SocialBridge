# 10_architecture — SocialBridge

## 1) Принцип №1: никаких “мега‑файлов”
Мы уже знаем, чем заканчивается “давай быстро в один файл, потом разнесём”: потом никогда не наступает, а рефакторинг становится отдельным проектом.

**Правила размера:**
- **API endpoint файл:** 50–120 LOC (макс. 200)
- **Service / use-case:** 80–200 LOC (макс. 300)
- **Repo / DB:** 80–200 LOC
- **Модели SQLAlchemy:** по таблицам, **1 файл = 1 таблица** (или 2–3 мелкие в одном, если логически едины)
- Любой файл **> 350 LOC** = красная лампа: делим по ответственности.

**Правило ответственности:** 1 файл = 1 смысловая единица (endpoint, use-case, repo, модель, утилита).

---

## 2) Высокоуровневая схема (канал‑агностик)
SocialBridge строится так, чтобы Instagram/TikTok/что‑угодно были **адаптерами**, а ядро логики не менялось.

```
             ┌──────────────────────────┐
             │        ManyChat           │
             │ (IG now, TT maybe later)  │
             └─────────────┬────────────┘
                           │ External Request
                           ▼
┌─────────────────────────────────────────────────────┐
│                    SocialBridge                      │
│                                                     │
│  API Layer        Use-cases         Persistence      │
│ (FastAPI)      (services)         (repos + DB)       │
│   │                 │                   │            │
│   ▼                 ▼                   ▼            │
│ normalize → resolve mapping → build shortlink → log  │
│                │                   │                 │
│                └───────┬───────────┘                 │
│                        ▼                              │
│                 shortlink redirect                    │
└────────────────────────┬─────────────────────────────┘
                         │ 302
                         ▼
                    Telegram → SIS
```

**Ключ:** API тонкий, логика в use-case, инфраструктура в адаптерах/репозиториях.

---

## 3) Слои и зависимости (железно)
### 3.1 Слои
1) **API layer** (`app/api/...`)
   - парсит HTTP
   - вызывает use-case
   - возвращает ответ
   - *не содержит бизнес-логики*

2) **Use-cases / services** (`app/services/...`)
   - решает: что отправить, куда редиректить, что логировать
   - принимает нормализованные входы, возвращает структурированные выходы
   - *не знает ничего про FastAPI*

3) **Domain** (`app/domain/...`)
   - типы/DTO/ошибки/валидаторы
   - чистые функции и правила

4) **Adapters** (`app/adapters/...`)
   - нормализаторы ManyChat payload
   - генератор Telegram deeplink / shortlink
   - (опц.) rate-limit/cache

5) **Persistence** (`app/db`, `app/repositories/...`)
   - SQLAlchemy модели
   - репозитории
   - миграции Alembic

### 3.2 Dependency rules
- `api` может импортировать `services`, `domain`
- `services` может импортировать `domain`, `repositories`, `adapters`
- `repositories` импортируют только `db`/`domain`
- `domain` **не импортирует ничего** из FastAPI/SQLAlchemy

Эта дисциплина экономит нервы: меняем инфраструктуру, не трогая ядро.

---

## 4) Рекомендованная структура проекта (папки и файлы)
```
socialbridge/
  README.md
  docs/
    00_overview.md
    10_architecture.md
    20_manychat.md
    30_api_contracts.md
    40_data_model.md
    60_deploy_runbook.md

  app/
    main.py                 # create_app(), lifespan
    api/
      v1/
        router.py           # include_router
        endpoints/
          health.py
          resolve.py
          redirect.py
          admin_content_map.py
    core/
      config.py             # pydantic-settings
      logging.py            # struct logging config
      security.py           # admin token, headers
      errors.py             # exception mapping
    domain/
      types.py              # ResolveInput/ResolveOutput, enums
      validators.py         # payload validation
      errors.py             # DomainError, NotFound, etc.
    adapters/
      manychat_normalizer.py
      deeplink.py           # build_tg_deeplink()
      shortlink.py          # build_shortlink_url()
      hashing.py            # sha256 helpers
      time.py               # utcnow helper
    services/
      resolve_service.py    # resolve() use-case
      redirect_service.py   # redirect() use-case
      admin_service.py      # upsert/import/export logic
    db/
      session.py            # async engine + sessionmaker
      base.py               # declarative base
      models/
        content_map.py
        inbound_event.py
        click_event.py
    repositories/
      content_map_repo.py
      inbound_event_repo.py
      click_event_repo.py
    utils/
      json.py               # safe json dumps
      strings.py            # slug sanitize, etc.

  alembic/
    env.py
    versions/
      0001_init.py

  docker-compose.yml
  Dockerfile
  .env.example
  pyproject.toml
```

**Почему так:** файлы маленькие, ответственность разделена, use-case тестируется без веба.

---

## 5) Потоки (golden path)
### 5.1 Resolve flow (ManyChat → ответ)
1) ManyChat вызывает `POST /v1/mc/resolve`
2) `manychat_normalizer` превращает “как попало” JSON в `ResolveInput`
3) `resolve_service.resolve(input)`:
   - пишет `inbound_event` (идемпотентно по `payload_hash`)
   - пытается найти `content_map` по `(channel, content_ref)`
   - если нет — fallback (попытка извлечь payload из текста → иначе каталог)
   - формирует `ResolveOutput {reply_text, slug/url, start_param, tag}`
4) API возвращает JSON в ManyChat

**Идемпотентность:** если ManyChat ретраит тот же payload → мы не плодим события и не ломаем статистику.

### 5.2 Redirect flow (клик → SIS)
1) Пользователь кликает `https://go.DOMAIN/t/{slug}`
2) `redirect_service.redirect(slug)`:
   - ищет slug → start_param
   - пишет click_event
   - возвращает 302 на `https://t.me/{SIS_BOT}?start={start_param}`

---

## 6) Маппинг контента: как не превратить в ад
### 6.1 content_ref как “универсальный ключ”
Не привязываемся к “реальному” IG media_id/TT id, если это мешает.
Можно вводить уровень абстракции:

- `ig:media:<id>` — когда ID доступен
- `mc:flow:<flow_id>` — когда проще привязать к конкретному flow
- `campaign:<name>` — когда один flow ведёт на одну кампанию
- `keyword:<word>` — keyword-based

**Рекомендация:** начать с `mc:flow:<id>` или `campaign:<name>`, чтобы не бегать за айдишниками постов.

### 6.2 Slug стратегия
Slug должен быть:
- короткий (до 32 символов)
- читаемый (для ручной диагностики)
- уникальный

Например: `dress001`, `look_spring26`, `catalog`.

---

## 7) Observability (без лишней болтовни, но достаточно)
### 7.1 Логи (структурированные)
- request_id / trace_id
- endpoint
- channel
- content_ref (с маскированием, если надо)
- slug
- result: hit/miss/fallback
- latency_ms

**Запрещено:** писать в лог сырой payload ManyChat целиком (особенно если там есть персональные данные).

### 7.2 Метрики (минимум)
- resolve_total{channel, result}
- redirect_total{slug}
- db_errors_total
- latency_ms buckets (resolve, redirect)

Можно начать без Prometheus, но как минимум подготовить точки.

---

## 8) Security и GDPR (минимум боли)
- Админка только по `X-Admin-Token`.
- inbound_events хранить как jsonb можно, но:
  - либо делать редактирование/маскирование,
  - либо хранить только нормализованное подмножество полей.
- IP не хранить. Если нужен антифрод — `ip_hash` + соль + короткий retention.

---

## 9) Производительность и устойчивость
- `resolve` должен быть быстрым: 1–2 DB запроса + запись inbound_event.
- `redirect` должен быть сверхбыстрым: lookup slug + click insert + 302.
- Redis (опционально):
  - кеш `slug → start_param` на 5–30 минут
  - rate-limit по contact_id

---

## 10) Тестируемость (почему модульность важна)
- Use-case тестируется без HTTP: подставляем fake repos.
- API тестируется “тонко”: проверяем контракт и коды ответов.
- Golden-path e2e можно поднять через docker-compose и прогнать curl.

---

## 11) Анти‑паттерны (не делаем)
- “GodService” который и парсит JSON, и ходит в БД, и формирует ответ, и пишет логи.
- “Один models.py на все таблицы” (вырастет и будет больно).
- “Сложные зависимости между модулями” (api → db напрямую).
- “Сырые payload в логах” (GDPR и просто стыдно).

---

## 12) Срез MVP (что точно должно быть в v0)
- Структура модулей как выше
- Resolve + Redirect
- content_map CRUD + import/export
- Идемпотентность inbound_events
- Docker + migrations + smoke tests
