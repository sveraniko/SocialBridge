# 60_deploy_runbook — Deploy + Ops (чтобы поднималось с первого раза)

## 0) Цель
Сделать так, чтобы SocialBridge:
- поднимался “из коробки” (baseline → alembic upgrade head → готово),
- имел предсказуемый dev/prod процесс,
- был дебажабельным: логи, health, smoke tests,
- не требовал шаманства с бубном и “а у меня на машине работало”.

---

## 1) Компоненты деплоя
### 1.1 Сервисы (docker-compose)
- `api` — FastAPI SocialBridge
- `db` — Postgres
- `redis` — опционально (rate-limit/cache)
- `proxy` — опционально (nginx/traefik/caddy) для TLS/headers

Минимальный прод: `api + db`.

---

## 2) Конфигурация (env)
### 2.1 Обязательные переменные
- `BASE_URL` — базовый URL shortlink (например `https://go.example.com`)
- `SIS_BOT_USERNAME` — username бота SIS (без @)
- `DATABASE_URL` — `postgresql+asyncpg://...`
- `ADMIN_TOKEN` — токен админки
- `MC_TOKEN` — токен ManyChat (если включаем проверку)
- `MC_TOKEN_REQUIRED` — `true|false` (в проде true)
- `LOG_LEVEL` — `INFO`

### 2.2 Рекомендуемые
- `STORE_TEXT_PREVIEW=false` (по умолчанию)
- `CLICK_LOG_IP=false` (по умолчанию)
- `RETENTION_INBOUND_DAYS=90`
- `RETENTION_CLICK_DAYS=365`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REDIS_URL=redis://redis:6379/0` (если используем Redis)

### 2.3 .env.example
В репо обязателен `.env.example` без секретов, только шаблоны.

---

## 3) Локальный запуск (dev)
### 3.1 Старт
```bash
docker compose up -d --build
```

### 3.2 Миграции (baseline)
```bash
docker compose exec api alembic upgrade head
```

### 3.3 Проверка
```bash
curl -sS http://localhost:8000/health
```

### 3.4 Smoke test resolve
```bash
curl -sS -X POST http://localhost:8000/v1/mc/resolve   -H 'Content-Type: application/json'   -d '{"channel":"ig","content_ref":"campaign:catalog","text":"hi","mc":{"contact_id":"1","flow_id":"F1","trigger":"test"}}'
```

### 3.5 Smoke test redirect
(если есть запись slug `catalog`)
```bash
curl -I http://localhost:8000/t/catalog
```

---

## 4) Baseline workflow (как мы любим)
В разработке допускается пересборка:

### 4.1 Полный reset (dev only)
⚠️ **Никогда в проде**

```bash
docker compose down -v
docker compose up -d --build
docker compose exec api alembic upgrade head
```

**Почему так:** schema всегда восстанавливается из baseline миграции.

---

## 5) Production deploy (типовой, без героизма)
### 5.1 Подход
- репо на сервере
- docker compose
- reverse proxy с TLS
- env в secrets/файле вне репо

### 5.2 Шаги (первый деплой)
1) Создать DNS `go.DOMAIN` → IP сервера
2) Настроить TLS (caddy/traefik/nginx + certbot)
3) Подготовить `.env` на сервере (не коммитить)
4) Запуск:
```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```
5) Проверки:
- `GET /health`
- `POST /v1/mc/resolve`
- `GET /t/catalog`

### 5.3 Обновление (релиз)
```bash
git pull
docker compose build api
docker compose up -d api
docker compose exec api alembic upgrade head
```

**Порядок важен:** сначала обновили код, затем миграции.  
Если миграция ломает код, то это уже проектная ошибка.

---

## 6) Reverse proxy (рекомендуется)
### 6.1 Зачем
- TLS
- rate-limit на уровне edge (опционально)
- security headers
- access logs

### 6.2 Минимальные требования
- проксировать `/:*` на `api:8000`
- preserve `X-Request-Id` (если есть)
- выставить timeouts разумные (5–10s)

---

## 7) Миграции: правила работы (prod)
### 7.1 Никогда
- не удалять volume БД в проде
- не “обнулять” схему

### 7.2 Всегда
- `alembic upgrade head` при каждом релизе
- если миграция тяжелая:
  - делать отдельно “expand → backfill → contract” (2–3 релиза)

### 7.3 Проверка перед релизом
На staging (или локально):
- поднять пустую БД → `upgrade head`
- поднять “старую” БД → прогнать миграции → прогнать тесты

---

## 8) Monitoring / Observability (минимальный набор)
### 8.1 Healthchecks
- `/health` должен быть быстрым и без DB запросов (liveness)
- опционально `/ready` который проверяет DB (readiness)

### 8.2 Логи
- структурированные (json)
- request_id обязательно
- уровни: INFO/ERROR

### 8.3 Метрики (по мере необходимости)
Минимум можно начать с логов, потом добавить Prometheus.

---

## 9) Ops задачи (регулярка)
### 9.1 Retention job (TTL)
Если не сделать — БД раздуется.

Опции реализации:
- cron на сервере (`docker compose exec api python -m app.jobs.retention`)
- apscheduler внутри контейнера (не лучший, но допустимо)
- отдельный container job

SQL:
- inbound: 90 дней
- click: 365 дней

### 9.2 Backup
Минимум для прод:
- ежедневный dump (`pg_dump`) или managed backups (DO managed PG)
- хранить 7–14 дней
- периодически проверять restore

---

## 10) Инциденты и диагностика (что смотреть первым)
### 10.1 “ManyChat не отправляет ссылку / пустая кнопка”
1) лог `resolve` — есть ли request?
2) ответ resolve содержит `url`?
3) ManyChat сохранил response.url в `sb_last_url`?
4) BASE_URL верный?

### 10.2 “Клик есть, но SIS не открывается”
1) `GET /t/{slug}` → какой Location?
2) `SIS_BOT_USERNAME` правильный?
3) `start_param` валиден и ≤ 64?
4) SIS реально понимает payload? (prod_ / LOOK_ / code)

### 10.3 “Сканят slug (много miss)”
1) включить rate-limit на /t/
2) смотреть `redirect_miss` count
3) при необходимости включить Cloudflare/WAF

### 10.4 “БД растет”
1) проверить retention job
2) добавить агрегации или уменьшить retention

---

## 11) Smoke checklist (боевой)
Перед “включить в прод”:
- [ ] `/health` OK
- [ ] `resolve` отдает url/start_param
- [ ] `t/{slug}` редиректит в Telegram
- [ ] `content_map` CRUD работает по админ токену
- [ ] логирование без PII
- [ ] токены включены
- [ ] retention job запланирован
- [ ] backup включен

---

## 12) Рекомендованный прод‑сетап (если делать красиво)
- Managed Postgres (DigitalOcean/AWS) + автоматические бэкапы
- SocialBridge API контейнер
- Caddy/Traefik как edge (TLS)
- Cloudflare перед `go.DOMAIN` (если начнут сканить)
- Redis только если нужен rate-limit/кеш

