# Manual Fulfillment Plan

## Goal
Replace auto-fulfillment with admin-driven manual credential entry for SERVICE items, especially TOOL RENTAL.

## Changes

### 1. payments.py — Stop auto-fulfillment
- Remove `fulfill_order()` call from both `/verify` and `/verify/{reference}`
- Keep sending `send_order_paid_email` only

### 2. admin.py — New fulfillment endpoints
- `GET /admin/orders/fulfillment-queue` — list PAID orders with no credentials assigned yet
- `GET /admin/orders/{id}/ready` — show order detail for fulfillment
- `POST /admin/orders/{id}/fulfill` — body: `{ credentials: [{order_item_id, payload}] }`
  - Validates each `order_item_id` belongs to the order
  - Encrypts each payload, stores in Credential, links to `order_item_id`
  - Commit all in one session
- `POST /admin/orders/{id}/reject` — marks order CANCELLED, refunds to wallet if applicable

### 3. Verify client-facing flow
- PAID orders appear in client history (no credentials yet)
- After admin fulfills, credentials appear on next fetch

## Test Script Plan
1. Register + login as client → get token
2. Create order for a SERVICE item
3. Initiate + verify payment via Paystack (or mock)
4. Confirm order is PAID with empty credentials
5. Login as admin → list fulfillment queue
6. Admin fulfills order with test credentials
7. Client fetches order → sees decrypted credentials
8. Verify Brevo emails sent correctly
