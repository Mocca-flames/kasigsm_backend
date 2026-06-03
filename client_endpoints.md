# Client Endpoints Documentation

All endpoints are prefixed with `/client` and require authentication via JWT Bearer token (CLIENT or ADMIN role).

---

## 1. Client Registration

- **Endpoint:** `POST /client/register`
- **Method:** `POST`
- **Authentication:** Not required
- **Request Body:**
```json
{
  "email": "string (required)",
  "password": "string (required)",
  "full_name": "string (optional)"
}
```
- **Response (201 Created):**
```json
{"id": "uuid", "email": "string", "role": "CLIENT"}
```

---

## 2. Client Login

- **Endpoint:** `POST /client/login`
- **Method:** `POST`
- **Authentication:** Not required
- **Request Body:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```
- **Response (200 OK):**
```json
{"access_token": "string", "token_type": "bearer"}
```

---

## 3. Get My Profile

- **Endpoint:** `GET /client/profile`
- **Method:** `GET`
- **Authentication:** Required (client JWT)
- **Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "string",
  "full_name": "string or null",
  "role": "CLIENT|ADMIN",
  "is_active": true
}
```

---

## 4. Update My Profile

- **Endpoint:** `PATCH /client/profile`
- **Method:** `PATCH`
- **Authentication:** Required (client JWT)
- **Request Body:**
```json
{
  "full_name": "string (optional)",
  "password": "string (optional)"
}
```
- **Response (200 OK):** Returns updated profile object

---

## 5. List Visible Items

- **Endpoint:** `GET /client/items`
- **Method:** `GET`
- **Authentication:** Not required
- **Query Parameters:**
  - `category` (string, optional) — Filter by category
  - `item_type` (string, optional) — Filter by SERVICE or PRODUCT
  - `search` (string, optional) — Search by title
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
    "price_final": "decimal",
    "currency": "string",
    "delivery_time": "string or null",
    "stock": "int or null",
    "is_visible": true,
    "low_stock": false
  }
]
```

---

## 6. Get Item Details

- **Endpoint:** `GET /client/items/{item_id}`
- **Method:** `GET`
- **Authentication:** Not required
- **Path Parameters:**
  - `item_id` (string, required) — Item UUID
- **Response (200 OK):** Returns ItemDetail object
- **Errors:** 404 if item not found or not visible

---

## 7. Create Order

- **Endpoint:** `POST /client/orders`
- **Method:** `POST`
- **Authentication:** Required (client JWT)
- **Request Body:**
```json
{
  "item_id": "uuid (required)",
  "quantity": "int (default: 1)"
}
```
- **Response (201 Created):**
```json
{
  "id": "uuid",
  "item_id": "uuid",
  "quantity": "int",
  "total_amount": "decimal",
  "status": "PENDING",
  "created_at": "datetime"
}
```
- **Errors:** 400 if item not visible or out of stock, 404 if item not found

---

## 8. List My Orders

- **Endpoint:** `GET /client/orders`
- **Method:** `GET`
- **Authentication:** Required (client JWT)
- **Query Parameters:**
  - `status` (string, optional) — Filter by status: PENDING, PAID, FULFILLED, CANCELLED, REFUNDED
- **Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "item_id": "uuid",
    "item_title": "string",
    "quantity": "int",
    "total_amount": "decimal",
    "status": "PENDING|PAID|FULFILLED|CANCELLED|REFUNDED",
    "created_at": "datetime"
  }
]
```

---

## 9. Get Order Details

- **Endpoint:** `GET /client/orders/{order_id}`
- **Method:** `GET`
- **Authentication:** Required (client JWT)
- **Path Parameters:**
  - `order_id` (string, required) — Order UUID
- **Response (200 OK):** Returns order details with item info
- **Errors:** 404 if order not found or not owned by client

---

## 10. Cancel Order

- **Endpoint:** `PATCH /client/orders/{order_id}/cancel`
- **Method:** `PATCH`
- **Authentication:** Required (client JWT)
- **Path Parameters:**
  - `order_id` (string, required) — Order UUID
- **Response (200 OK):** Returns updated order with status CANCELLED
- **Errors:** 404 if order not found, 400 if cannot be cancelled

---

## 11. Get Credential (for Service Orders)

- **Endpoint:** `GET /client/credentials/{order_id}`
- **Method:** `GET`
- **Authentication:** Required (client JWT)
- **Path Parameters:**
  - `order_id` (string, required) — Order UUID
- **Response (200 OK):**
```json
{
  "credential": "string"
}
```
- **Errors:** 404 if order not found, 400 if order not fulfilled or item not SERVICE type

---

## 12. List Active Banners

- **Endpoint:** `GET /banners`
- **Method:** `GET`
- **Authentication:** Not required
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
    "is_dismissible": true
  }
]
```
- **Behavior:** Returns only banners where `is_active=true` and current time is within the `starts_at` and `ends_at` range (if set). Banners with past `ends_at` or future `starts_at` are excluded.