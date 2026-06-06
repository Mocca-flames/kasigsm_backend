# Client Endpoints Documentation

> **Suite:** Client API (`/auth`, `/items`, `/orders`, `/payments`, `/wallet`, `/promo-codes`, `/technician`, `/search`, `/banners`, `/device`, `/tools`)  
> **Auth:** JWT Bearer via `Authorization: Bearer <token>`. Public endpoints accept any caller. Authenticated routes require a valid JWT issued to a `CLIENT` role account.

---

## Auth

### Register

- **Endpoint:** `POST /auth/register`
- **Method:** `POST`
- **Auth:** Not required
- **Rate Limit:** Max 3 attempts per 15 minutes per IP
- **Request Body:**
  ```json
  {
    "email": "string (required)",
    "password": "string (required)"
  }
  ```
- **Response (200 OK):**
  ```json
  { "id": "uuid", "email": "string", "message": "Account created. Please verify your email with the OTP sent." }
  ```
- **Side effects:** Creates an inactive user record, generates a 6-digit OTP, sends an OTP email, and initialises a wallet for the new user.
- **Errors:**
  - `400` — "Email already registered"
  - `400` — "Email registered but not verified. Please check your inbox or resend OTP."

### Verify OTP

- **Endpoint:** `POST /auth/verify-otp`
- **Method:** `POST`
- **Auth:** Not required
- **Rate Limit:** Max 3 attempts per 15 minutes per IP
- **Request Body:**
  ```json
  { "email": "string", "code": "string" }
  ```
- **Response (200 OK):**
  ```json
  { "id": "uuid", "email": "string", "message": "Email verified. Account activated." }
  ```
- **Side effects:** Sets `User.is_active = true`, sends a welcome email.
- **Errors:**
  - `400` — "Invalid or expired OTP"
  - `404` — "User not found"

### Resend OTP

- **Endpoint:** `POST /auth/resend-otp`
- **Method:** `POST`
- **Auth:** Not required
- **Query Parameters:** `email` (string, required)
- **Rate Limit:** Max 3 attempts per 15 minutes per IP
- **Response (200 OK):**
  ```json
  { "message": "OTP resent" }
  ```
- **Errors:**
  - `404` — "User not found"
  - `400` — "Account already verified"

### Login

- **Endpoint:** `POST /auth/login`
- **Method:** `POST`
- **Auth:** Not required
- **Rate Limit:** Max 5 attempts per 15 minutes per IP; 15-minute lockout after 5 failures
- **Request Body (form-data / OAuth2):**
  - `username` (email): `string`
  - `password`: `string`
- **Response (200 OK):**
  ```json
  { "access_token": "string", "token_type": "bearer" }
  ```
- **Errors:**
  - `400` — Rate limit exceeded / login lockout
  - `401` — "Invalid credentials"
  - `403` — "Account not verified. Please verify your email first."

---

## Public Catalog

### List Items

- **Endpoint:** `GET /items`
- **Method:** `GET`
- **Auth:** Not required
- **Query Parameters:**
  - `item_type` (`SERVICE|PRODUCT`, optional) — filter by item type
  - `category` (string, optional) — filter by resolved category name or alias
  - `search` (string, optional) — search by title or slug tokens for phones/devices/brands (e.g. "iphone", "samsung", "redmi")
- **Behavior:**
  - Only returns items where `is_visible=true`, `is_archived=false`, and at least one active `ProviderListing` exists under an active `Provider`.
  - `search` ranks results by full-text slug token matching and title relevance.
  - `category` is resolved through the alias system before filtering.
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "uid": "string or null",
      "slug": "string",
      "title": "string",
      "description": "string or null",
      "item_type": "SERVICE|PRODUCT",
      "category": "string",
      "thumbnail": "string or null",
      "media_url": "string or null",
      "price_final": "decimal",
      "currency": "string",
      "delivery_time": "string or null",
      "stock": "int or null",
      "meta": {
        "display_title": "string or null",
        "rent_duration": "string or null",
        "rent_notes": ["string"]
      } or null
    }
  ]
  ```

### Get Item Detail

- **Endpoint:** `GET /items/{slug}`
- **Method:** `GET`
- **Auth:** Not required
- **Path Parameters:**
  - `slug` (string, required) — URL-friendly item slug
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "uid": "string or null",
    "slug": "string",
    "title": "string",
    "description": "string or null",
    "item_type": "SERVICE|PRODUCT",
    "category": "string",
    "thumbnail": "string or null",
    "media_url": "string or null",
    "price_final": "decimal",
    "currency": "string",
    "delivery_time": "string or null",
    "stock": "int or null",
    "is_visible": true,
    "meta": {
      "display_title": "string or null",
      "rent_duration": "string or null",
      "rent_notes": ["string"]
    } or null
  }
  ```

