from typing import Optional
from app.config import settings


def resolve_media_url(thumbnail: Optional[str]) -> Optional[str]:
    if not thumbnail:
        return None
    if thumbnail.startswith("http"):
        return thumbnail
    base = settings.MEDIA_BASE_URL.rstrip("/")
    return f"{base}/{thumbnail.lstrip('/')}"
