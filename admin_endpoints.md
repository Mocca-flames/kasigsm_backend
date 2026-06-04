# Admin Endpoints Documentation

> **Suite:** Admin API (`/admin`, `/wallet`, `/payments`, `/auth`, `/technician`, `/client`)  
> **Auth:** JWT Bearer via `Authorization: Bearer <token>`. All routes below marked `ADMIN` require admin role unless noted. `CLIENT` routes are available to authenticated clients.

---

## Auth

### Admin Login

- **Endpoint:** `POST /auth/login`
- **Method:** `POST`
- **Auth:** Not required
- **Request Body (form-data):**
  - `username`: `juniorflamebet@gmail.com`
  - `password`: `Maurice@12!`
- **Response (200 OK):**
  ```json
  { "access_token": "jwt_token_here", "token_type": "bearer" }
  ```

### Verify OTP

- **Endpoint:** `POST /auth/verify-otp`
- **Method:** `POST`
- **Auth:** Not required
- **Request Body:**
  ```json
  { "email": "string", "code": "string" }
  ```

### Resend OTP

- **Endpoint:** `POST /auth/resend-otp`
- **Method:** `POST`
- **Auth:** Not required
- **Query Parameters:** `email`

---

## Admin (`/admin`)

All admin routes are mounted with `Depends(require_admin)`.

### 1. List All Categories

- **Endpoint:** `GET /admin/categories`
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "name": "Tool Rental",
      "slug": "tool-rental",
      "description": null,
      "is_active": true,
      "created_at": "2026-06-02T10:00:00Z"
    }
  ]
  ```

### 2. Create Category

- **Endpoint:** `POST /admin/categories`
- **Query Parameters:**
  - `name` (string, required)
  - `description` (string, optional)
- **Response (200 OK):**
  ```json
  { "id": "uuid", "name": "Tool Rental", "slug": "tool-rental", "description": null, "is_active": true }
  ```

### 3. Update Category

- **Endpoint:** `PATCH /admin/categories/{id}`
- **Query Parameters:** `name` (string, optional), `is_active` (bool, optional)

### 4. Delete Category

- **Endpoint:** `DELETE /admin/categories/{id}`

### 5. List Provider Category Markups

- **Endpoint:** `GET /admin/providers/{id}/markups`
- **Response (200 OK):**
  ```json
  [ { "id": "uuid", "category": "Tool Rental", "price_markup": "15.00" } ]
  ```

### 6. Upsert Provider Category Markup

- **Endpoint:** `POST /admin/providers/{id}/markups`
- **Query Parameters:** `category`, `price_markup`

### 7. Delete Provider Category Markup

- **Endpoint:** `DELETE /admin/providers/{provider_id}/markups/{category}`
- **Note:** `{category}` must be URL-encoded.

### 8. Bulk Set Category Markup (Flat)

- **Endpoint:** `POST /admin/categories/{category_name}/markup/bulk`
- **Auth:** ADMIN
- **Query Parameters:** `markup` (decimal, required) — flat ZAR amount
- **Behavior:** Updates `Item.price_markup` for all non-archived items in the category.
- **Response (200 OK):**
  ```json
  {
    "message": "Bulk markup applied to 25 items",
    "category": "Tool Rental",
    "markup_type": "flat",
    "items_updated": 25,
    "updated_items": [
      { "id": "uuid", "title": "string", "new_price_markup": "15.00" }
    ]
  }
  ```

### 9. Bulk Set Category Markup (Percentage)

- **Endpoint:** `POST /admin/categories/{category_name}/markup/bulk-percentage`
- **Auth:** ADMIN
- **Query Parameters:** `percentage` (decimal, 0-100, required)
- **Behavior:** Calculates markup as `% of cost_price` from the active preferred listing for each item.
- **Response (200 OK):**
  ```json
  {
    "message": "Bulk percentage markup applied to 25 items",
    "category": "Tool Rental",
    "markup_type": "percentage",
    "items_updated": 25,
    "updated_items": [
      { "id": "uuid", "title": "string", "cost_price": "100.00", "new_price_markup": "15.00" }
    ]
  }
  ```

### 10. List All Items

- **Endpoint:** `GET /admin/items`
- **Query Parameters:** `offset` (int, default `0`), `limit` (int, default `100`)
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "slug": "string",
      "title": "string",
      "description": "string or null",
      "item_type": "SERVICE|PRODUCT",
      "category": "string",
      "thumbnail": "string or null",
      "media_url": "string",
      "price_final": "decimal",
      "currency": "string",
      "delivery_time": "string or null",
      "stock": "int or null",
      "is_visible": true,
      "low_stock": false,
      "provider_listings": [],
      "effective_markup": "decimal",
      "markup_source": "item|provider_category"
    }
  ]
  ```

