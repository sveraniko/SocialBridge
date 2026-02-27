# 26_manychat_ops — Operations pack (campaign lifecycle + safety)

## 0) Scope
Документ для операторов, которые ведут кампании в ManyChat + SocialBridge без изменения API контрактов.

Базовые принципы:
- Управляем кампаниями через `campaign:*` и admin API.
- Делаем rollback через disable/export/import, а не через "быстрые ручные правки" в хаосе.
- Всегда держим fallback на каталог (`campaign:catalog`).

---

## 1) Campaign lifecycle
Цикл эксплуатации:

1. **Create**
   - Создать/обновить запись в реестре кампаний (CSV).
   - Сгенерировать JSON (`scripts/registry_to_content_map.py`).
   - Импортировать в content map (`scripts/admin_import_map.py` или через API).

2. **Validate**
   - Проверить `/v1/admin/resolve-preview` для целевого `channel + content_ref`.
   - Проверить, что slug/start_param соответствуют кампании.

3. **Enable triggers**
   - Включить нужные триггеры в ManyChat (comment, story reply, keyword).
   - Подтвердить, что `sb_channel` + `sb_content_ref` выставляются корректно.

4. **Monitor**
   - Следить за кликами, resolve hit-rate и redirect miss-rate.
   - Следить за ростом dynamic mappings (meta.dynamic=true).

5. **Edit**
   - Вносить изменения через upsert/import (не ручными SQL правками).
   - Повторить Validate перед публикацией изменения в триггеры.

6. **Rollback**
   - Сначала disable проблемной mapping.
   - Затем восстановить предыдущий export backup.
   - При необходимости включить emergency fallback на каталог.

7. **Disable**
   - Отключить кампанию через admin disable.
   - Проверить, что resolve уходит в безопасный fallback.

---

## 2) Operating modes (коммерческие режимы)

### Mode 0 — direct shortlink
**Каналы:** bio / stories / pinned comment.

- Без per-post mapping.
- Оператор распространяет готовый shortlink (`/t/{slug}`) напрямую.
- Минимум интеграционных рисков, быстрый запуск.

### Mode 1 — keyword BUY + code (без per-post mapping)
- Триггер: keyword (например `BUY`, `SIZE`, код товара).
- `content_ref` стабильный (обычно `campaign:*`), роутинг по слову/коду.
- Нет привязки "конкретный пост → конкретный map item".

### Mode 2 — per-post comment-to-DM mapping (campaign registry)
- Каждый продающий пост сопоставляется с отдельным `campaign:*`.
- Используется campaign registry + регулярные export/import бэкапы.
- Максимальная точность, но выше операционная дисциплина.

---

## 3) Rollback playbook

### A) Disable mapping (admin disable)
1. Найти проблемный ключ `channel + content_ref`.
2. Выполнить:
   ```bash
   python scripts/ops_disable_campaign.py \
     --base-url http://localhost:8000 \
     --token "$ADMIN_TOKEN" \
     --channel ig \
     --content-ref campaign:dress001
   ```
3. Убедиться по ответу, что `result=disabled`.

### B) Re-import previous registry export
1. Выбрать последний валидный backup JSON.
2. Импортировать:
   ```bash
   python scripts/admin_import_map.py \
     --base-url http://localhost:8000 \
     --token "$ADMIN_TOKEN" \
     --file backups/content_map_backup_all_all_YYYYMMDDTHHMMSSZ.json
   ```
3. Проверить `created/updated/failed` и сделать spot-check через resolve preview.

### C) Emergency switch to catalog
- Временно направить триггеры/кампанию на `campaign:catalog`.
- Если нужно, отключить нестабильные post-specific mappings.
- Сообщение пользователю: "актуальный каталог" вместо узкого оффера.

---

## 4) Monitoring checklist

Операторский минимум (ежедневно / на запуске кампании):

- **Clicks per slug**
  - Проверка топовых slug и их тренда.
- **Resolve hit-rate**
  - Доля успешных resolve (не fallback / не not_found).
- **Redirect miss-rate**
  - Частота промахов по slug (`/t/{slug}` not_found/inactive).
- **Dynamic mapping count vs limit**
  - Сколько `meta.dynamic=true` создано за последние 24 часа.
  - Сравнение с операционным порогом.

