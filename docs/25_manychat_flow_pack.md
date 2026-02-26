# 25_manychat_flow_pack — операторский пакет для ManyChat (IG)

## 0) Цель
Этот документ — практический "flow pack" для оператора:
- единые правила именования,
- готовые шаблоны блоков,
- безопасный путь запуска новой кампании за 3 минуты,
- без изменений API и без переписывания Flow логики.

Документ дополняет `docs/20_manychat.md` и фиксирует copy-paste шаблоны для масштабирования.

---

## 1) Канонические соглашения

### 1.1 Имена Flow
Используй только эти паттерны:
- `SB_IG_CAMP_<CODE>` — продуктовая кампания
- `SB_IG_LOOK_<CODE>` — кампании "лук/подборка"
- `SB_IG_FALLBACK` — запасной каталог
- `SB_IG_KEY_<KEYWORD>` — ключевое слово в DM
- `SB_IG_ROUTER` (опционально) — общий роутер

Примеры:
- `SB_IG_CAMP_DRESS001`
- `SB_IG_LOOK_SPRING26`
- `SB_IG_KEY_CATALOG`

### 1.2 Campaign key (`content_ref`)
Формат:
- `campaign:<lower_snake_or_code>`

Примеры:
- `campaign:dress001`
- `campaign:look_spring26`
- `campaign:catalog`

### 1.3 Slug
Правила slug:
- lowercase,
- prefer `<=32` символов,
- допустимый паттерн: `[a-z0-9_-]`.

---

## 2) Обязательные Custom Fields в ManyChat
Создай (тип `Text`):
- `sb_channel`
- `sb_content_ref`
- `sb_last_url`
- `sb_reply_text`

Опционально:
- `sb_last_tag`

Рекомендация: все интеграционные поля держим под префиксом `sb_`.

---

## 3) External Request (копируй как есть)

### 3.1 Request
- Method: `POST`
- URL: `https://<YOUR_DOMAIN>/v1/mc/resolve`
- Headers:
  - `Content-Type: application/json`
  - `X-MC-Token: <shared_secret>`

JSON Body template:

```json
{
  "channel": "{{sb_channel}}",
  "content_ref": "{{sb_content_ref}}",
  "text": "{{last_text_input}}",
  "mc": {
    "contact_id": "{{contact.id}}",
    "flow_id": "{{flow.id}}",
    "trigger": "{{trigger.name}}"
  }
}
```

### 3.2 Response Mapping
Обязательно настроить mapping:
- `sb_last_url` <- `response.url`
- `sb_reply_text` <- `response.reply_text`

Опционально:
- `sb_last_tag` <- `response.tag`

### 3.3 Message block после External Request
Короткий шаблон:
- Text: `{{sb_reply_text}}`
- Button label: `Открыть` / `Смотреть`
- Button URL: `{{sb_last_url}}`

---

## 4) Flow Blueprints (текстовые block-diagram шаблоны)

> Базовый каркас для всех: `Trigger -> Set fields -> External Request -> Send Message`

### 4.1 Product campaign flow
**Flow name:** `SB_IG_CAMP_DRESS001`  
**Purpose:** отправка ссылки на карточку/офер для продукта DRESS001  
**Trigger type:** comment-to-DM / button click  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:dress001`

**External Request:** `/v1/mc/resolve` (шаблон из раздела 3)  
**Message copy:** `Вот ссылка на модель DRESS001 ✨`  
**Button label:** `Смотреть DRESS001`  
**When to use:** пост/реклама под конкретный SKU, один пост = один product code.

---

### 4.2 Look campaign flow
**Flow name:** `SB_IG_LOOK_SPRING26`  
**Purpose:** выдача ссылки на лук/подборку LOOK_SPRING26  
**Trigger type:** story reply / DM keyword  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:look_spring26`

**External Request:** `/v1/mc/resolve`  
**Message copy:** `Собрали для тебя LOOK_SPRING26 🌿`  
**Button label:** `Открыть look`  
**When to use:** сезонные подборки, lookbook, capsule drops.

---

