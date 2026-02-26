# 27_campaign_wizard_overview

## Purpose
`wizard_bot` is a Telegram admin-only helper for operating SocialBridge content mapping in a phone-first flow.
PR3 extends PR2 with operator tools for backup/restore, campaign enable/disable from browse view, and service status checks.

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

## PR3 inline screens and actions (inline-only)
1. **MAIN**
   - `Create Link`
   - `Campaigns`
   - `Backup / Export`
   - `Restore / Import`
   - `Status`
   - `Clean Chat`

2. **Campaigns list (phone-first paging)**
   - First page shown with `WIZARD_CAMPAIGNS_PAGE_LIMIT`
   - `Next` / `Prev` paging by offset
   - Each campaign line is a button opening **Campaign View**

3. **Campaign View panel**
   - Displays: `channel`, `content_ref`, `start_param` (`NULL -> Catalog`), `slug`, `is_active`
   - Displays shortlink: `{WIZARD_PUBLIC_BASE_URL}/t/{slug}`
   - Actions:
     - `Disable` / `Enable` (toggle)
     - `Resolve Preview`
     - `Back to list`
     - `Main Menu`
     - `Clean Chat`

4. **Backup / Export**
   - Calls `GET /v1/admin/content-map/export`
   - Bot sends JSON document:
     - filename: `content_map_backup_YYYYMMDD_HHMM.json`
   - Sent document message id is registered in chat message registry for `Clean Chat`

5. **Restore / Import**
   - Bot enters awaiting document state: `awaiting_document=import_content_map`
   - Admin uploads JSON document (`array` OR `{"items":[...]}`)
   - Bot downloads via Telegram `getFile` + file endpoint
   - Calls `POST /v1/admin/content-map/import`
   - Shows summary panel: `created/updated/failed` and first 5 errors

6. **Status**
   - `/health` status (`200/503`)
   - `/ready` status (`200/503`)
   - total campaigns count (`GET /v1/admin/content-map` total)
   - dynamic mappings for last 24h (approx):
     - export `channel=generic,is_active=true`
     - count where `content_ref` starts with `dyn:` and `created_at` in last 24h
   - dynamic limit label:
     - `DYNAMIC_MAPPING_MAX_PER_DAY` if available
     - otherwise `limit configured on server`

## Wizard create flow behavior updates in PR3
- Create/upsert always sends `is_active=true` to avoid re-creating disabled campaigns as disabled.
- Result screen actions include `Disable campaign`, `Enable campaign`, `Resolve Preview`, `Main Menu`, and `Clean Chat` (inline-only).
- Disable still uses `POST /v1/admin/content-map/disable`.
- Enable uses upsert with `is_active=true` (no new API endpoint).
- After enable/disable, the bot refreshes campaign state and edits the same panel with a short status line (`✅ Campaign enabled` / `⛔ Campaign disabled`).

### Result screen example (textual screenshot)
```text
Campaign created ✅
Shortlink: http://localhost:8000/t/dress001
Link for bio/story/pinned comment: http://localhost:8000/t/dress001

✅ Campaign enabled

[Disable campaign]
[Enable campaign]
[Resolve Preview]
[Main Menu] [Clean Chat]
```

## UX guarantees
- No reply keyboards, only inline keyboards.
- `Back` must move exactly one step back (wizard step or nav stack route).
- Every wizard output uses a unified send+register path, so panel messages, extra text notices, and sent documents are all tracked in `wiz:chat:{chat_id}:msgs` for cleanup.
- `Clean Chat` deletes active panel + all registered messages, clears wizard state keys (`session` and `stack`), and then shows a single `✅ Cleaned` inline panel.
- SocialBridge HTTP errors are shown in friendly panel text and do not crash wizard flow.

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

## Operator quick workflows
### Export backup from bot
1. `/start`
2. Tap `Backup / Export`
3. Download sent `content_map_backup_*.json` file from chat.

### Import backup file
1. `/start`
2. Tap `Restore / Import`
3. Upload JSON backup document
4. Read import summary panel (`created/updated/failed`, first errors)

### Enable/Disable a campaign
1. `/start`
2. Tap `Campaigns`
3. Open campaign in list
4. Tap `Disable` or `Enable`
5. Optional: tap `Resolve Preview` to validate mapping behavior.

### Status panel
1. `/start`
2. Tap `Status`
3. Check health/ready statuses, total campaigns, and recent dynamic mapping count.