### 11. Create Item

- **Endpoint:** `POST /admin/items`
- **Request Body:**
  ```json
  {
    "slug": "string (required)",
    "title": "string (required)",
    "description": "string (optional)",
    "item_type": "SERVICE|PRODUCT (required)",
    "category": "string (required)",
    "thumbnail": "string (optional)",
    "price_markup": "decimal (default: 0)",
    "currency": "string (default: ZAR)",
    "delivery_time": "string (optional)",
    "stock": "int (optional)"
  }
  ```

### 10. Edit Item

- **Endpoint:** `PATCH /admin/items/{item_id}`
- **Request Body:**
  ```json
  {
    "title": "string (optional)",
    "description": "string (optional)",
    "category": "string (optional)",
    "thumbnail": "string (optional)",
    "price_markup": "decimal (optional)",
    "currency": "string (optional)",
    "delivery_time": "string (optional)",
    "stock": "int (optional)",
    "is_visible": "bool (optional)"
  }
  ```

### 11. Set Item Markup

- **Endpoint:** `PATCH /admin/items/{item_id}/markup`
- **Query Parameters:** `markup` (decimal, required)

### 12. Toggle Item Visibility

- **Endpoint:** `PATCH /admin/items/{item_id}/visibility`
- **Query Parameters:** `is_visible` (bool, required)

### 13. Archive Item

- **Endpoint:** `DELETE /admin/items/{item_id}`
- **Response:** `{ "message": "Item archived" }`

### 14. List Users

- **Endpoint:** `GET /admin/users`

### 15. Update User Status

- **Endpoint:** `PATCH /admin/users/{user_id}`
- **Query Parameters:** `is_active` (bool, required)

### 16. List Orders

- **Endpoint:** `GET /admin/orders`
- **Query Parameters:** `status` (string, optional) — PENDING, PAID, FULFILLED, CANCELLED, REFUNDED
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "status": "PENDING|PAID|FULFILLED|CANCELLED|REFUNDED",
      "total_amount": "decimal"
    }
  ]
  ```

### 17. Update Order Status

- **Endpoint:** `PATCH /admin/orders/{order_id}/status`
- **Query Parameters:** `status` (string, required)

### 18. List Fulfillment Queue

- **Endpoint:** `GET /admin/orders/fulfillment-queue`
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "status": "PAID",
      "total_amount": "decimal",
      "currency": "string",
      "created_at": "datetime or null",
      "items": [
        {
          "id": "uuid",
          "item_id": "uuid",
          "quantity": 0,
          "unit_price": "decimal"
        }
      ]
    }
  ]
  ```

### 19. Get Order Readiness for Fulfillment

- **Endpoint:** `GET /admin/orders/{order_id}/ready`
- **Errors:** 404 if not found, 400 if not PAID

### 20. Fulfill Order Manually

- **Endpoint:** `POST /admin/orders/{order_id}/fulfill`
- **Request Body:**
  ```json
  { "credentials": [ { "order_item_id": "uuid", "payload": "string" } ] }
  ```
- **Response:** `{ "order_id": "uuid", "status": "fulfilled", "credentials_assigned": 0 }`

### 21. Reject (Cancel) Order

- **Endpoint:** `POST /admin/orders/{order_id}/reject`
- **Errors:** 400 if order is not PAID
- **Response:** `{ "order_id": "uuid", "status": "CANCELLED" }`

### 22. Bulk Upload Credentials

- **Endpoint:** `POST /admin/credentials/bulk?item_id={uuid}`
- **Request:** `multipart/form-data` with `credentials_file` (JSON or CSV)

### 23. Get Credential Pool

- **Endpoint:** `GET /admin/credentials/{item_id}`
- **Response (200 OK):**
  ```json
  {
    "item_id": "uuid",
    "item_title": "string",
    "total": 0,
    "used": 0,
    "remaining": 0,
    "low_stock": false
  }
  ```

### 24. List Banners

- **Endpoint:** `GET /admin/banners`

### 25. Create Banner