### 4.3 Fallback catalog flow
**Flow name:** `SB_IG_FALLBACK`  
**Purpose:** безопасная выдача общего каталога, если нет точной кампании  
**Trigger type:** button click / default fallback  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:catalog`

**Expected registry mapping:** `slug=catalog`, `start_param` пустой/null  
**External Request:** `/v1/mc/resolve`  
**Message copy:** `Открывай актуальный каталог 👇`  
**Button label:** `Перейти в каталог`  
**When to use:** общий CTA в bio, fallback при нераспознанном сценарии.

---

### 4.4 Keyword flows (SIZE / BUY / CATALOG)
**Flow names:**
- `SB_IG_KEY_SIZE`
- `SB_IG_KEY_BUY`
- `SB_IG_KEY_CATALOG`

**Purpose:** роутинг DM keywords на стабильные campaign keys  
**Trigger type:** DM keyword  
**Set variables (пример):**
- SIZE -> `sb_channel=ig`, `sb_content_ref=campaign:size_help`
- BUY -> `sb_channel=ig`, `sb_content_ref=campaign:buy_now`
- CATALOG -> `sb_channel=ig`, `sb_content_ref=campaign:catalog`

**External Request:** `/v1/mc/resolve`  
**Message copy:** `Готово — вот нужная ссылка 👇`  
**Button label:** `Открыть`  
**When to use:** часто повторяемые intents без ветвления внутри ManyChat.

---

### 4.5 Comment-to-DM post selling pattern
**Flow name template:** `SB_IG_CAMP_<CODE>`  
**Purpose:** автоматический DM после комментария под продающим постом  
**Trigger type:** comment-to-DM  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:<code>`

**External Request:** `/v1/mc/resolve`  
**Message copy:** `Спасибо за комментарий! Вот ссылка 👇`  
**Button label:** `Получить предложение`  
**When to use:** конверсия комментариев в клики с минимальной ручной обработкой.

---

### 4.6 Story reply pattern
**Flow name template:** `SB_IG_LOOK_<CODE>` или `SB_IG_CAMP_<CODE>`  
**Purpose:** отвечать на replies к stories релевантной ссылкой  
**Trigger type:** story reply  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:<code>`

**External Request:** `/v1/mc/resolve`  
**Message copy:** `Лови ссылку по сторис ✨`  
**Button label:** `Открыть`  
**When to use:** быстрый social commerce по сторис-активностям.

---

### 4.7 Operator test flow (pre-launch)
**Flow name:** `SB_IG_ROUTER` или `SB_IG_TEST_<CODE>`  
**Purpose:** проверка резолва до включения триггеров  
**Trigger type:** button click (только для операторов/админов)  
**Set variables:**
- `sb_channel = ig`
- `sb_content_ref = campaign:<candidate_code>`

**External Request:** `/v1/mc/resolve`  
**Message copy:** `Тестовый ответ: {{sb_reply_text}}`  
**Button label:** `Проверить ссылку`  
**When to use:** до публикации поста/триггера, вместе с `/v1/admin/resolve-preview`.

---

## 5) "Создать новую кампанию за 3 минуты" (чеклист)
1. Добавь запись в реестр кампаний (`seed/campaign_registry_*.csv`).
2. Сгенерируй JSON для импорта:
   - `python scripts/registry_to_content_map.py --in seed/campaign_registry_example.csv --out seed/generated_content_map.json`
3. Импортируй JSON через админ API (`/v1/admin/content-map/import`).
4. Дублируй нужный flow template (`SB_IG_CAMP_*` / `SB_IG_LOOK_*`).
5. В ManyChat задай:
   - `sb_channel=ig`
   - `sb_content_ref=campaign:<new_key>`
6. Подключи триггеры (comment / story reply / keyword / button).
7. Проверь резолв до запуска:
   - `python scripts/admin_resolve_preview.py --base-url http://localhost:8000 --token <ADMIN_TOKEN> --channel ig --content-ref campaign:<new_key> --text "preview"`
8. После успешной проверки включи trigger в production.

---

## 6) Правила эксплуатации
- Не кодируй бизнес-логику в ветках ManyChat; только trigger + variables + request + message.
- Всегда используй `campaign:*` как основной `content_ref` для операционной прозрачности.
- Для каталога держи отдельный fallback flow (`SB_IG_FALLBACK`) и запись реестра с пустым `start_param`.
- Перед массовым запуском новых flows сначала валидируй CSV -> JSON скриптом.
