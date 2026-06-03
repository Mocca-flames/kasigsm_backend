# KasI GSM — Platform Plan

## Overview

A lean FastAPI backend powering two surfaces:
- **Client Portal** — browse, authenticate, buy services/products, pay in ZAR
- **Admin Dashboard** — manage inventory, markup, visibility, orders, and supplier availability

---

## Stack

| Layer | Choice | Reason |
|---|---|---|
| API | FastAPI | Async, typed, auto-docs |
| ORM | SQLModel | Thin Pydantic+SQLAlchemy wrapper, fits FastAPI natively |
| DB | PostgreSQL | Relational, handles products + services cleanly |
| Auth | JWT (python-jose) + bcrypt | Stateless, simple |
| Payments | PayFast / Ozow / Paystack | ZAR, local |
| Migrations | Alembic | Standard, pairs with SQLModel |
| Seeding | Standalone Python script | CLI, no framework overhead |
| Hosting | Docker Compose on GCP CE | Already decided |

---

## Data Model

### `Item` (unified table for Services and Products)

```
id            UUID PK
uid           str UNIQUE INDEX        # Human-readable code generated during seeding
slug          str UNIQUE INDEX
title         str
description   str | null
item_type     enum: SERVICE | PRODUCT
category      str                      # Validated against Category.name at API layer
thumbnail     str | null
price_markup  Decimal                  # Admin-set markup amount (ZAR) — fallback
currency      str DEFAULT "ZAR"        # Always ZAR in DB; suppliers may quote other currencies
delivery_time str | null
stock         int | null               # null = unlimited (services)
is_visible    bool DEFAULT true
is_archived   bool DEFAULT false
meta          JSON | null
created_at    datetime
updated_at    datetime
```

> Services have `stock = null`. Products have `stock >= 0`.
> `price_markup` is set per-item by Admin. `price_final` is derived.
> `uid` is generated per supplier + service_type scope during seed (e.g. `GSM-TOO-001`).

---

### `Category` (lookup table)

```
id            UUID PK
name          str UNIQUE NOT NULL      # Canonical name (e.g. "Tool Rental")
slug          str UNIQUE NOT NULL INDEX
description   str | null
is_active     bool DEFAULT true
created_at    datetime
```

> `Item.category` remains a plain string. Validation happens at the API layer
> (`POST/PATCH /admin/items` and seed script). FK constraint deferred.

---

### `ProviderCategoryMarkup`

```
id              UUID PK
provider_id     UUID INDEX              # FK → provider.id
category        str NOT NULL INDEX
price_markup    Decimal NOT NULL
```

> Unique constraint on (`provider_id`, `category`).
> Admin-only override: when resolving price for a preferred listing, use this markup
> if an override exists for that supplier + item category; else fall back to `Item.price_markup`.

---

### `Provider`

```
id            UUID PK
name          str UNIQUE               # e.g. "GSM Cheap", "GSM Tech Africa"
base_url      str | null
notes         str | null
is_active     bool DEFAULT true        # Admin can hide/show a supplier
created_at    datetime
```

### `ProviderListing` *(junction — Item ↔ Provider)*

```
id              UUID PK
item_id         FK → Item
provider_id     FK → Provider
external_id     str | null
cost_price      Decimal                  # ZAR-normalized from supplier currency
is_preferred    bool DEFAULT false
is_active       bool DEFAULT true
created_at      datetime
updated_at      datetime
```

> Each provider that stocks a tool gets one `ProviderListing` row under that Item's ID.
> The first listing created for an item is marked `is_preferred = true`.
> If that provider is deactivated, admin can promote another listing.
> `price_final = preferred_ProviderListing.cost_price + Item.price_markup`

---

### `User`

```
id            UUID PK
email         str UNIQUE
password_hash str
role          enum: CLIENT | ADMIN
is_active     bool DEFAULT true
created_at    datetime
```

---

### `Order`

```
id              UUID PK
user_id         FK → User
status          enum: PENDING | PAID | FULFILLED | CANCELLED | REFUNDED
payment_ref     str | null
payment_gateway str | null
total_amount    Decimal
currency        str DEFAULT "ZAR"
created_at      datetime
updated_at      datetime
```

---

### `OrderItem`

```
id            UUID PK
order_id      FK → Order
item_id       FK → Item
quantity      int
unit_price    Decimal       # Snapshot of price_final at time of purchase
```

---

### `Credential`

```
id            UUID PK
item_id       FK → Item
payload       str (encrypted)
is_used       bool DEFAULT false
order_item_id FK → OrderItem | null
assigned_at   datetime | null
```

---

## API Surface

### Public (no auth)

```
GET  /items                  # List visible items (filter: type, category) — active suppliers only
GET  /items/{slug}           # Single item detail — active suppliers + prices, no supplier names
POST /auth/register
POST /auth/login             # Returns JWT
POST /search/validate        # Validate search query/category with live matches
```

### Client (JWT required, role=CLIENT)

