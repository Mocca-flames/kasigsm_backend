import argparse
import json
import os
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse

import httpx
from sqlmodel import Session, select
from app.config import settings
from app.database import engine
from app.models.item import Item, Provider, ProviderListing, ItemType


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def get_media_root() -> str:
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    os.makedirs(media_root, exist_ok=True)
    return media_root


def build_local_media_path(filename: str) -> str:
    media_root = get_media_root()
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
    name = f"{uuid.uuid4().hex[:8]}-{base}.{ext}"
    return name


def generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:200]


def convert_usd_to_zar(usd_price: Decimal) -> Decimal:
    rate = Decimal(str(settings.USD_TO_ZAR_RATE))
    return (usd_price * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _is_local(value: str | None) -> bool:
    if not value or not value.startswith(settings.MEDIA_PUBLIC_URL):
        return False
    rel = value[len(settings.MEDIA_PUBLIC_URL):]
    full = os.path.join(get_media_root(), rel.lstrip("/"))
    return os.path.exists(full)


def resolve_remote_url(raw: str, supplier_url: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if supplier_url:
        base = supplier_url.rstrip("/")
        rel = raw.lstrip("/")
        return f"{base}/{rel}"
    return None


def download_image(client: httpx.Client, url: str) -> str | None:
    try:
        response = client.get(url)
        if response.status_code != 200:
            print(f"  [WARN] HTTP {response.status_code} for {url}")
            return None
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type and len(response.content) < 500:
            print(f"  [WARN] Got HTML instead of image for {url}")
            return None
        filename = sanitize_filename(url)
        local_path = build_local_media_path(filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as fp:
            fp.write(response.content)
        return f"{settings.MEDIA_PUBLIC_URL}/{filename}"
    except Exception as exc:
        print(f"  [ERROR] Download failed for {url}: {exc}")
        return None


def import_from_json(file_path: str) -> None:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    supplier_name = data.get("supplier", "Unknown Supplier")
    services_type = data.get("services_type", "General")
    supplier_url = data.get("supplier_url", "")
    services = data.get("services", [])

    print(f"Importing thumbnails from: {file_path}")
    print(f"Supplier: {supplier_name} | Category: {services_type} | Base URL: {supplier_url}")

    with Session(engine) as session:
        provider = session.exec(
            select(Provider).where(Provider.name == supplier_name)
        ).first()
        if not provider:
            provider = Provider(name=supplier_name, base_url=supplier_url)
            session.add(provider)
            session.commit()
            session.refresh(provider)
        elif not provider.base_url and supplier_url:
            provider.base_url = supplier_url
            session.add(provider)
            session.commit()

        client = httpx.Client(follow_redirects=True, timeout=30)
        downloaded = 0
        skipped = 0
        failed = 0
        url_cache: dict[str, str] = {}

        for svc in services:
            title = svc.get("title", "").strip()
            thumbnail = svc.get("thumbnail", "").strip()
            if not thumbnail:
                skipped += 1
                continue

            slug = generate_slug(title)
            item = session.exec(select(Item).where(Item.slug == slug)).first()
            if not item:
                skipped += 1
                continue

            if item.thumbnail and _is_local(item.thumbnail):
                skipped += 1
                continue

            full_url = resolve_remote_url(thumbnail, supplier_url)
            if not full_url:
                skipped += 1
                continue

            if full_url in url_cache:
                item.thumbnail = url_cache[full_url]
                session.add(item)
                session.commit()
                skipped += 1
                continue

            local_url = download_image(client, full_url)
            if local_url:
                item.thumbnail = local_url
                session.add(item)
                session.commit()
                url_cache[full_url] = local_url
                downloaded += 1
            else:
                failed += 1

        client.close()

    print(f"Done: downloaded={downloaded} skipped={skipped} failed={failed}")


def import_from_db(provider_name: str | None = None) -> None:
    with Session(engine) as session:
        items = session.exec(select(Item)).all()
        client = httpx.Client(follow_redirects=True, timeout=30)

        processed = 0
        skipped = 0
        failed = 0
        url_cache: dict[str, str] = {}

        for item in items:
            thumb = item.thumbnail
            if not thumb:
                continue
            if _is_local(thumb):
                skipped += 1
                continue

            listing = item.provider_listings[0] if item.provider_listings else None
            provider = listing.provider if listing else None
            if provider_name and (provider is None or provider.name != provider_name):
                continue

            supplier_url = ""
            if provider and provider.base_url:
                supplier_url = provider.base_url
            elif provider:
                supplier_url = "https://gsmcheap.com"

            target_url = resolve_remote_url(thumb, supplier_url)
            if not target_url:
                skipped += 1
                continue

            if target_url in url_cache:
                item.thumbnail = url_cache[target_url]
                session.add(item)
                session.commit()
                skipped += 1
                continue

            local_url = download_image(client, target_url)
            if local_url:
                item.thumbnail = local_url
                session.add(item)
                session.commit()
                url_cache[target_url] = local_url
                processed += 1
            else:
                failed += 1

        print(f"DB import: processed={processed} skipped={skipped} failed={failed}")

        updated = 0
        providers = session.exec(select(Provider)).all()
        for provider in providers:
            if provider.logo_url:
                continue
            if not provider.base_url or not provider.base_url.startswith("http"):
                continue
            logo_url = download_image(client, f"{provider.base_url.rstrip('/')}/favicon.ico")
            if logo_url:
                provider.logo_url = logo_url
                session.add(provider)
                session.commit()
                updated += 1

        print(f"Provider logos updated={updated}")
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import supplier thumbnails into local media")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Import directly from supplier JSON file")
    group.add_argument("--provider", help="Import from DB items for a specific provider")
    group.add_argument("--all", action="store_true", help="Import from all DB items")
    args = parser.parse_args()

    if args.file:
        import_from_json(args.file)
    elif args.provider:
        import_from_db(provider_name=args.provider)
    elif args.all:
        import_from_db()