- **Endpoint:** `POST /admin/banners`
- **Request Body:**
  ```json
  {
    "slug": "string (required)",
    "title": "string (required)",
    "content": "string (required)",
    "image_url": "string (optional)",
    "link_url": "string (optional)",
    "is_active": true,
    "is_dismissible": true,
    "starts_at": "datetime (optional)",
    "ends_at": "datetime (optional)"
  }
  ```

### 26. Edit Banner

- **Endpoint:** `PATCH /admin/banners/{banner_id}`
  ```json
  { "slug|title|content|image_url|link_url|is_active|is_dismissible|starts_at|ends_at": "(optional)" }
  ```

### 27. Delete Banner

- **Endpoint:** `DELETE /admin/banners/{banner_id}`

### 28. Toggle Banner Active Status

- **Endpoint:** `PATCH /admin/banners/{banner_id}/toggle`
- **Query Parameters:** `is_active` (bool, required)

### 29. List Providers (Suppliers)

- **Endpoint:** `GET /admin/providers`
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "name": "string",
      "base_url": "string or null",
      "notes": "string or null",
      "is_active": true,
      "logo_url": "string or null"
    }
  ]
  ```

### 30. Toggle Provider Status

- **Endpoint:** `PATCH /admin/providers/{provider_id}`
- **Query Parameters:** `is_active` (bool, required)

### 31. Upload Media

- **Endpoint:** `POST /admin/upload`
- **Request:** `multipart/form-data` with `file` field
- **Response:** `{ "url": "/media/..." }`

### 32. Update Provider Logo

- **Endpoint:** `PATCH /admin/providers/{provider_id}/logo`
- **Request:** `multipart/form-data` with `file` field (optional) OR `logo_url` query param (optional)

### 33. Update Item Thumbnail

- **Endpoint:** `PATCH /admin/items/{item_id}/thumbnail`
- **Request:** `multipart/form-data` with `file` field (optional) OR `thumbnail_url` query param (optional)

### 34. List Technician Requests

- **Endpoint:** `GET /admin/technicians/requests`
- **Description:** Returns PENDING technician requests joined with user info.

### 35. List All Technicians

- **Endpoint:** `GET /admin/technicians`

### 36. Review Technician Request

- **Endpoint:** `POST /admin/technicians/{tech_id}/review`
- **Request Body:** `{ "action": "approve" | "reject" }`
- **Behavior:**
  - APPROVED → sets `Technician.status = APPROVED`, records `reviewed_at`/`reviewed_by`, sets `User.role = TECHNICIAN`
  - REJECTED → sets `Technician.status = REJECTED`

---

## Wallet (`/wallet`)

### 37. Get My Wallet

- **Endpoint:** `GET /wallet/me`
- **Auth:** CLIENT or ADMIN
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "balance": "decimal",
    "status": "ACTIVE|DISABLED",
    "client_ref": "string",
    "is_low_balance": true
  }
  ```

### 38. List Wallet Transactions

- **Endpoint:** `GET /wallet/transactions`
- **Auth:** CLIENT or ADMIN
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "amount": "decimal",
      "type": "CREDIT|DEBIT",
      "reference": "string",
      "description": "string",
      "created_at": "datetime or null"
    }
  ]
  ```

### 39. Request Wallet Top-Up

- **Endpoint:** `POST /wallet/top-up`
- **Auth:** CLIENT or ADMIN
- **Request Body:**
  ```json
  { "amount": "decimal", "reference": "string", "proof_note": "string (optional)" }
  ```
- **Constraints:** Amount must be between `WALLET_TOPUP_MIN` and `WALLET_TOPUP_MAX`, multiple of `WALLET_TOPUP_STEP` (from `.env`).

### 40. Pay for Order

- **Endpoint:** `POST /wallet/pay`
- **Auth:** CLIENT or ADMIN
- **Request Body:**
  ```json
  { "order_id": "uuid" }
  ```
- **Behavior:** Deducts order total from wallet, marks order PAID, sends payment email.
- **Response (200 OK):**
  ```json
  {
    "order_id": "uuid",
    "status": "PAID",
    "wallet_balance": "decimal",
    "wallet_status": "ACTIVE|DISABLED"
  }
  ```

### 41. List All Top-Ups (Admin)

- **Endpoint:** `GET /wallet/top-ups`
- **Auth:** ADMIN
- **Query Parameters:** `status` (string, optional) — PENDING, APPROVED, REJECTED, EXPIRED

### 42. Review Wallet Top-Up (Admin)

- **Endpoint:** `POST /wallet/top-ups/{top_up_id}/review`
- **Auth:** ADMIN
- **Request Body:**
  ```json
  { "approved": true, "note": "string (optional)" }
  ```
- **Behavior:** APPROVED → credits wallet and sends approval email. REJECTED → marks rejected.

### 43. Credit Wallet (Admin)

- **Endpoint:** `PATCH /wallet/{wallet_id}/credit`
- **Auth:** ADMIN
- **Request Body:**
  ```json
  { "amount": "decimal > 0", "description": "string (optional)" }
  ```
- **Response (200 OK):**
  ```json
  {
    "wallet_id": "uuid",
    "balance": "decimal",
    "status": "ACTIVE|DISABLED",
    "transaction_id": "uuid",
    "amount": "decimal"
  }
  ```

### 44. List All Wallets (Admin)

- **Endpoint:** `GET /wallet/all`
- **Auth:** ADMIN
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "user_id": "uuid",
      "email": "string",
      "client_ref": "string",
      "balance": "decimal",
      "status": "ACTIVE|DISABLED",
      "created_at": "datetime or null"
    }
  ]
  ```