### Get Item Detail

- **Endpoint:** `GET /items/{slug}`
- **Method:** `GET`
- **Auth:** Not required
- **Path Parameters:**
  - `slug` (string, required) — URL-friendly item slug
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "uid": "string or null",
    "slug": "string",
    "title": "string",
    "description": "string or null",
    "item_type": "SERVICE|PRODUCT",
    "category": "string",
    "thumbnail": "string or null",
    "media_url": "string or null",
    "price_final": "decimal",
    "currency": "string",
    "delivery_time": "string or null",
    "stock": "int or null",
    "is_visible": true,
    "meta": {
      "display_title": "string or null",
      "rent_duration": "string or null",
      "rent_notes": ["string"]
    } or null,
    "provider_listings": [
      {
        "provider": "string",
        "cost_price": "decimal",
        "currency": "string",
        "is_preferred": true
      }
    ]
  }
  ```
- **Errors:**
  - `404` — "Item not found" (archived, not visible, or does not exist)

### Search Validation

- **Endpoint:** `POST /search/validate`
- **Method:** `POST`
- **Auth:** Not required
- **Request Body:**
  ```json
  {
    "q": "string (optional)",
    "category": "string (optional)",
    "service_type": "string (optional)",
    "location": "string (optional)",
    "item_ids": ["string (optional)"]
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "valid": true,
    "total_matches": 0,
    "items": [
      {
        "id": "uuid",
        "title": "string",
        "category": "string"
      }
    ]
  }
  ```
- **Behavior:** Returns matching items filtered by the supplied criteria. `q` does a case-insensitive `ILIKE` search on title; `category`, `item_ids`, and `service_type` are exact-match filters.

### List Active Banners

- **Endpoint:** `GET /banners`
- **Method:** `GET`
- **Auth:** Not required
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "slug": "string",
      "title": "string",
      "content": "string",
      "image_url": "string or null",
      "link_url": "string or null",
      "is_dismissible": true,
      "starts_at": "datetime or null",
      "ends_at": "datetime or null"
    }
  ]
  ```
- **Behavior:** Only banners with `is_active=true` whose `starts_at` is in the past (or unset) and `ends_at` is in the future (or unset) are returned. Banners with a past `ends_at` or a future `starts_at` are excluded.
- **Recommended image dimensions:** `1920 x 600` px (landscape). Accepted formats: `png`, `jpg`, `jpeg`, `webp`, `gif`.

---

## Orders

### Create Order

- **Endpoint:** `POST /orders`
- **Method:** `POST`
- **Auth:** Required (client JWT)
- **Request Body:**
  ```json
  {
    "items": [
      { "item_id": "uuid", "quantity": 1 }
    ],
    "promo_code": "string (optional)"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "status": "PENDING",
    "subtotal": "decimal",
    "discount_code": "string or null",
    "discount_amount": "decimal",
    "total_amount": "decimal",
    "currency": "string",
    "created_at": "datetime",
    "items": [
      {
        "id": "uuid",
        "item_id": "uuid",
        "quantity": 1,
        "unit_price": "decimal",
        "credentials": null
      }
    ]
  }
  ```
- **Behavior:**
  - Validates each item is visible, not archived, and has sufficient stock.
  - `quantity` units are deducted from stock at order creation.
  - Applies a promo code if supplied; failures return `400`.
  - `total_amount` is `max(0, subtotal - discount_amount)`.
- **Errors:**
  - `400` — "{item_id} not available"
  - `400` — "Insufficient stock for item {item_id}"
  - `400` — PromoValidationError detail string

### List My Orders

- **Endpoint:** `GET /orders`
- **Method:** `GET`
- **Auth:** Required (client JWT)
- **Response (200 OK):**
  ```json
  [
    {
      "id": "uuid",
      "status": "PENDING|PAID|FULFILLED|CANCELLED|REFUNDED",
      "subtotal": "decimal",
      "discount_code": "string or null",
      "discount_amount": "decimal",
      "total_amount": "decimal",
      "currency": "string",
      "created_at": "datetime",
      "items": [
        {
          "id": "uuid",
          "item_id": "uuid",
          "quantity": 1,
          "unit_price": "decimal",
          "credentials": null
        }
      ]
    }
  ]
  ```
