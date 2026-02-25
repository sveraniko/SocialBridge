# 50_security_gdpr — Security + GDPR (минимум риска, максимум практики)

## 0) Зачем это
SocialBridge находится на стыке:
- внешних платформ (ManyChat, соцсети),
- публичных ссылок (shortlink),
- Telegram deeplink в SIS,
- логирования событий.

Это классическое место, где “чуть-чуть поленились” → потом:
- спам и DDOS на `/resolve`,
- утечки персональных данных (PII),
- GDPR-паника,
- блокировка домена/аккаунтов.

Цель: **разумная безопасность**, без паранойи, но и без студенческих “и так сойдёт”.

---

## 1) Угрозы и модель риска (коротко)
### 1.1 Основные угрозы
1) **Public endpoint abuse**
   - злоумышленник дергает `/v1/mc/resolve` и жжёт БД/CPU
2) **Shortlink scanning**
   - перебор `slug` (dictionary attack)
3) **PII leakage**
   - сырые payload ManyChat/соцсетей попадают в логи/БД
4) **Admin takeover**
   - утечка токена админки → подмена маппинга → “клиентам улетает не то”
5) **Supply chain**
   - утечки секретов через репо/.env/CI

### 1.2 Контрольные меры (high-level)
- токены на resolve/admin
- rate-limit и анти-скан коротких ссылок
- минимизация хранения данных (data minimization)
- retention (TTL)
- безопасные логи
- секреты только через env/secret store

---

## 2) Аутентификация и доступ
### 2.1 ManyChat shared secret
**Зачем:** “чужие” клиенты не должны дергать resolve.

- Header: `X-MC-Token: <secret>`
- Проверка: только на `/v1/mc/*`
- Ответ при fail: `403`

**Правило:** token меняем при компрометации (rotation).  
**Dev:** можно отключить через `MC_TOKEN_REQUIRED=false`, но в проде — всегда true.

### 2.2 Admin token (обязательно)
- Header: `X-Admin-Token: <secret>`
- Только на `/v1/admin/*`
- Ответ при fail: `403`

**Жёсткая дисциплина:**
- отдельный токен, не пересекается с MC
- достаточно длинный (32+ символов), случайный
- не хранить в README/чатах

### 2.3 IP allowlist (опционально)
Если админка используется редко:
- можно ограничить `/v1/admin/*` по IP (например, только сервер/твоя сеть).

---

## 3) Rate limiting и анти‑абьюз
### 3.1 Resolve
`/v1/mc/resolve` не должен принимать трафик “как публичный сайт”.

Рекомендуемые лимиты (пример):
- per token (MC): 60–120 req/min
- per contact_id (если есть): 6–12 req/min
- per IP: 30 req/min (на случай, если токен где-то засветился)

Реализация:
- Redis‑based rate limiter (опционально)
- или простой in‑memory limiter (только для dev)

### 3.2 Shortlink /t/{slug}
Публичный endpoint. Его будут сканировать.

Меры:
1) Slug короткий и читабельный, но:
   - **не используем “001, 002…”** массово
   - лучше: `dress001`, `look_spring26` (смыслы, но не “словарь из 10”)
2) При miss:
   - редирект в каталог (чтобы не палить 404 на каждый запрос)
   - логируем `redirect_miss`
3) Rate-limit на IP: 60–300 req/min
4) (опционально) `robots.txt` запретить индексацию (но от сканеров не спасёт)

---

## 4) Логи (важное)
### 4.1 Нельзя
- логировать raw payload ManyChat целиком
- логировать email/phone/имена (если вдруг прилетит)
- логировать токены (`X-Admin-Token`, `X-MC-Token`)
- логировать IP “как есть” (если нет причины)

### 4.2 Можно и нужно
- request_id
- endpoint
- channel
- content_ref (если в нём нет PII; иначе маскируем)
- result (`hit/fallback`)
- slug
- latency_ms

### 4.3 Маскирование
Если `content_ref` может содержать потенциально чувствительные куски:
- показываем только префикс + хвост:
  - `campaign:dress001` — ок целиком
  - `ig:media:1789...` — ок, это не PII
  - `mc:contact:123` — лучше не писать в лог

---

