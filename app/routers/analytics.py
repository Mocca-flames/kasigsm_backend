from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import httpx

from app.utils.security import require_admin
from app.config import settings

router = APIRouter()


@router.get("/visitors")
async def get_visitor_summary(_admin=Depends(require_admin)):
    if not settings.CLOUDFLARE_API_TOKEN:
        raise HTTPException(status_code=400, detail="Cloudflare API token not configured")

    end = datetime.utcnow()
    start = end - timedelta(hours=24)

    # Use Cloudflare's REST-style analytics endpoint for Netlify-like site analytics
    # This works for Cloudflare Web Analytics without GraphQL.
    # Docs reference: https://developers.cloudflare.com/analytics/
    url = "https://api.cloudflare.com/client/v4/accounts/web_analytics/summary"

    headers = {
        "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    params = {
        "since": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "until": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain": getattr(settings, "CLOUDFLARE_ANALYTICS_DOMAIN", ""),
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code == 404:
        # Endpoint not enabled/available for this token; return empty stats
        return {
            "period_start": start.isoformat() + "Z",
            "period_end": end.isoformat() + "Z",
            "total_requests": 0,
            "bandwidth_bytes": 0,
            "unique_visitors": 0,
            "status": "unavailable",
        }

    try:
        data = response.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Invalid response from Cloudflare")

    if response.status_code != 200 or not data.get("success", False):
        # Surface the Cloudflare error message without crashing
        msg = data.get("errors", [{}])[0].get("message", "Cloudflare API error")
        return {
            "period_start": start.isoformat() + "Z",
            "period_end": end.isoformat() + "Z",
            "total_requests": 0,
            "bandwidth_bytes": 0,
            "unique_visitors": 0,
            "status": "error",
            "error": msg,
        }

    try:
        rows = data.get("data", [])
        total_requests = sum(r.get("visits", 0) or r.get("requests", 0) or 0 for r in rows)
        unique_visitors = sum(r.get("uniques", 0) or r.get("unique_visitors", 0) or 0 for r in rows)
        bandwidth_bytes = sum(r.get("bytes", 0) or r.get("bandwidth", 0) or 0 for r in rows)
    except Exception:
        total_requests = 0
        unique_visitors = 0
        bandwidth_bytes = 0

    return {
        "period_start": start.isoformat() + "Z",
        "period_end": end.isoformat() + "Z",
        "total_requests": total_requests,
        "bandwidth_bytes": bandwidth_bytes,
        "unique_visitors": unique_visitors,
        "status": "ok",
    }
