# 20_manychat — ManyChat как входной шлюз (IG сейчас, TikTok по возможности)

## 0) Задача документа
Зафиксировать **как именно** мы собираем ManyChat‑flows так, чтобы:
- не плодить 200 “почти одинаковых” сценариев,
- передавать в SocialBridge стабильный ключ (`content_ref`) без плясок с ID,
- легко включить новый канал (TikTok) без переписывания ядра,
- не утонуть в ограничениях free‑плана.

Идея простая: **ManyChat триггерит → зовёт наш API → отправляет пользователю ссылку**.

---

## 1) Термины и соглашения (важно)
### 1.1 content_ref
**content_ref** — универсальный ключ, который мы передаём в SocialBridge, чтобы получить правильную ссылку.

Формат (строка):
- `ig:media:<id>` — если реально используем media_id поста
- `ig:story:<id>` — если есть story_id
- `mc:flow:<id>` — самый стабильный вариант (не зависит от соцсетей)
- `campaign:<name>` — когда один flow = одна кампания/товар/лук
- `keyword:<word>` — когда триггер по слову

**Рекомендация для старта:** `campaign:<name>` или `mc:flow:<id>`  
Это практичнее, чем гоняться за media_id каждого поста.

### 1.2 channel
Строка канала:
- `ig` (Instagram)
- `tt` (TikTok)
- `generic` (если “просто ссылка” без соцсети)

### 1.3 slug
Slug = короткая метка shortlink’а (`dress001`, `spring26`, `catalog`).  
**Slug создаёт/возвращает SocialBridge**. ManyChat slug сам не придумывает.

---

## 2) Предварительные условия (чтобы не ловить “почему не работает”)
### 2.1 Instagram
- Instagram аккаунт должен быть **Professional** (Business или Creator).
- Аккаунт подключаем к ManyChat через их стандартный коннектор.

### 2.2 TikTok
- TikTok подключение в ManyChat может быть **недоступно** по региону/аккаунту.
- Поэтому наша архитектура:
  - IG: “автоматика через ManyChat”
  - TikTok: пока **bio link / закреп / shortlink**, потом, если коннектор откроется, включаем аналогично IG.

---

## 3) Общая схема Flow (шаблон)
Любой flow должен быть устроен одинаково:

1) **Trigger** (comment/story/DM/keyword)
2) **Set variables** (минимум: `sb_channel`, `sb_content_ref`)
3) **External Request** → `POST /v1/mc/resolve`
4) **Send message** (текст + кнопка/ссылка из ответа)

И всё. Никаких “внутри ManyChat 20 веток логики”, иначе потом это никто не поддержит.

---

## 4) Какие переменные мы храним в ManyChat
В ManyChat создаём Custom Fields (минимум):
- `sb_channel` (text) — `ig` / `tt`
- `sb_content_ref` (text) — `campaign:...` / `mc:flow:...` / etc.
- `sb_last_url` (text) — чтобы удобно дебажить и переиспользовать
- `sb_last_start_param` (text) — опционально
- `sb_last_tag` (text) — опционально

**Почему так:** ManyChat умеет вставлять custom fields в JSON для External Request и в сообщения.

Рекомендованная дисциплина имен:
- префикс `sb_` (SocialBridge), чтобы не путать с остальными интеграциями.

---

## 5) External Request: контракт и настройка
### 5.1 Endpoint
- Method: `POST`
- URL: `https://YOUR_SOCIALBRIDGE_DOMAIN/v1/mc/resolve`
- Headers:
  - `Content-Type: application/json`
  - `X-MC-Token: <shared_secret>` (опционально, но желательно)
  - (если надо) `X-Request-Source: manychat`

### 5.2 Body (рекомендуемый шаблон, копируй как есть)
Формируй тело запроса по контракту `/v1/mc/resolve`:

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

**Примечания:**
- Если в твоём шаблоне ManyChat другое имя переменной текста (`{{message.text}}`, `{{comment_text}}`), подставь его в поле `text`.
- Если текста нет, передай пустую строку: `"text": ""`.

### 5.3 Response mapping (обязательно)
В External Request map response fields в Custom Fields:
- `sb_last_url` ← `response.url`
- `sb_reply_text` ← `response.reply_text`

Рекомендуется дополнительно сохранять:
- `sb_last_start_param` ← `response.start_param`
- `sb_last_tag` ← `response.tag`

После этого блок “Send message” использует `{{sb_reply_text}}` и кнопку/ссылку `{{sb_last_url}}`.

---

## 6) Шаблоны Flow (в боевой практике)

### 6.1 “Один пост → один товар” (рекомендованный старт)
**Trigger:** comment/story reply/DM mention на конкретный контент.  
**content_ref:** не обязательно media_id. Берём `campaign:<name>`.

**Пример:**
- Flow: `SB_IG_CAMP_DRESS001`
- Set:
  - `sb_channel = ig`
  - `sb_content_ref = campaign:dress001`
- External Request
- Send:
  - `{{sb_reply_text}}`
  - кнопка: `Купить` → `{{sb_last_url}}`

**Плюс:** не зависим от того, как ManyChat отдаёт id поста.

### 6.2 “Один flow → несколько постов”
Если одна и та же вещь продаётся из разных постов:
- в ManyChat вешаем один и тот же flow на несколько триггеров
- `content_ref = campaign:dress001` одинаковый
- в SocialBridge одна запись `campaign:dress001 → start_param=DRESS001`

