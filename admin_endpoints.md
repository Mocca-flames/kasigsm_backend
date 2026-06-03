# Admin Endpoints Documentation

## Admin Login

- **Endpoint:** `POST /auth/login`
- **Method:** `POST`
- **Description:** Authenticate admin user and receive JWT token
- **Request Body (form-data):**
  - `username`: `juniorflamebet@gmail.com`
  - `password`: `Maurice@12!`
- **Response (200 OK):**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

All other admin endpoints are prefixed with `/admin` and require admin authentication via JWT Bearer token.

---

## 1. List All Items

- **Endpoint:** `GET /admin/items`
- **Method:** `GET`
- **Authentication:** Required (admin JWT)
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

## 2. Create Item

- **Endpoint:** `POST /admin/items`
- **Method:** `POST`
- **Authentication:** Required (admin JWT)
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
- **Response (200 OK):** Returns `ItemDetail` object

---

## 3. Edit Item

- **Endpoint:** `PATCH /admin/items/{item_id}`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Item UUID
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
- **Response (200 OK):** Returns `ItemDetail` object
- **Errors:** 404 if item not found

---

## 4. Set Item Markup

- **Endpoint:** `PATCH /admin/items/{item_id}/markup`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Item UUID
- **Query Parameters:**
  - `markup` (decimal, required) — New markup price
- **Response (200 OK):** Returns `ItemDetail` object
- **Errors:** 404 if item not found

---

## 5. Toggle Item Visibility

- **Endpoint:** `PATCH /admin/items/{item_id}/visibility`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Item UUID
- **Query Parameters:**
  - `is_visible` (bool, required) — Visibility state
- **Response (200 OK):** Returns `ItemDetail` object
- **Errors:** 404 if item not found

---

## 6. Archive Item (Soft Delete)

- **Endpoint:** `DELETE /admin/items/{item_id}`
- **Method:** `DELETE`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Item UUID
- **Response (200 OK):**
```json
{"message": "Item archived"}
```
- **Errors:** 404 if item not found

---

## 7. List Users

- **Endpoint:** `GET /admin/users`
- **Method:** `GET`
- **Authentication:** Required (admin JWT)
- **Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "email": "string",
    "role": "CLIENT|ADMIN",
    "is_active": true
  }
]
```

---

## 8. Update User Status

- **Endpoint:** `PATCH /admin/users/{user_id}`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `user_id` (string, required) — User UUID
- **Query Parameters:**
  - `is_active` (bool, required) — User active status
- **Response (200 OK):**
```json
{"id": "uuid", "email": "string", "is_active": true}
```
- **Errors:** 404 if user not found

---

## 9. List Orders

- **Endpoint:** `GET /admin/orders`
- **Method:** `GET`
- **Authentication:** Required (admin JWT)
- **Query Parameters:**
  - `status` (string, optional) — Filter by status: PENDING, PAID, FULFILLED, CANCELLED, REFUNDED
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

---

## 10. Update Order Status

- **Endpoint:** `PATCH /admin/orders/{order_id}/status`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `order_id` (string, required) — Order UUID
- **Query Parameters:**
  - `status` (string, required) — New status: PENDING, PAID, FULFILLED, CANCELLED, REFUNDED
- **Response (200 OK):**
```json
{"id": "uuid", "status": "PENDING|PAID|FULFILLED|CANCELLED|REFUNDED"}
```
- **Errors:** 404 if order not found

---

## 11. Bulk Upload Credentials

- **Endpoint:** `POST /admin/credentials/bulk`
- **Method:** `POST`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Service item UUID
- **Request:** `multipart/form-data` with `credentials_file` (JSON or CSV)
- **File Format:**
  - JSON: Array of objects or single object
  - CSV: Key-value pairs as columns
- **Response (200 OK):**
```json
{"item_id": "uuid", "credentials_added": 0}
```
- **Errors:** 404 item not found, 400 if not SERVICE type or invalid file format

---

## 12. Get Credential Pool

- **Endpoint:** `GET /admin/credentials/{item_id}`
- **Method:** `GET`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `item_id` (string, required) — Service item UUID
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
- **Errors:** 404 if item not found

---

## 13. List Banners

- **Endpoint:** `GET /admin/banners`
- **Method:** `GET`
- **Authentication:** Required (admin JWT)
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
    "is_active": true,
    "is_dismissible": true,
    "starts_at": "datetime or null",
    "ends_at": "datetime or null",
    "created_at": "datetime"
  }
]
```

---

## 14. Create Banner

- **Endpoint:** `POST /admin/banners`
- **Method:** `POST`
- **Authentication:** Required (admin JWT)
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
- **Response (200 OK):** Returns banner object

---

## 15. Edit Banner

- **Endpoint:** `PATCH /admin/banners/{banner_id}`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `banner_id` (string, required) — Banner UUID
- **Request Body:**
```json
{
  "slug": "string (optional)",
  "title": "string (optional)",
  "content": "string (optional)",
  "image_url": "string (optional)",
  "link_url": "string (optional)",
  "is_active": "bool (optional)",
  "is_dismissible": "bool (optional)",
  "starts_at": "datetime (optional)",
  "ends_at": "datetime (optional)"
}
```
- **Response (200 OK):** Returns updated banner object
- **Errors:** 404 if banner not found

---

## 16. Delete Banner

- **Endpoint:** `DELETE /admin/banners/{banner_id}`
- **Method:** `DELETE`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `banner_id` (string, required) — Banner UUID
- **Response (200 OK):**
```json
{"message": "Banner deleted"}
```
- **Errors:** 404 if banner not found

---

## 17. Toggle Banner Active Status

- **Endpoint:** `PATCH /admin/banners/{banner_id}/toggle`
- **Method:** `PATCH`
- **Authentication:** Required (admin JWT)
- **Path Parameters:**
  - `banner_id` (string, required) — Banner UUID
- **Query Parameters:**
  - `is_active` (bool, required) — Active state
- **Response (200 OK):**
```json
{"id": "uuid", "is_active": true}
```
- **Errors:** 404 if banner not found