---

## Payments

### 45. Initiate Payment

- **Endpoint:** `POST /payments/initiate`
- **Auth:** CLIENT or ADMIN
- **Request Body:**
  ```json
  { "order_id": "uuid", "return_url": "string (optional)" }
  ```
- **Behavior:** Initializes Paystack transaction. Uses `PAYSTACK_CALLBACK_URL` from `.env` when `return_url` is omitted.
- **Response (200 OK):**
  ```json
  { "authorization_url": "string", "reference": "string" }
  ```

### 46. Verify Payment

- **Endpoint:** `POST /payments/verify`
- **Auth:** Any
- **Request Body:**
  ```json
  { "reference": "string" }
  ```
- **Responses:**
  - `200` → `{ "status": "success", "order_id": "uuid" }`
  - `200` → `{ "status": "pending", "message": "Payment not successful" }`
  - `200` → `{ "status": "already_processed", "order_id": "uuid" }`
  - `400` → `{ "detail": "..." }`

### 47. Verify Payment (GET)

- **Endpoint:** `GET /payments/verify/{reference}`
- **Auth:** Any
- **Responses:** Same as POST verify.

---

## Technician Self-Service

### 48. Request Technician Role

- **Endpoint:** `POST /technician/technicians/request`
- **Auth:** CLIENT (non-admin)
- **Request Body:**
  ```json
  { "specialization": "string" }
  ```
- **Response (201 Created):** Returns `TechnicianResponse`

---

## Client Order

### 49. Get Credential

- **Endpoint:** `GET /client/credentials/{order_id}`
- **Auth:** CLIENT
- **Response (200 OK):**
  ```json
  { "credential": "string" }
  ```
- **Errors:** 400 if order not fulfilled or item is not SERVICE type.

---

## Public

### 50. Search Validation

- **Endpoint:** `POST /search/validate`
- **Auth:** Not required
- **Behavior:** Returns suggested category aliases for the supplied search terms.

### 51. Active Banners

- **Endpoint:** `GET /banners`
- **Auth:** Not required
- **Behavior:** Returns active banners whose `starts_at` / `ends_at` windows include now.

---

## Admin Item Detail — New Fields

**Endpoints:** `GET /admin/items`, `GET /admin/items/{id}`

New fields in `ItemDetail`:

| Field            | Type     | Values                        | Description                                            |
|------------------|----------|-------------------------------|--------------------------------------------------------|
| effective_markup | Decimal  | e.g. `"15.00"`                | Actual markup applied (override or item fallback)      |
| markup_source    | string   | `"item"` or `"provider_category"` | Where effective markup came from                       |

> These fields are **admin-only**; absent from `GET /items` and client order responses.

---

## Pricing Rules (Admin Display Logic)

Server-side `price_final` resolution:

1. **Active preferred ProviderListing exists:**
   - Check `ProviderCategoryMarkup` for (provider, category) → use that markup
   - Else fall back to `Item.price_markup`
   - `price_final = cost_price + effective_markup`
2. **No active preferred listing:**
   - `price_final = Item.price_markup`

`OrderItem.unit_price` is a snapshot and never changes after order creation.

---