### 6.3 “Keyword‑воронка” (учитывая free‑лимиты)
На free обычно мало keyword‑триггеров, поэтому:
- делай 1–3 “универсальных” слова, например: `BUY`, `SIZE`, `CATALOG`
- внутри не ветвись на 20 товаров. Просто отдавай:
  - `SIZE` → SizeBot/размерная логика (или лук)
  - `BUY` → каталог / подборки
  - `CATALOG` → каталог

**Если нужно много товаров:** делай пост‑специфичные flows через comment/story triggers, а не keyword.

### 6.4 “Fallback flow” (обязателен)
Должен быть один универсальный flow:
- `SB_IG_FALLBACK`
- `sb_content_ref = campaign:catalog`
- SocialBridge возвращает каталог

Это спасает продажи, когда маппинг не успели завести.

---

## 7) Нейминг и организация flows (чтобы не наступить на себя)
### 7.1 Конвенция имен
- `SB_IG_CAMP_<CODE>` — кампании/товары
- `SB_IG_LOOK_<CODE>` — луки
- `SB_IG_FALLBACK` — дефолт
- `SB_TT_*` — TikTok (когда будет)

### 7.2 “Один flow = один смысл”
Flow должен быть короткий:
- Set variables
- External Request
- Send message

Если хочется “добавить прогрев на 5 сообщений” — делай отдельный flow (иначе дебажить невозможно).

---

## 8) Текст сообщения (как писать, чтобы люди кликали)
### 8.1 Формула
- 1 строка: обещание
- 1 строка: ссылка/кнопка
- опционально: мини‑подсказка

Пример:
- “Готово. Вот товар 👇”
- “Если нужен размер, напиши **SIZE**.”

### 8.2 Кнопка всегда лучше, чем голая ссылка
Пользователь должен нажать в один тап.

---

## 9) Тестирование (без гаданий)
### 9.1 Тест resolve без ManyChat
`curl -X POST https://YOUR_DOMAIN/v1/mc/resolve -H 'Content-Type: application/json' -d '{"channel":"ig","content_ref":"campaign:dress001","text":"hi","mc":{"contact_id":"1","flow_id":"F1","trigger":"test"}}'`

### 9.2 Тест ManyChat
1) Подключил IG
2) Создал flow `SB_IG_CAMP_DRESS001`
3) Поставил trigger на тестовый пост/коммент
4) Посмотрел:
   - SocialBridge лог: `resolve hit/miss`
   - ManyChat preview: корректная подстановка `sb_last_url`
5) Клик по ссылке → редирект в Telegram → открылась карточка

### 9.3 Типовые ошибки
- забыли `sb_content_ref` → SocialBridge отдаёт каталог (по fallback)
- не сохранили response.url → кнопка пустая
- неверный домен `BASE_URL` → ссылки ведут в никуда
- длинный start_param → Telegram его отрежет/сломает

---

## 10) TikTok режим “пока без интеграции” (план Б)
Если TikTok не подключается в ManyChat:
- TikTok bio link: `https://go.DOMAIN/t/<slug>`
- закреплённый комментарий с shortlink
- CTA в видео “ссылка в профиле”

**Плюс:** SocialBridge уже считает клики и кампании через slug, даже без DM.

Когда TikTok коннектор станет доступным:
- копируем IG‑шаблон flow
- меняем `sb_channel = tt`
- `sb_content_ref = campaign:...` остаётся тем же
- всё работает без правок ядра.

---

## 11) Безопасность (минимум, но нормально)
- В External Request добавляем `X-MC-Token`.
- SocialBridge проверяет токен и логирует отказ (403), если токен неверный.
- Не шлём в SocialBridge лишние PII поля из ManyChat, только необходимые.

---

## 12) Чек‑лист “готово к бою”
- [ ] Есть `SB_IG_FALLBACK`
- [ ] Есть 3–10 кампаний `SB_IG_CAMP_*`
- [ ] content_map заполнен на эти кампании
- [ ] resolve возвращает url/start_param стабильно
- [ ] редирект /t/{slug} пишет click_event
- [ ] Telegram deeplink открывает нужный объект в SIS


## 13) Первый IG flow за 15 минут (чек-лист)
1. Подними инфраструктуру (базовый compose сервисы `api` + `postgres`): `docker compose up -d --build`.
2. Прогони миграции в сервисе `api`: `docker compose exec api alembic upgrade head`.
3. Импортируй минимальный seed:
   `python scripts/admin_import_map.py --base-url http://localhost:8000 --token <ADMIN_TOKEN> --file seed/content_map_seed_min.json`.
4. Проверь резолв каталога:
   `python scripts/admin_resolve_preview.py --base-url http://localhost:8000 --token <ADMIN_TOKEN> --channel ig --content-ref campaign:catalog --text "hi"`.
5. В ManyChat создай Custom Fields: `sb_channel`, `sb_content_ref`, `sb_last_url`, `sb_reply_text`.
6. Создай flow `SB_IG_CAMP_DRESS001`.
7. В блоке Set Custom Fields выставь: `sb_channel=ig`, `sb_content_ref=campaign:dress001`.
8. Добавь External Request с body из секции 5.2 и mapping из 5.3.
9. В Send Message вставь `{{sb_reply_text}}` и кнопку `Купить` на `{{sb_last_url}}`.
10. Протести путь целиком: триггер в IG → ManyChat reply → клик `/t/dress001` → редирект в `https://t.me/<SIS_BOT_USERNAME>?start=DRESS001`.