- **Behavior:** Returns all orders where `Order.user_id` matches the authenticated user's ID.
- **Errors:**
  - `403` — Not authenticated

### Get Order Detail

- **Endpoint:** `GET /orders/{order_id}`
- **Method:** `GET`
- **Auth:** Required (client JWT)
- **Path Parameters:**
  - `order_id` (string, required) — Order UUID
- **Response (200 OK):** Same shape as a single `OrderPublic` object.
- **Behavior:** When `status=PAID`, encrypted credential payloads are decrypted and included in each `OrderItemPublic.credentials` list.
- **Errors:**
  - `403` — Not authenticated
  - `404` — "Order not found" (also enforces ownership: `Order.user_id == user.id`)

---

## Payments

### Initiate Payment (Paystack)

- **Endpoint:** `POST /payments/initiate`
- **Method:** `POST`
- **Auth:** Required (client JWT)
- **Request Body:**
  ```json
  { "order_id": "uuid", "return_url": "string (optional)" }
  ```
- **Response (200 OK):**
  ```json
  { "authorization_url": "string", "reference": "string" }
  ```
- **Behavior:**
  - Converts order total to kobo (ZAR × 100) and calls the Paystack Transaction Initialize API.
  - Stores `payment_ref` and `payment_gateway="paystack"` on the order.
  - Falls back to `.env` `PAYSTACK_CALLBACK_URL` when `return_url` is omitted.
- **Errors:**
  - `403` — Not authenticated
  - `404` — "Order not found" (also enforces ownership)
  - `400` — "Order is not pending" (must be `PENDING`)
  - `400` — "Payment initiation failed" (from Paystack response)

### Verify Payment (POST)

- **Endpoint:** `POST /payments/verify`
- **Method:** `POST`
- **Auth:** Any (public)
- **Request Body:**
  ```json
  { "reference": "string" }
  ```
- **Response Shapes (200 OK):**
  - **Pending:**
    ```json
    { "status": "pending", "message": "Payment not successful" }
    ```
  - **Already processed:**
    ```json
    { "status": "already_processed", "message": "Order already paid", "order_id": "uuid" }
    ```
  - **Success:**
    ```json
    { "status": "success", "order_id": "uuid" }
    ```
- **Behavior:** Calls Paystack Transaction Verify API. On success, marks order `PAID` and sends order-paid email. Verifies paid amount matches `Order.total_amount`.
- **Errors:**
  - `400` — "Verification failed" (from Paystack)
  - `404` — "Order not found"
  - `400` — "Payment not successful" (transaction status ≠ success)
  - `400` — "Amount mismatch" (paid amount ≠ order total)

### Verify Payment (GET)

- **Endpoint:** `GET /payments/verify/{reference}`
- **Method:** `GET`
- **Auth:** Any (public)
- **Path Parameters:**
  - `reference` (string, required) — Paystack payment reference (e.g. `PAY-xxxxxxxxxxxx`)
- **Response:** Same three shapes as `POST /payments/verify`.
- **Behavior:** Same as POST verify; designed for browser redirect callbacks.
- **Errors:** Same as POST verify.

---

## Wallet

### Get My Wallet

