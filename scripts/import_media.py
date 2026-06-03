import argparse
import os
import re
import uuid
from urllib.parse import urlparse

import httpx
from sqlmodel import select
from app.config import settings
from app.database import get_session
from app.models.item import Item, Provider


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def build_local_media_path(filename: str) -> str:
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    target = os.path.abspath(os.path.join(media_root, filename))
    if not target.startswith(media_root):
        raise ValueError("Invalid target path")
    return target


def sanitize_filename(source_url: str) -> str:
    parsed = urlparse(source_url)
    original = os.path.basename(parsed.path)
    base, ext = os.path.splitext(original)
    ext = ext.lower().strip(".")
    if ext not in ALLOWED_EXTENSIONS:
        ext = "png"
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", base.lower()).strip("-")
    if not base:
        base = "image"
    name = f"{uuid.uuid4().hex}-{base}-{uuid.uuid4().hex[:4]}.{ext}"
    return name


def resolve_remote_url(raw: str, provider: Provider | None) -> str | None:
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if provider and provider.base_url:
        base = provider.base_url.rstrip("/")
        rel = raw.lstrip("/")
        return f"{base}/{rel}"
    return None


def _is_local(value: str | None) -> bool:
    if not value or not value.startswith(settings.MEDIA_PUBLIC_URL):
        return False
    rel = value[len(settings.MEDIA_PUBLIC_URL):]
    return os.path.exists(os.path.join(settings.MEDIA_ROOT, rel.lstrip("/")))


def import_media(provider_name: str | None = None) -> None:
    session = next(get_session())
    items = session.exec(select(Item)).all()
    clients = httpx.Client(follow_redirects=True, timeout=30)

    processed = 0
    skipped = 0
    failed = 0
    processed_urls: dict[str, str] = {}

    for item in items:
        thumb = item.thumbnail
        if not thumb:
            continue
        if _is_local(thumb):
            skipped += 1
            continue

        provider = item.provider_listings[0].provider if item.provider_listings else None
        if provider_name and (provider is None or provider.name != provider_name):
            continue

        target_url = resolve_remote_url(thumb, provider)
        if not target_url:
            skipped += 1
            continue

        if target_url in processed_urls:
            item.thumbnail = processed_urls[target_url]
            session.add(item)
            session.commit()
            skipped += 1
            continue

        try:
            response = clients.get(target_url)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")
            filename = sanitize_filename(target_url)
            local_path = build_local_media_path(filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as fp:
                fp.write(response.content)
            local_url = f"{settings.MEDIA_PUBLIC_URL}/{filename}"
            item.thumbnail = local_url
            session.add(item)
            session.commit()
            processed_urls[target_url] = local_url
            processed += 1
        except Exception as exc:
            print(f"[ERROR] item {item.id}: {exc}")
            failed += 1

    print(f"import_media completed: processed={processed} skipped={skipped} failed={failed}")

    providers = session.exec(select(Provider)).all()
    updated = 0
    for provider in providers:
        if provider.logo_url:
            continue
        if not provider.base_url or not provider.base_url.startswith("http"):
            continue
        try:
            response = clients.get(f"{provider.base_url.rstrip('/')}/favicon.ico")
            if response.status_code != 200:
                continue
            filename = sanitize_filename(provider.base_url)
            local_path = build_local_media_path(filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as fp:
                fp.write(response.content)
            provider.logo_url = f"{settings.MEDIA_PUBLIC_URL}/{filename}"
            session.add(provider)
            session.commit()
            updated += 1
        except Exception:
            pass

    print(f"provider logos updated={updated}")
    clients.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import supplier thumbnails into local media")
    parser.add_argument("--provider", help="Limit to specific provider name")
    args = parser.parse_args()
    import_media(provider_name=args.provider)