Быстрый статус:
```bash
python scripts/ops_status.py --base-url http://localhost:8000 --token "$ADMIN_TOKEN" --dynamic-limit 5000
```

---

## 5) Token rotation checklist

Ротация токенов должна быть плановой и после инцидентов.

### ADMIN_TOKEN
1. Сгенерировать новый токен.
2. Обновить секреты окружения (`.env`, vault, CI/CD secrets).
3. Перезапустить сервис `api`.
4. Прогнать smoke-check admin endpoints (`/v1/admin/content-map/export`).
5. Отозвать старый токен.

### MC_TOKEN
1. Сгенерировать новый shared secret.
2. Обновить `MC_TOKEN` в SocialBridge окружении.
3. Обновить header `X-MC-Token` в ManyChat External Request.
4. Проверить `/v1/mc/resolve` тестовым flow.
5. Отозвать старый токен.

---

## 6) Retention & cleanup policy

### inbound_events TTL
- Рекомендуемый TTL: **90 дней** (или согласно политике/договору).
- Очистка через retention job.

### click_events TTL
- Рекомендуемый TTL: **90 дней** (или согласно политике/договору).
- Для долгих периодов оставлять только агрегаты (при необходимости отдельно).

### Dynamic mappings (`meta.dynamic=true`)
- На MVP удаление dynamic mappings не делаем автоматически.
- Что делаем сейчас:
  - мониторим суточный рост;
  - контролируем "count vs limit";
  - при превышениях включаем разбор причин и планируем cleanup отдельной задачей.
- Опциональный cleanup позже: отдельный ops сценарий с whitelist/age filters (не в рамках текущего контракта).

---

## 7) Operator commands (copy/paste)

### 7.1 Export backup
```bash
python scripts/ops_export_backup.py \
  --base-url http://localhost:8000 \
  --token "$ADMIN_TOKEN" \
  --channel ig \
  --is-active all \
  --out-dir backups
```

### 7.2 Disable campaign
```bash
python scripts/ops_disable_campaign.py \
  --base-url http://localhost:8000 \
  --token "$ADMIN_TOKEN" \
  --channel ig \
  --content-ref campaign:dress001
```

### 7.3 Re-import registry JSON
```bash
python scripts/admin_import_map.py \
  --base-url http://localhost:8000 \
  --token "$ADMIN_TOKEN" \
  --file backups/content_map_backup_ig_all_YYYYMMDDTHHMMSSZ.json
```

---

## 8) Analytics in Wizard / Admin API

Новые операторские endpoints для базовой воронки IG:
- `GET /v1/admin/stats/overview?hours=24|168`
- `GET /v1/admin/stats/top?hours=24|168&limit=20`
- `GET /v1/admin/stats/campaign?content_ref=...&hours=24|168`

Что измеряем:
- `resolves_total` — число resolve событий (`sb_inbound_event`) за окно.
- `resolves_by_result` — разрез `hit / fallback_payload / fallback_catalog`.
- `clicks_total` — число кликов/редиректов (`sb_click_event`) за окно.
- `ctr_bridge` — `clicks_total / resolves_total` (с защитой от деления на 0).
- `redirect_miss_total` — клики с `meta.miss=true` (slug не найден/неактивен).
- топ кампаний по кликам и по resolve.

Что **не** измеряем (важно):
- нет заказов/выручки/покупок (purchase attribution пока не внедрен);
- нет user-level/PII аналитики (агрегированные счетчики только по событиям);
- нет cohort/funnel до оплаты — только bridge-часть: resolve → click.

## 9) Notes on dynamic count implementation
`ops_status.py` по-прежнему считает dynamic mappings за 24 часа через admin export (`/v1/admin/content-map/export`) и поля `meta.dynamic + created_at`.


## Keyword intents (BUY / LOOK / CAT)

SocialBridge and Wizard support 3 configurable keywords:

- `BUY <CODE>` → product intent (`fallback_payload`, `start_param=<CODE>`)
- `LOOK <CODE>` → look intent (`fallback_payload`, `start_param=LOOK_<CODE>` if prefix missing)
- `CAT` → catalog intent (`fallback_catalog`, `start_param=null`)

Recommended ManyChat triggers:
- DM contains `BUY`
- DM contains `LOOK`
- DM equals `CAT`

Keywords are configurable via env (`WIZARD_KEYWORD_*` in wizard, `KEYWORD_*` in API).
