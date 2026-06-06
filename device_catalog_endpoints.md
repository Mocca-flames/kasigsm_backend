# Device Catalog Endpoints

## POST /device/recommend/services

Recommends on-site services/tools for a list of detected device issues. Uses seed scan data + item pricing to build frontend-ready deep links.

### Request Body

```json
{
  "issues": ["frp"],
  "brand_slug": "Samsung",
  "chipset_key": "—",
  "top": 3
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `issues` | `string[]` | Yes | Lower-cased issue slugs from `/device/scan` response |
| `brand_slug` | `string \| null` | No | Brand slug; case-insensitive |
| `chipset_key` | `string \| null` | No | Chipsets like `exynos`, `snapdragon`; placeholders/non-alphanumeric are ignored |
| `top` | `integer` | No | Max services to return (default `3`) |

### Response Body

```json
{
  "services": [
    {
      "slug": "samfirm",
      "name": "SamFirm / FRP Tool",
      "description": "Samsung firmware and FRP removal helper.",
      "website_url": null,
      "reason": "Bypass: Frp",
      "rent_slug": "samfirm",
      "rent_price_final": 7.92,
      "rent_currency": "ZAR",
      "full_slug": "samfirm",
      "full_price_final": 47.52,
      "full_currency": "ZAR"
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `slug` | `string` | Canonical tool slug (deep-linkable within the app) |
| `name` | `string` | Tool display name |
| `description` | `string \| null` | Tool description |
| `website_url` | `string \| null` | Always `null` for keep-in-app UX |
| `reason` | `string \| null` | Why this tool matched (e.g. `Bypass: Frp`) |
| `rent_slug` | `string \| null` | Slug for on-site rental item |
| `rent_price_final` | `number \| null` | Calculated rent price in `ZAR` |
| `rent_currency` | `string` | Currency (`ZAR`) |
| `full_slug` | `string \| null` | Slug for a future full-tool purchase item |
| `full_price_final` | `number \| null` | Estimated full-tool price in `ZAR` (fabricated multiplier for now) |
| `full_currency` | `string` | Currency (`ZAR`) |

### Notes

- All prices are already converted to `ZAR` (aligned with `seed_products` currency so frontend does not need extra conversion logic).
- `website_url` is stripped so users stay inside the app.
- `top` is capped internally (max `20`) to protect performance.
- Same slug is reused for rent vs full so frontend only needs one item lookup.