```
GET  /me                     # Profile
POST /orders                 # Create order from cart payload
GET  /orders                 # My order history
GET  /orders/{id}            # Order detail + fulfilled credentials
POST /payments/initiate      # Returns PayFast/Ozow/Paystack redirect URL
POST /payments/notify        # Webhook from payment gateway (ITN)
```

### Admin (JWT required, role=ADMIN)

```
GET    /admin/providers
POST   /admin/providers
PATCH  /admin/providers/{id}                    # Toggle is_active

GET    /admin/items/{id}/providers
POST   /admin/items/{id}/providers
PATCH  /admin/items/{id}/providers/{listing_id}/prefer

GET    /admin/items
POST   /admin/items
PATCH  /admin/items/{id}
DELETE /admin/items/{id}

PATCH  /admin/items/{id}/markup
PATCH  /admin/items/{id}/visibility

GET    /admin/categories
POST   /admin/categories
PATCH  /admin/categories/{id}
DELETE /admin/categories/{id}

GET    /admin/providers/{id}/markups
POST   /admin/providers/{id}/markups
DELETE /admin/providers/{id}/markups/{category}

GET    /admin/orders
PATCH  /admin/orders/{id}/status

POST   /admin/credentials/bulk
GET    /admin/credentials/{item_id}

GET    /admin/users
PATCH  /admin/users/{id}
```

---

## Markup Logic

Admin sets `price_markup` (flat ZAR amount) per item.
Supplier-category markup override takes precedence when defined for the preferred listing's provider + item category.

Resolution order (deterministic):
1. `ProviderCategoryMarkup.price_markup` for (provider, item.category)
2. `Item.price_markup` fallback
3. `0` fallback (when no preferred listing exists)

`price_final = preferred_ProviderListing.cost_price + effective_markup`

`cost_price` lives on `ProviderListing`. The client always sees only `price_final`.
Admin changes supplier preference by promoting another listing (`is_preferred = true`).

Admin `ItemDetail` responses also expose `effective_markup` and `markup_source` (`item` or `provider_category`).

---

## Multi-Supplier & Supplier Toggle Rules

- Same service title from multiple suppliers is **one Item** with multiple active `ProviderListing` rows.
- Public APIs **only** see listings where `ProviderListing.is_active = true` **and** `Provider.is_active = true`.
- Supplier names are **never** exposed to clients.
- Admin can deactivate a supplier at any time via `PATCH /admin/providers/{id}`.
- Seed script preserves the first-listing-is-preferred rule; re-running with a different provider adds a second listing without touching the first.

---

## Currency Normalization

- `USD_TO_ZAR_RATE` is set in `app.config.Settings` (currently hardcoded to `16.5`).
- Seed script converts all USD `price` values to ZAR before writing `ProviderListing.cost_price`.
- `Item.currency` is always `ZAR`.

---

## Seed Script

`scripts/seed_services.py`:

- Arguments:
  - `--file` — path to supplier JSON (minimal schema: `supplier`, `services_type`, `services[title, price, currency, delivery_time]`)
  - `--provider` — override supplier name (optional)
- For every service:
  1. Upsert `Item` by `slug` (auto-generated from title). Create-only: same title = same Item.
  2. Generate `uid` scoped to `PREFIX-SERVICETYPE-###` (e.g. `GSM-TOO-001`).
  3. Upsert `ProviderListing` for the provider; first listing per item is `is_preferred = true`.
  4. Convert USD to ZAR using `USD_TO_ZAR_RATE`; store in `cost_price`.

Run per supplier JSON:
```
python scripts/seed_services.py --file data/gsm_cheap.json
python scripts/seed_services.py --file data/gsm_cheap_remote.json
```

---

## Configuration (`.env`)

```
DATABASE_URL
SECRET_KEY
JWT_EXPIRE_MINUTES
PAYFAST_MERCHANT_ID
PAYFAST_MERCHANT_KEY
PAYFAST_PASSPHRASE
OZOW_SITE_CODE
OZOW_PRIVATE_KEY
ENCRYPTION_KEY
USD_TO_ZAR_RATE=16.5
```

---

## Project Layout

```
kasigsm-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── item.py
│   │   ├── user.py
│   │   ├── order.py
│   │   └── credential.py
│   ├── routers/
│   │   ├── public.py
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── client.py
│   │   ├── payments.py
│   │   └── search.py
│   ├── schemas/
│   │   ├── item.py
│   │   ├── search.py
│   │   └── payment.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── fulfillment.py
│   │   └── search.py
│   └── utils/
│       ├── security.py
│       └── encryption.py
├── scripts/
│   ├── seed_services.py
│   └── seed_products.py
├── alembic/
├── data/
│   ├── gsm_cheap.json
│   └── gsm_cheap_remote.json
├── docker-compose.yml
├── Dockerfile
└── .env
```

---

## Search Validation

```
POST /search/validate
Body: { q?, category?, service_type?, location?, item_ids? }
Response: { valid, total_matches, items }
```

Supports category alias resolution (e.g. `remote` → `Remote Services`, `tool` → `Tool Rental`).

---

## Out of Scope (this version)

- Subscription / recurring billing
- Discount codes
- Email notifications (add post-MVP with background tasks)
- SMS OTP (add post-MVP)
