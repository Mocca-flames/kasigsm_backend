# KasI GSM — Build Phases

## Phase 0 — Foundation
*Goal: Running project skeleton, DB connected, migrations working*

- [x] Init FastAPI project, folder structure per PLAN.md
- [x] `.env` + `config.py` with Pydantic Settings
- [x] `database.py` — SQLModel engine + session dependency
- [x] Define all models: `Item`, `User`, `Order`, `OrderItem`, `Credential`, `Provider`, `ProviderListing`
- [x] Alembic init, generate and run first migration
- [x] Dockerfile + docker-compose (API + PostgreSQL)
- [x] Confirm `/health` route returns 200
- [x] Verify tables exist in DB after migration
- [x] Add `uid` column to `Item` with unique index
- [x] Add `Provider.is_active` toggle (supplier activation)

**Exit condition:** `docker compose up` starts cleanly, tables exist in DB.

---

## Phase 1 — Seed Script + Item Data
*Goal: Real data in DB, queryable; provider listings populated with UIDs and ZAR prices*

- [x] `scripts/seed_services.py` — simplified JSON schema (`title`, `price`, `currency`, `delivery_time`)
  - Generates `slug` from title server-side
  - Generates `uid` scoped to `PREFIX-SERVICETYPE-###` (e.g. `GSM-TOO-001`, `GSM-REM-001`)
  - Converts USD prices to ZAR using `USD_TO_ZAR_RATE` (hardcoded to 16.5)
  - First listing per item is `is_preferred = true`; subsequent providers get `false`
  - Re-running with same provider updates existing listings; new provider adds second listing
- [x] Seed `gsm_cheap.json` (Tool Rental — 44 services)
- [x] Seed `gsm_cheap_remote.json` (Remote Services — 225 services from same supplier)
- [x] Confirm items and listings visible via API
- [x] Multi-supplier support: same title stays one Item, multiple ProviderListings per item

**Exit condition:** Two runs with different service_type files each produce UIDs with unique prefixes; no duplicate Item entries.

---

## Phase 2 — Public API + Auth
*Goal: Anyone can browse; clients can register and log in*

- [x] `GET /items` — list visible items, filter by `item_type` and `category`
  - Filters to active suppliers only (`Provider.is_active` and `ProviderListing.is_active`)
  - Hides supplier names from client responses
- [x] `GET /items/{slug}` — single item detail with active supplier listings
- [x] `POST /auth/register` — hash password, create CLIENT user
- [x] `POST /auth/login` — verify, return signed JWT
- [x] `POST /search/validate` — validate search queries with category alias resolution
- [x] JWT decode middleware / dependency (`get_current_user`)
- [x] Role guard dependency (`require_admin`)

**Exit condition:** Swagger UI at `/docs` shows all routes; register + login + browse working.

---

## Phase 3 — Admin API
*Goal: Admin can manage the full catalogue from API*

- [x] `GET /admin/providers` — list all suppliers with `is_active` flag
- [x] `PATCH /admin/providers/{id}` — toggle supplier active/inactive
- [x] `GET /admin/items` — all items, including hidden and archived
  - Returns `provider_listings` with supplier names and cost prices for admin
- [x] `POST /admin/items` — create new item (service or product)
- [x] `PATCH /admin/items/{id}` — full edit
- [x] `PATCH /admin/items/{id}/markup` — set `price_markup`, recompute `price_final`
- [x] `PATCH /admin/items/{id}/visibility` — toggle `is_visible`
- [x] `DELETE /admin/items/{id}` — soft delete (`is_archived = true`)
- [x] `GET /admin/users` + `PATCH /admin/users/{id}` — activate/deactivate clients
- [x] `GET /admin/orders` — filterable by status
- [x] `PATCH /admin/orders/{id}/status` — manual override

**Exit condition:** Admin can toggle a supplier off, and it disappears from public listings immediately.

---

## Phase 4 — Orders (Client)
*Goal: Authenticated clients can place orders*

- [x] `POST /orders` — accepts `[{item_id, quantity}]`, creates Order + OrderItems in `PENDING`
  - Validates item is visible and in stock (for products)
  - Snapshots `price_final` into `OrderItem.unit_price`
  - Decrements stock for PRODUCT items