## 5) GDPR: что мы считаем персональными данными
В ЕС (ты в Германии) GDPR относится к любым данным, которые могут идентифицировать человека:
- contact_id / user_id (если у провайдера это идентификатор человека)
- IP адрес (прямо PII)
- user agent в сочетании с другими параметрами (потенциально)
- текст сообщений (может содержать имя/телефон/адрес)

**Вывод:** храним минимум и коротко.

---

## 6) Data minimization (минимизация данных)
### 6.1 inbound_events (resolve)
Храним только то, что нужно для диагностики и метрик:
- channel
- content_ref
- flow_id (опционально)
- trigger (опционально)
- payload_hash (dedup)
- result
- resolved_slug, resolved_start_param
- latency_ms
- created_at
- `payload_min` (санитизированный JSON, без PII)

**Не храним:**
- полное содержимое сообщения
- профили пользователя
- любые поля ManyChat, которые не нужны

**text_preview**:
- допускается, но ограничить длину (256) и включать опционально `STORE_TEXT_PREVIEW=false` по умолчанию.

### 6.2 click_events
Минимальный набор:
- slug
- timestamp
- optional: user_agent (обрезанный)
- optional: referer

IP:
- по умолчанию **не хранить**
- если нужно антифрод/рейты → хранить `ip_hash` (sha256(ip + salt))

---

## 7) Retention / TTL (обязательная гигиена)
Если не чистить — БД раздуется и станет мусоркой.

Рекомендуем:
- `sb_inbound_event`: 30–90 дней
- `sb_click_event`: 180–365 дней (или меньше, если агрегации)

Реализация:
- простой cron job (например, раз в сутки)
- SQL:
  - `DELETE FROM sb_inbound_event WHERE created_at < now() - interval '90 days';`
  - `DELETE FROM sb_click_event WHERE created_at < now() - interval '365 days';`

**Важно:** TTL job это часть runbook. Без него “проект взрослый” не считается.

---

## 8) Право на удаление / DSAR (если когда‑нибудь понадобится)
Сейчас SocialBridge не хранит явных пользовательских данных (email/phone/name), поэтому DSAR обычно сводится к “мы не можем идентифицировать пользователя по нашим данным”.

Но если вдруг начнёте хранить `contact_id`:
- добавьте возможность удалить события по `mc_contact_id`
- документируйте это

**Рекомендация:** не хранить contact_id в проде, если нет явного бизнес‑смысла.

---

## 9) Secrets management
### 9.1 Где хранить секреты
- `.env` только локально
- в проде: secret store (DO, k8s secret, GitHub Actions secrets)

### 9.2 Ротация
- `MC_TOKEN` и `ADMIN_TOKEN` должны быть ротируемыми без миграций
- при ротации:
  - обновить env
  - перезапустить сервис

### 9.3 Никогда
- не коммитить `.env`
- не вставлять токены в docs/скриншоты/чаты

---

## 10) Transport security
- HTTPS обязателен
- HSTS (если есть возможность)
- корректные TLS настройки на reverse proxy (nginx/traefik/caddy)

---

## 11) HTTP security headers (на уровне reverse proxy или приложения)
Минимум:
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer` (или strict-origin-when-cross-origin)
- `Content-Security-Policy` (если нет HTML страниц, можно минимально)
- `X-Frame-Options: DENY`

Для API это не супер критично, но приятно.

---

## 12) Ошибки и “что отдаём наружу”
- наружу отдаём короткое сообщение + request_id
- подробности только в логах
- stacktrace никогда не отдаём в response

---

## 13) Простой security checklist (боевой)
- [ ] `X-MC-Token` включён в проде
- [ ] `X-Admin-Token` включён всегда
- [ ] Rate-limit включён хотя бы на `/t/{slug}`
- [ ] В логах нет токенов и сырого payload
- [ ] inbound_events хранит только `payload_min`
- [ ] TTL job настроен
- [ ] `.env` не в git
- [ ] HTTPS работает

---

## 14) “Порог красной лампы” (когда надо усиливать)
Усиливаем меры, если:
- трафик > 10k кликов/день
- начались сканы slug (много redirect_miss)
- замечен спам на resolve
- появляются жалобы/проверки по GDPR

Тогда добавляем:
- Redis rate-limit (строже)
- агрегации + сокращение raw event retention
- IP allowlist на admin
- WAF/Cloudflare перед доменом shortlink