- **Endpoint:** `GET /wallet/me`
- **Method:** `GET`
- **Auth:** Required (client JWT)
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "balance": "decimal",
    "status": "ACTIVE|DISABLED",
    "client_ref": "string or null",
    "is_low_balance": true
  }
  ```
- **Behavior:** Retrieves the wallet linked to the authenticated user, creating one if absent. `is_low_balance` is `true` when balance ≤ `WALLET_LOW_BALANCE_THRESHOLD`.
- **Errors:**
  - `403` — Not authenticated

### Request Wallet Top-Up

- **Endpoint:** `POST /wallet/top-up`
- **Method:** `POST`
- **Auth:** Required (client JWT)
- **Request Body:**
  ```json
  {
    "amount": "decimal (required)",
    "reference": "string (optional)",
    "proof_note": "string (optional)"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "id": "uuid",
    "wallet_id": "uuid",
    "amount": "decimal",
    "reference": "string",
    "status": "PENDING",
    "client_ref": "string",
    "message": "Top-up request submitted. Admin will review shortly."
  }
  ```
- **Constraints:**
  - `amount` must be between `WALLET_TOPUP_MIN` and `WALLET_TOPUP_MAX` (from `.env`)
  - `amount` must be a multiple of `WALLET_TOPUP_STEP` (from `.env`)
- **Errors:**
  - `403` — Not authenticated
  - `400` — "Amount must be a multiple of {STEP}"
  - `400` — "Amount must be between {MIN} and {MAX}"

### List Wallet Transactions

- **Endpoint:** `GET /wallet/transactions`
- **Method:** `GET`
- **Auth:** Required (client JWT)
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
- **Behavior:** Returns all transactions for the authenticated user's wallet, newest first.
- **Errors:**
  - `403` — Not authenticated

### Pay for Order with Wallet

- **Endpoint:** `POST /wallet/pay`
- **Method:** `POST`
- **Auth:** Required (client JWT)
- **Request Body:**
  ```json
  { "order_id": "uuid" }
  ```
- **Response (200 OK):**
  ```json
  {
    "order_id": "uuid",
    "status": "PAID",
    "wallet_balance": "decimal",
    "wallet_status": "ACTIVE|DISABLED"
  }
  ```
- **Behavior:** Debits the order total from the wallet, sets `order.payment_gateway="wallet"`, marks the order `PAID`, and sends an order-paid email.
- **Errors:**
  - `403` — Not authenticated
  - `404` — "Order not found" (also enforces ownership)
  - `400` — "Order is not pending" (must be `PENDING`)
  - `400` — Insufficient balance or other debit error detail

---

## Promo Codes

### Validate Promo Code

- **Endpoint:** `POST /promo-codes/validate`
- **Method:** `POST`
- **Auth:** Authenticated user (CLIENT or ADMIN) — `user_id` is `None` for anonymous callers (graceful fallback)
- **Request Body:**
  ```json
  { "code": "WELCOME20", "order_amount": "200.00" }
  ```
- **Response (200 OK) — valid:**
  ```json
  {
    "valid": true,
    "code": "WELCOME20",
    "discount_type": "PERCENTAGE|FIXED_AMOUNT",
    "discount_value": "20.00",
    "discount_amount": "40.00",
    "message": null
  }
  ```
- **Response (200 OK) — invalid:**
  ```json
  {
    "valid": false,
    "code": "WELCOME20",
    "discount_type": "",
    "discount_value": "0",
    "discount_amount": "0",
    "message": "This promo code has expired"
  }
  ```
- **Behavior:** Runs the full validation chain: existence, active flag, date window, max uses, per-user limit, min order amount, and category/item applicability. Does not create an order or usage record.
- **Errors:** None — validation failures are returned in the response body with `valid=false`.

### Apply Promo Code (Cart Preview)

- **Endpoint:** `POST /promo-codes/apply`
- **Method:** `POST`
- **Auth:** Required (client JWT)
- **Request Body:**
  ```json
  { "code": "WELCOME20" }
  ```
- **Response (200 OK) — valid:**
  ```json
  {
    "valid": true,
    "code": "WELCOME20",
    "discount_type": "PERCENTAGE|FIXED_AMOUNT",
    "discount_value": "20.00",
    "discount_amount": "40.00",
    "final_amount": "160.00"
  }
  ```
- **Response (200 OK) — invalid:**
  ```json
  {
    "valid": false,
    "code": "WELCOME20",
    "discount_type": "",
    "discount_value": "0",
    "discount_amount": "0",
    "final_amount": "0",
    "message": "Promo code not found"
  }
  ```
- **Behavior:** Same validation as `/promo-codes/validate` but also computes the final discounted amount. Does **not** create an order or usage record — use for cart preview only.
- **Errors:**
  - `403` — Not authenticated

---

## Technician Self-Service

### Request Technician Role

- **Endpoint:** `POST /technician/technicians/request`
- **Method:** `POST`
- **Auth:** Required (CLIENT role; non-admin)
- **Request Body:**
  ```json
  { "specialization": "string (optional)" }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": "uuid",
    "user_id": "uuid",
    "email": "string",
    "role": "CLIENT",
    "status": "PENDING",
    "specialization": "string or null",
    "created_at": "datetime or null"
  }
  ```
- **Behavior:** Creates a `Technician` record with `status=PENDING`. An admin must review the request via `POST /admin/technicians/{tech_id}/review` to change the status and promote the user to the `TECHNICIAN` role.
- **Errors:**
  - `400` — "Admins cannot request technician access"
  - `400` — "Pending technician request already exists"

---

## Device Scanner

### List Issues

- **Endpoint:** `GET /device/issues`
- **Method:** `GET`
- **Auth:** Not required
- **Response (200 OK):**
  ```json
  [
    { "slug": "frp", "label": "FRP Lock" },
    { "slug": "network_lock", "label": "Network Lock" },
    { "slug": "mdm", "label": "MDM Lock" },
    { "slug": "icloud", "label": "iCloud Lock" },
    { "slug": "password", "label": "Password / Pattern Lock" },
    { "slug": "corrupt_os", "label": "Corrupt OS" }
  ]
  ```
- **Behavior:** Returns active repair issue categories for the device scanner.

### List Chipsets

- **Endpoint:** `GET /device/chipsets`
- **Method:** `GET`
- **Auth:** Not required
- **Response (200 OK):**
  ```json
  [
    { "key": "mediatek", "label": "MediaTek" },
    { "key": "snapdragon", "label": "Qualcomm Snapdragon" },
    { "key": "exynos", "label": "Samsung Exynos" },
    { "key": "tensor", "label": "Google Tensor" },
    { "key": "unisoc", "label": "Unisoc" },
    { "key": "apple", "label": "Apple" }
  ]
  ```
- **Behavior:** Returns supported chipsets used for device identification and tool matching.

### List Brands

- **Endpoint:** `GET /device/brands`
- **Method:** `GET`
- **Auth:** Not required
- **Response (200 OK):**
  ```json
  [
    { "slug": "samsung", "name": "Samsung" },
    { "slug": "apple", "name": "Apple" },
    { "slug": "google", "name": "Google" },
    { "slug": "xiaomi", "name": "Xiaomi" },
    { "slug": "realme", "name": "Realme" },
    { "slug": "tecno", "name": "Tecno" },
    { "slug": "generic", "name": "Generic / Other" }
  ]
  ```
- **Behavior:** Returns active device brands.

### Scan Device

- **Endpoint:** `POST /device/scan`
- **Method:** `POST`
- **Auth:** Not required
- **Request Body:**
  ```json
  {
    "model_number": "string (optional)",
    "brand": "string (optional)",
    "chipset": "string (optional)",
    "firmware": "string (optional)",
    "imei": "string (optional)"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "detected_brand": "samsung",
    "detected_model": "SM-A546B",
    "detected_chipset": "exynos",
    "firmware": "Android 14",
    "issues": [
      { "slug": "frp", "label": "FRP Lock" },
      { "slug": "network_lock", "label": "Network Lock" },
      { "slug": "mdm", "label": "MDM Lock" },
      { "slug": "icloud", "label": "iCloud Lock" },
      { "slug": "password", "label": "Password / Pattern Lock" },
      { "slug": "corrupt_os", "label": "Corrupt OS" }
    ]
  }
  ```
- **Behavior:** Accepts device info read from the browser via Web Serial API or manual entry. Infers brand and chipset from the model number when not supplied. Always returns the list of supported issues; frontend does not infer issue from device alone.

### Recommend Tools

- **Endpoint:** `POST /device/recommend`
- **Method:** `POST`
- **Auth:** Not required
- **Request Body:**
  ```json
  {
    "issue_slug": "frp",
    "brand_slug": "samsung",
    "chipset_key": "exynos"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "issue": { "slug": "frp", "label": "FRP Lock" },
    "tools": [
      {
        "slug": "kg-killer",
        "name": "KG Killer",
        "description": "Specialized Samsung KG lock removal utility.",
        "website_url": "https://kgkiller.com",
        "reason": "Compatible with Samsung Exynos devices"
      }
    ]
  }
  ```
- **Behavior:** Matches tools that support the requested issue and are compatible with the given device brand/chipset. Compatibility is based on `ToolCapability` and `DeviceCompatibility` tables.

### List Tools

- **Endpoint:** `GET /tools`
- **Method:** `GET`
- **Auth:** Not required
- **Query Parameters:**
  - `issue` (string, optional) — filter by issue slug
  - `brand` (string, optional) — filter by device brand slug
  - `chipset` (string, optional) — filter by chipset key
- **Response (200 OK):**
  ```json
  [
    { "id": "uuid", "slug": "kg-killer", "name": "KG Killer", "website_url": "https://kgkiller.com" }
  ]
  ```
- **Behavior:** Returns tools that satisfy all supplied filters. This endpoint is useful for browsing or debugging matches without issue context.

---

## Global

### Health Check

- **Endpoint:** `GET /health`
- **Method:** `GET`
- **Auth:** Not required
- **Response (200 OK):**
  ```json
  { "status": "ok" }
  ```

### Media Files

- **Endpoint:** `GET /media/{path}`
- **Method:** `GET`
- **Auth:** Not required
- **Behavior:** Serves static files from the local media root. Returns thumbnail and full images referenced by `media_url` on items and banners.
