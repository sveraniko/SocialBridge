# SB-RECON-01: SIS Deep-link Facts for SocialBridge Integration

**Date:** 2026-02-25  
**Scope:** Read-only analysis for ManyChat → SIS deep-link integration  
**Status:** Complete

---

## A) Summary Facts (Bullets)

### 1. /start Handler Overview
- **Main file:** [app/bot/handlers/start.py](file://app/bot/handlers/start.py)
- **Handler:** `on_start()` at line 54-393
- **Deep-link parameter extraction:** Lines 97-99 — splits message text to get param after `/start`

### 2. Supported Payload Formats
| Prefix | Action | Priority | Notes |
|--------|--------|----------|-------|
| `pfm_{order_id}_{token}` | PayForMe payment link | 1st | Format: `pfm_123_abc123token` |
| `ao_{order_id}` | Admin order view | 2nd | **Admin only** |
| `order_{order_id}` | User order details | 3rd | User must own the order |
| `key_{raw_key}` | Access key redemption | 4th | For closed-club access |
| `club_{raw_key}` | Access key redemption | 4th | Alias for `key_` |
| `LOOK_{code}` | Look/outfit card | 5th | Opens look by code |
| `prod_{product_id}` | Product by ID | 6th | Opens product by database ID |
| `{product_code}` | Product by code | **fallback** | Any other value = product code lookup |

### 3. Start Param Restrictions
- **Explicit length check in SIS:** ❌ None found
- **Telegram limit:** 64 characters (per Telegram Bot API spec)
- **Character restrictions:** Base64-safe recommended (alphanumeric, `_`, `-`)

### 4. Analytics/Source Tracking
- **Source field exists:** ✅ Yes — `source="deeplink"` passed when opening via deep-link
- **Logged events:**
  - `LOOK_OPENED` → [app/bot/ui/look_card.py#L270-292](file://app/bot/ui/look_card.py#L270)
  - `LOOK_CARD_VIEW` (track_event) → [app/bot/ui/look_card.py#L251-264](file://app/bot/ui/look_card.py#L251)
  - Product views emit `PRODUCT_VIEWED` event
- **No `campaign` field currently** — only `source` is tracked

### 5. Catalog Home (No Payload)
- `/start` without parameters → `show_catalog_home()` at line 393
- Opens default catalog view (products, looks, or mixed depending on settings)
- **No special "catalog" payload exists** — empty param = catalog home

### 6. Hidden Product Access
- Setting `allow_open_hidden_product_by_deeplink` controls access to hidden products
- Defined in [app/domain/shop/settings/schema.py#L147](file://app/domain/shop/settings/schema.py#L147)

---

## B) Payload → Action → File Reference Table

| Payload Pattern | Action | Primary File | Key Lines |
|-----------------|--------|--------------|-----------|
| `pfm_{order_id}_{token}` | Open PayForMe payment page | [start.py](file://app/bot/handlers/start.py) | 109-123 |
| — | Parsing logic | [shop_payforme/router.py](file://app/bot/shop_payforme/router.py) | 457-466 |
| `ao_{order_id}` | Open admin order panel | [start.py](file://app/bot/handlers/start.py) | 125-137 |
| `order_{order_id}` | Show user order details | [start.py](file://app/bot/handlers/start.py) | 139-152 |
| `key_{raw}` / `club_{raw}` | Redeem access key | [access_control.py](file://app/bot/handlers/access_control.py) | 95-104, 254-273 |
| `LOOK_{code}` | Open look card | [start.py](file://app/bot/handlers/start.py) | 164-264 |
| — | Look service call | [start.py](file://app/bot/handlers/start.py) | 192-193 |
| — | Render look card | [ui/look_card.py](file://app/bot/ui/look_card.py) | 250-263 |
| `prod_{product_id}` | Open product by ID | [start.py](file://app/bot/handlers/start.py) | 271-293 |
| `{code}` (no prefix) | Open product by code | [start.py](file://app/bot/handlers/start.py) | 294-316 |
| — | `get_product_by_code()` | [catalog/service.py](file://app/domain/shop/catalog/service.py) | 358-391 |
| *(empty)* | Catalog home | [start.py](file://app/bot/handlers/start.py) | 383-393 |

---

## C) Recommendations for SocialBridge

### Recommended Payloads

| Use Case | Recommended Payload | Notes |
|----------|---------------------|-------|
| **Открыть товар** | `{PRODUCT_CODE}` | Просто код товара без префикса. Пример: `DRESS001` |
| **Открыть лук** | `LOOK_{CODE}` | Пример: `LOOK_SPRING2026` |
| **Открыть каталог** | *(no payload)* | `/start` без параметра = каталог |
| **Товар по ID** | `prod_{ID}` | Если известен только ID: `prod_123` |

### Best Practices

1. **Для товаров используйте код товара напрямую** (без префикса) — это fallback-поведение
2. **Для луков используйте `LOOK_` префикс** — строго `LOOK_` (uppercase) + код лука
3. **Для каталога** — просто пустой параметр или не указывать `start=` вовсе
4. **Длина payload** — держите до 50 символов для запаса (лимит Telegram: 64)

### Reserved Prefixes (Collision Risk)

| Prefix | Reserved For | Risk Level |
|--------|--------------|------------|
| `pfm_` | PayForMe | ⚠️ HIGH — will intercept |
| `ao_` | Admin orders | ⚠️ MEDIUM — admin only, но зарезервирован |
| `order_` | User orders | ⚠️ MEDIUM — user-specific |
| `key_` | Access keys | ⚠️ HIGH — will intercept |
| `club_` | Access keys | ⚠️ HIGH — will intercept |
| `LOOK_` | Looks | ✅ Use for looks |
| `prod_` | Product by ID | ✅ Use for products by ID |

### Suggested SocialBridge Payload Schema

```
# Товар по коду (рекомендуемый)
https://t.me/YOUR_BOT?start=DRESS001

# Лук
https://t.me/YOUR_BOT?start=LOOK_SUMMER2026

# Каталог (главная)
https://t.me/YOUR_BOT?start=

# Товар по ID (альтернативный)
https://t.me/YOUR_BOT?start=prod_456
```

### Future Considerations

1. **Campaign tracking** — сейчас нет поля `campaign` в аналитике. Если нужно отслеживать источник (ManyChat campaign), потребуется доработка:
   - Вариант A: Добавить `utm_` или `src_` prefix support
   - Вариант B: Расширить metadata в существующих событиях

2. **Новые префиксы** — если SocialBridge нужен собственный префикс (например `sb_`), он НЕ конфликтует с существующими и будет обработан как product code (не найдёт товар)

---

## D) Code References Summary

### Main Entry Point
```
app/bot/handlers/start.py:on_start()
├─ Line 97-99: Extract deep_link_param
├─ Line 109: Check pfm_
├─ Line 125: Check ao_
├─ Line 139: Check order_
├─ Line 154: Check key_/club_ (via handle_access_start_payload)
├─ Line 164: Check LOOK_
├─ Line 271: Check prod_
├─ Line 294: Fallback to product code
└─ Line 393: No param → show_catalog_home()
```

### Service Methods
- **Product by code:** `CatalogService.get_product_by_code()` → [service.py#L358](file://app/domain/shop/catalog/service.py#L358)
- **Look by code:** `LooksService.get_look_by_code()` → via `make_looks_service(session)`
- **PayForMe parse:** `parse_payforme_deeplink()` → [router.py#L461](file://app/bot/shop_payforme/router.py#L461)
- **Access key parse:** `extract_access_payload()` → [access_control.py#L99](file://app/bot/handlers/access_control.py#L99)

---

**End of Analysis**
