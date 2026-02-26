# 27_campaign_wizard_overview

## Purpose
`wizard_bot` is a Telegram admin-only helper for operating SocialBridge content mapping in a phone-first flow.
PR1 adds only the foundation and read-only campaign list panel.

## Security model
- Access is restricted by Telegram user id whitelist from `WIZARD_ADMIN_IDS`.
- The bot calls SocialBridge admin API with `SOCIALBRIDGE_ADMIN_TOKEN`.
- Token values are never written to bot logs.
- Redis stores only minimal navigation/panel state:
  - `wiz:chat:{chat_id}:stack`
  - `wiz:chat:{chat_id}:msgs`
  - `wiz:chat:{chat_id}:panel:active`
  - `wiz:chat:{chat_id}:lock`

## Local run
1. Configure env vars in `.env`:
   - `WIZARD_BOT_TOKEN`
   - `WIZARD_ADMIN_IDS`
   - `WIZARD_REDIS_URL`
   - `SOCIALBRIDGE_ADMIN_BASE_URL`
   - `SOCIALBRIDGE_ADMIN_TOKEN`
2. Start stack:
   ```bash
   docker compose up -d --build
   ```
3. Apply migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```
4. Open Telegram, send `/start` to bot, use inline menu.

## Included in PR1
- Telegram polling bot service (`python -m wizard_bot`).
- Inline-only panel UX:
  - MAIN (`Campaigns`, `Clean Chat`)
  - CAMPAIGNS_LIST (`Refresh`, `Back`, `Clean Chat`)
- Redis-backed navigation stack and panel message registry.
- Clean chat action deletes all registered panel messages.
- Per-chat Redis lock to handle callback double-clicks safely.
- Read-only campaigns list via `GET /v1/admin/content-map?limit=50`.