- [x] `GET /orders` — client's own order history
- [x] `GET /orders/{id}` — order detail + OrderItems

**Exit condition:** Client posts an order, order appears in DB as PENDING with correct amounts.

---

## Phase 5 — Payments
*Goal: Real ZAR payment flow, order fulfillment on success*

- [x] `POST /payments/initiate` — builds Paystack payment payload for a PENDING order, returns redirect URL
- [x] `POST /payments/verify` — verification handler
- [x] `GET /payments/verify/{reference}` — GET verification endpoint
- [x] Fulfillment logic (`services/fulfillment.py`)
  - For SERVICE items: pull unused `Credential` for each OrderItem, mark used, link to OrderItem
  - For PRODUCT items: (physical delivery — just mark FULFILLED, no credential pool needed)
- [x] `GET /orders/{id}` now returns assigned credential payloads for PAID service orders

**Exit condition:** Full flow: place order → initiate payment → simulate ITN → order PAID → credential assigned and visible on order detail.

---

## Phase 6 — Credential Management (Admin)
*Goal: Admin can stock and monitor the credential pool*

- [x] `POST /admin/credentials/bulk` — upload JSON/CSV batch of credentials for an item
  - Encrypts each payload with `ENCRYPTION_KEY` before storing
- [x] `GET /admin/credentials/{item_id}` — pool summary: total / used / remaining
- [x] Low-stock visibility: items with < 3 remaining credentials flagged in admin item list

**Exit condition:** Admin uploads 10 credentials for a service item, places 2 test orders, pool shows 8 remaining.

---

## Phase 7 — Client Portal (Frontend Demo)
*Goal: Working browser UI for the client-facing flow*

- [x] Product/Service listing page (fetches `GET /items`)
- [x] Item detail page with active supplier pricing (no supplier names exposed)
- [x] Register + Login forms (stores JWT in localStorage)
- [x] Cart → Checkout → Payment redirect
- [x] Order history page + credential reveal on PAID orders
- [x] Tech: React + plain fetch, kept thin

**Exit condition:** Full demo walkthrough in browser from browse → buy → view credentials.

---

## Phase 8 — Admin Dashboard (Frontend Demo)
*Goal: Visual admin panel over the admin API*

- [x] Login (admin JWT)
- [x] Items table — sortable, with inline markup edit, visibility toggle
- [x] Add / Edit item form
- [x] Orders table with status filter + manual status override
- [x] Credential pool view per item + bulk upload
- [x] User list
- [x] Providers table with toggle to activate/inactivate suppliers

**Exit condition:** Admin can onboard a new service, set markup, manage orders, upload credentials, and toggle suppliers without touching the DB directly.

---

## Phase 9 — Category Management & Supplier-Category Markups
*Goal: Centralised categories and supplier-specific markup overrides*

- [ ] `Category` lookup table + admin API
  - `GET /admin/categories` — list
  - `POST /admin/categories` — create (name + description)
  - `PATCH /admin/categories/{id}` — update name / is_active
  - `DELETE /admin/categories/{id}` — soft-deactivate if no dependent items
- [ ] `ProviderCategoryMarkup` model + admin API
  - `GET /admin/providers/{id}/markups` — list overrides
  - `POST /admin/providers/{id}/markups` — upsert override { category, price_markup }
  - `DELETE /admin/providers/{id}/markups/{category}` — remove override
- [ ] Price resolution service honoring overrides
  - `ProviderCategoryMarkup` > `Item.price_markup` > `0`
- [ ] Seed script auto-registers categories
- [ ] `POST/PATCH /admin/items` validates supplied category against `Category.name`; 400 with suggestions if missing
- [ ] Admin dashboard surfaces `effective_markup` and `markup_source`

**Exit condition:** Admin sets a R15 markup override on Supplier X for Category Y; all items in Category Y from Supplier X price at the override amount.

---

## Post-MVP (not in scope now)

- Email notifications on order PAID / credential delivered
- Wallet System for fast Orders
- SMS OTP on registration
- Bulk markup — apply markup % across a category
- Discount / promo codes
- Audit log for admin actions
- Rate limiting + brute-force protection on auth

