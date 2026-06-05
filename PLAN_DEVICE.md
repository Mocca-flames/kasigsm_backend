# PLAN.md — KasIGSM Device Intelligence Tool

> **Project name:** KasIGSM Device Scanner  
> **Goal:** Free, browser-based tool that detects a technician's plugged-in phone, diagnoses the issue, and funnels them to rent the right tool on gsmcheap.com — at a fraction of the cost of buying it.  
> **Lives on:** Main page of gsmcheap.com (embedded section, replaces or sits above current hero slider)  
> **Revenue model:** Free tool → account registration → tool rental conversion

---

## The Core Problem We Are Solving

Technicians visiting KasIGSM already know what tools exist. They leave without purchasing because:
1. They don't know which tool fits their exact phone + issue combination
2. Full tool activations are expensive — they hesitate
3. They don't see immediate value before committing

**This scanner solves all three in under 60 seconds.**

---

## What the Tool Does (User Perspective)

```
Technician plugs phone into PC via USB
          ↓
Visits gsmcheap.com — no app, no install, no admin rights
          ↓
Clicks "Scan My Device" → browser permission dialog appears
          ↓
Web Serial API reads COM port → AT commands extract:
  · Brand (Samsung / Apple / Xiaomi / Realme / Tecno / etc.)
  · Model number (e.g. SM-A546B, iPhone 14, Redmi Note 12)
  · Firmware / Android version
  · IMEI (optional, if AT+CGSN responds)
          ↓
Backend matches device to compatible tools in KasIGSM catalogue
          ↓
Technician selects their issue (FRP, Network Lock, MDM, iCloud, etc.)
          ↓
Tool recommendations shown with:
  · Tool name (Unlock Tool, DFT Pro, Octoplus, etc.)
  · Rent price vs buy price (value anchor)
  · Compatibility badge: "Works with your device ✓"
          ↓
If not registered → Registration gate (soft: "Save your results + get notified")
If registered     → Direct "Rent Now" CTA linking to existing service page
```

---

## Business Logic

### Why free?

- Zero-friction entry: technicians don't pay, don't install, don't commit
- Trust builder: we correctly identify their device = we know our stuff
- Data asset: every scan = device brand/model data + issue category = better inventory decisions
- SEO: "free phone diagnostic tool" + "what tool for [device model]" searches drive organic traffic
- Conversion: technician who gets accurate recommendation is 5× more likely to rent

### Revenue funnel

```
Scan (free, anonymous)
  → Soft registration prompt ("Save device history")
    → Registered user sees personalised dashboard
      → Rental recommendation with urgency ("Tool available now")
        → Rental purchase on existing KasIGSM checkout
```

### What stays on KasIGSM.com (no change needed)

- All existing service pages (`/imei/service`, `/remote/service`, etc.)
- Existing checkout and payment system
- Existing tool catalogue and pricing

### What gets added to KasIGSM.com

- The Device Scanner section on the homepage (Vite React embedded widget or standalone `/scan` route)
- A FastAPI microservice (your ngrok in dev, VPS subdomain in prod: `api.gsmcheap.com`)
- A `device_tools_map.json` — mapping device models/brands to tool recommendations

---

## Scope Boundaries

### IN scope
- Web Serial device detection (Samsung, Android, iPhone via iTunes COM driver)
- Manual fallback (user types model if serial fails)
- Issue category selector (FRP / Network / MDM / iCloud / Password / Corrupt OS)
- Tool recommendation engine (backend lookup, not AI)
- Soft registration prompt after results
- Link-out to existing KasIGSM service pages for rental
- Mobile-safe layout (technician may scan from desktop, browse from phone)

### OUT of scope (future phases)
- Actually running repair tools in the browser
- Payment processing inside the scanner (use existing KasIGSM checkout)
- Firmware flashing
- Full user account dashboard (Phase 3)

---

## Success Metrics

| Metric | Target (Month 1) |
|---|---|
| Scans per day | 50+ |
| Scan → registration conversion | 15% |
| Registered → rental within 7 days | 25% |
| Organic search impressions (device + tool queries) | +30% |

---

## Dependencies

| Dependency | Owner | Notes |
|---|---|---|
| FastAPI server deployment | You | ngrok for dev, VPS for prod |
| `device_tools_map.json` | You + Claude | Maps brands/models to KasIGSM service URLs |
| Web Serial API | Browser | Chrome / Edge only — show warning for Firefox/Safari |
| Samsung USB driver | Technician's PC | Already installed on 95% of workshop PCs |
| Apple Mobile Device USB driver | Technician's PC | Installed with iTunes — common in workshops |
| KasIGSM homepage embed | You | Add `<div id="gsmcheap-scanner">` + script tag |