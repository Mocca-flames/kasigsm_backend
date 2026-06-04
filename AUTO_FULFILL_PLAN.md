# Auto-Fulfill Plan

## Goal
Automate purchase of SERVICE items (tool rentals) from GSM Cheap via Python worker, then fulfill backend orders by placing credentials.

## Architecture

### 1. Worker Modules
- `fetch_gsmcheap_v1.py` — scrapes/fetches available services from GSM Cheap and saves to `data/gsm_cheap.json`.
- `workers/gsmcheap_worker.py` — main automation loop (to be implemented).

### 2. GSM Cheap Service Mapping
- Source: `fetch_gsmcheap_v1.py` → `data/gsm_cheap.json`
- Target: backend `Item` records with `ItemType.SERVICE`
- Normalization: match by title after cleaning/prefix stripping.

### 3. Purchase Flow (pending user-provided GSM Cheap auth/login requests)
1. Worker reads pending PAID orders from backend API.
2. For each unfulfilled SERVICE order item:
   - Lookup matching GSM Cheap service in `data/gsm_cheap.json`.
   - Submit purchase to GSM Cheap using provided login/session handling.
   - Capture credential payload returned by GSM Cheap (username/password, license, or account login details).
3. Call backend `POST /admin/orders/{order_id}/fulfill` with credentials.

### 4. Configuration / Secrets
- GSM Cheap credentials: to be provided by user; do NOT hardcode.
- Keep secrets in environment variables or a separate local-only file (gitignored).

### 5. Data Files
- `data/gsm_cheap.json` — latest service catalog from GSM Cheap.
- `data/gsm_cheap_rental.json` — rental service catalog.
- `data/gsm_cheap_remote.json` — remote service catalog.

### 6. Future Endpoints (if needed)
- Optional internal API to expose fulfillment status to worker.

### 7. TODOs for Future Implementation
- [ ] Provide GSM Cheap login flow (form, API, headers, cookies).
- [ ] Provide exact purchase request format (service ID, parameters, callbacks).
- [ ] Implement GSM Cheap session management in worker.
- [ ] Implement credential capture and parsing from purchase response.
- [ ] Implement mapping between backend service titles and GSM Cheap service titles.
- [ ] Handle rate limits and retries.
- [ ] Handle credential expiry or service rejection.
