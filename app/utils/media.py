from typing import Optional
from app.config import settings


def resolve_media_url(thumbnail: Optional[str]) -> Optional[str]:
    if not thumbnail:
        return None
    if thumbnail.startswith("http"):
        return thumbnail
    if thumbnail.startswith("/"):
        return thumbnail
    return f"{settings.MEDIA_PUBLIC_URL}/{thumbnail.lstrip('/')}"