## Category Validation on Item Create/Edit

- **Endpoints:** `POST /admin/items`, `PATCH /admin/items/{id}`
- **Behavior:** `category` validated against `Category.name`. Returns 400 with suggestion list if missing.

---

## Admin Dashboard — Frontend → API Summary

| Dashboard Page           | Frontend Route          | Underlying Admin API Route(s)                              |
|--------------------------|-------------------------|------------------------------------------------------------|
| Dashboard                | `/`                     | `GET /admin/stats/summary`, `GET /admin/orders`, `GET /admin/clients` |
| Items                    | `/items`                | `GET /admin/items`, `POST /admin/items`, `PATCH /admin/items/{id}`, `PATCH /admin/items/{id}/markup`, `PATCH /admin/items/{id}/visibility`, `DELETE /admin/items/{id}` |
| Services & Pricing       | `/services`             | `GET /admin/items`, `GET /admin/providers`, `GET /admin/providers/{id}/markups`, `POST /admin/providers/{id}/markups`, `DELETE /admin/providers/{id}/markups/{category}` |
| Suppliers                | `/suppliers`            | `GET /admin/providers`, `PATCH /admin/providers/{id}`       |
| Categories               | `/categories`           | `GET /admin/categories`, `POST /admin/categories`, `PATCH /admin/categories/{id}`, `DELETE /admin/categories/{id}` |
| Provider Markups         | `/provider-markups`     | `GET /admin/providers/{id}/markups`, `POST /admin/providers/{id}/markups`, `DELETE /admin/providers/{id}/markups/{category}` |
| Orders                   | `/orders`               | `GET /admin/orders`, `PATCH /admin/orders/{id}/status`, `POST /admin/orders/{id}/fulfill`, `POST /admin/orders/{id}/reject` |
| Fulfillment Queue        | `/fulfillment-queue`    | `GET /admin/orders/fulfillment-queue`, `GET /admin/orders/{id}/ready` |
| Repair Orders            | `/repair-orders`        | Same as `/orders`                                           |
| Order Detail             | `/orders/:orderId`      | `GET /admin/orders/{id}`, status/fulfill actions            |
| Credentials              | `/credentials`          | `POST /admin/credentials/bulk`, `GET /admin/credentials/{item_id}`, `PATCH /admin/items/{id}/markup` |
| Users                    | `/users`                | `GET /admin/users`, `PATCH /admin/users/{id}`               |
| Customers                | `/customers`            | `GET /admin/clients`, user management as above             |
| Technicians              | `/technicians`          | `GET /admin/technicians/requests`, `GET /admin/technicians`, `POST /admin/technicians/{tech_id}/review` |
| Banners                  | `/banners`              | `GET /admin/banners`, `POST /admin/banners`, `PATCH /admin/banners/{id}`, `DELETE /admin/banners/{id}`, `PATCH /admin/banners/{id}/toggle` |
| Settings                 | `/settings`             | Admin user/profile settings, supplier toggles               |

---

## Analytics (Cloudflare)

### 52. Visitor Summary (24h)

- **Endpoint:** `GET /admin/analytics/visitors`
- **Auth:** ADMIN
- **Response:**
  ```json
  {
    "period_start": "ISO datetime",
    "period_end": "ISO datetime",
    "total_requests": 0,
    "bandwidth_bytes": 0,
    "unique_visitors": 0
  }
  ```

---

## Media & Storage (Cloudflare R2)

Current media handling is local (`/media`). To move media to Cloudflare R2:

1. **Deploy a bucket** in Cloudflare R2 and create an API token with `Object Read & Write`.
2. **Add to `.env`:**
   ```env
   CF_R2_ACCOUNT_ID="..."
   CF_R2_ACCESS_KEY_ID="..."
   CF_R2_SECRET_ACCESS_KEY="..."
   CF_R2_BUCKET_NAME="gsm-media"
   CDN_DOMAIN="https://cdn.example.com"
   ```
3. **Implementation notes:**
   - Replace local `_save_upload()` in `app/routers/admin.py` with an R2 PUT using `boto3` / `boto3-stubs` or Cloudflare's Python SDK.
   - Return `{ "url": "{CDN_DOMAIN}/{key}" }` from `POST /admin/upload`.
   - Update `resolve_media_url()` to prefix existing paths with `CDN_DOMAIN`.
4. **Security:** Keep R2 bucket private; serve only via CDN domain.
