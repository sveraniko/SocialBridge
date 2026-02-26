# 27_campaign_wizard_overview

## Purpose
`wizard_bot` is a Telegram admin-only helper for operating SocialBridge content mapping in a phone-first flow.
PR2 adds full Create Link/Campaign CRUD wizard screens (inline-only), plus result actions (disable and resolve preview).

## Security model
- Access is restricted by Telegram user id whitelist from `WIZARD_ADMIN_IDS`.
- The bot calls SocialBridge admin API with `SOCIALBRIDGE_ADMIN_TOKEN`.
- Token values are never written to bot logs.
- Redis stores minimal wizard/chat state:
  - `wiz:chat:{chat_id}:stack`
  - `wiz:chat:{chat_id}:msgs`
  - `wiz:chat:{chat_id}:panel:active`
  - `wiz:chat:{chat_id}:lock`
  - `wiz:chat:{chat_id}:session`
  - `wiz:chat:{chat_id}:unauth:notified`
- Unauthorized message UX: one `UNAUTHORIZED_TEXT` notice per chat every 24h.

## PR2 inline screens
1. **MAIN**
   - `Create Link`
   - `Campaigns`
   - `Clean Chat`

2. **Create Link wizard**
   - Step 1: choose mode (`0` direct shortlink, `1` BUY+code, `2` comment→DM mapping)
   - Step 2: choose kind (`product`, `look`, `catalog`)
   - Step 3: start_param input (product/look validated, catalog = NULL)
   - Step 4: slug mode (`auto`, `custom`, `skip`)
   - Step 5: confirm (`Create`, `Back`, `Cancel`)

3. **Result panel after create**
   - Shows shortlink (`WIZARD_PUBLIC_BASE_URL/t/<slug>`)
   - Mode-specific operator output:
     - Mode 0: link copy
     - Mode 1: BUY template copy
     - Mode 2: ManyChat operator snippet + response mapping fields
   - Actions:
     - `Disable campaign`
     - `Resolve Preview`
     - `Main Menu`
     - `Clean Chat`

## API integration in PR2
- `GET /v1/admin/content-map` (campaign list)
- `POST /v1/admin/content-map/upsert` (create/update mapping)
- `POST /v1/admin/content-map/disable` (disable mapping)
- `POST /v1/admin/resolve-preview` (preview resolver result)

Created mappings default to channel `ig` and include metadata:
```json
{"mode":"0|1|2","kind":"product|look|catalog","wizard":true}
```

## Local run
1. Configure env vars in `.env`:
   - `WIZARD_BOT_TOKEN`
   - `WIZARD_ADMIN_IDS`
   - `WIZARD_REDIS_URL`
   - `SOCIALBRIDGE_ADMIN_BASE_URL`
   - `SOCIALBRIDGE_ADMIN_TOKEN`
   - `WIZARD_DEFAULT_CHANNEL` (default `ig`)
   - `WIZARD_PUBLIC_BASE_URL` (for rendered shortlink; example `http://localhost:8000`)
2. Start stack:
   ```bash
   docker compose up -d --build
   ```
3. Apply migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```
4. Open Telegram, send `/start` to bot.

## Quick operator path (create DRESS001 link)
1. `/start`
2. Tap `Create Link`
3. Select `Mode 0 · Direct shortlink`
4. Select `Product`
5. Send text: `DRESS001`
6. Choose `Auto` slug (or `Custom` and send slug)
7. Tap `Create`
8. Copy shortlink from result panel.

## Notes
- UX stays inline-only (no reply keyboards).
- `Back` always moves exactly one step back.
- `Clean Chat` removes all registered bot messages and resets wizard session.
