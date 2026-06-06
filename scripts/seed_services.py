import argparse
import json
import re
from decimal import Decimal
from sqlmodel import select, func
from app.database import get_session
from app.models.item import Item, Provider, ProviderListing, ItemType
from app.models.category import Category
from app.config import settings

DEFAULT_CURRENCY = "ZAR"
DEFAULT_PRICE_FALLBACK = Decimal("0")
DEFAULT_SUPPLIER_URL = "https://gsmcheap.com"

NORMALIZERS = {
    "GSM Tech Africa": {
        "currency": "ZAR",
        "url_trusted": {"https://gsmtechafrica.com"},
    }
}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    return text.strip("-")


EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)
SYMBOL_RE = re.compile(r"[\u26a0-\u26ff\ufe0f]+")


def extract_service_meta(title: str):
    clean = title
    duration = None
    notes = []

    dur_match = re.search(r"[\[\({]?\s*(\d+)\s*(Hours?|Miniutes|Minutes?|Days?)\s*[\]\)}]?", clean, re.IGNORECASE)
    if dur_match:
        duration = f"{dur_match.group(1)} {dur_match.group(2).lower()}"
        clean = clean[: dur_match.start()] + clean[dur_match.end():]
    else:
        for token in ("instant",):
            if re.search(rf"\b{re.escape(token)}\b", clean, re.IGNORECASE):
                duration = token.title()
                clean = re.sub(rf"\b{re.escape(token)}\b", "", clean, flags=re.IGNORECASE)
                break

    clean = re.sub(r"\{?\s*Time:\s*\}?\s*", "", clean, flags=re.IGNORECASE)
    parens = re.findall(r"\(([^)]+)\)", clean)
    for p in parens:
        text = EMOJI_RE.sub("", p)
        text = SYMBOL_RE.sub("", text)
        text = re.sub(r"\{?\s*Time:\s*\}?\s*", "", text, flags=re.IGNORECASE).strip()
        if text:
            notes.append(text)
        clean = clean.replace(f"({p})", "", 1)

    clean = EMOJI_RE.sub("", clean)
    clean = SYMBOL_RE.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" -:[]{}")
    if not clean:
        clean = title.strip()

    display_title = clean
    notes = notes or []

    return display_title, duration, notes


def make_uid(session, supplier_name: str, service_type: str) -> str:
    prefix = f"{supplier_name[:3].upper()}-{service_type[:3].upper()}"
    existing = session.exec(
        select(func.max(Item.uid)).where(Item.uid.like(f"{prefix}-%"))
    ).first()
    num = 1
    if existing:
        try:
            num = int(existing.split("-")[-1]) + 1
        except (ValueError, IndexError):
            pass
    return f"{prefix}-{num:03d}"


def normalize_title(title: str) -> str:
    if not title:
        return ""
    title = title.strip()
    title = re.sub(r" {2,}", " ", title)
    return title


def normalize_price(raw_price) -> Decimal:
    if raw_price is None or raw_price == "":
        return DEFAULT_PRICE_FALLBACK
    if isinstance(raw_price, (int, float)):
        try:
            return Decimal(str(raw_price))
        except Exception:
            return DEFAULT_PRICE_FALLBACK
    text = str(raw_price)
    text = re.sub(r"[^0-9.]", "", text)
    if "." in text:
        parts = text.split(".")
        text = parts[0] + "." + (parts[1] if len(parts) > 1 else "")
    try:
        return Decimal(text) if text else DEFAULT_PRICE_FALLBACK
    except Exception:
        return DEFAULT_PRICE_FALLBACK


def guess_currency(supplier_name: str) -> str:
    n = NORMALIZERS.get(supplier_name, {})
    return n.get("currency", DEFAULT_CURRENCY)


def seed_services(file_path: str, provider_name: str = None) -> None:
    session = next(get_session())

    with open(file_path) as f:
        data = json.load(f)

    services = data.get("services", [])
    default_supplier = data.get("supplier", provider_name or "Unknown")
    default_service_type = data.get("services_type", "Tool Rental")
    supplier_url = data.get("supplier_url") or DEFAULT_SUPPLIER_URL

    trusted_urls = NORMALIZERS.get(default_supplier, {}).get("url_trusted", set())

    provider = session.exec(select(Provider).where(Provider.name == default_supplier)).first()
    if not provider:
        provider = Provider(name=default_supplier, base_url=supplier_url)
        session.add(provider)
        session.commit()
    else:
        if not provider.base_url or supplier_url in trusted_urls:
            provider.base_url = supplier_url
            session.add(provider)
            session.commit()

    category = session.exec(select(Category).where(Category.name == default_service_type)).first()
    if not category:
        slug = slugify(default_service_type)
        category = Category(name=default_service_type, slug=slug)
        session.add(category)
        session.commit()

    rate = Decimal(str(settings.USD_TO_ZAR_RATE))

    for svc in services:
        title = normalize_title(svc.get("title", ""))
        raw_price = svc.get("price")
        currency = svc.get("currency") or guess_currency(default_supplier)
        normalized_price = normalize_price(raw_price)
        delivery_time = svc.get("delivery_time")
        if isinstance(delivery_time, str):
            delivery_time = delivery_time.replace("Miniutes", "Minutes")
        thumbnail = svc.get("thumbnail")

        display_title, rent_duration, rent_notes = extract_service_meta(title)

        cost_price_zar = normalized_price * rate if currency == "USD" else normalized_price

        slug = slugify(title)

        item = session.exec(select(Item).where(Item.slug == slug)).first()
        if item:
            item.title = title
            if delivery_time is not None:
                item.delivery_time = delivery_time
            if thumbnail:
                existing_is_local = (
                    item.thumbnail
                    and item.thumbnail.startswith(settings.MEDIA_PUBLIC_URL)
                )
                if not existing_is_local:
                    item.thumbnail = thumbnail
            item.currency = currency
            if default_service_type == "Tool Rental":
                meta = dict(item.meta or {})
                if display_title and display_title != title:
                    meta["display_title"] = display_title
                else:
                    meta.pop("display_title", None)
                if rent_duration:
                    meta["rent_duration"] = rent_duration
                else:
                    meta.pop("rent_duration", None)
                if rent_notes:
                    meta["rent_notes"] = rent_notes
                else:
                    meta.pop("rent_notes", None)
                item.meta = meta or None
            session.add(item)
            session.commit()
            session.refresh(item)
        else:
            uid = make_uid(session, default_supplier, default_service_type)
            meta = {}
            if default_service_type == "Tool Rental":
                if display_title:
                    meta["display_title"] = display_title
                if rent_duration:
                    meta["rent_duration"] = rent_duration
                if rent_notes:
                    meta["rent_notes"] = rent_notes
            item = Item(
                uid=uid,
                slug=slug,
                title=title,
                item_type=ItemType.SERVICE,
                category=default_service_type,
                is_visible=True,
                currency=currency,
                price=normalized_price,
                delivery_time=delivery_time,
                thumbnail=thumbnail,
                meta=meta or None,
            )
            session.add(item)
            session.commit()
            session.refresh(item)

        listing = session.exec(
            select(ProviderListing).where(
                ProviderListing.item_id == item.id,
                ProviderListing.provider_id == provider.id,
            )
        ).first()
        if listing:
            listing.cost_price = cost_price_zar
            listing.external_id = svc.get("external_id")
        else:
            existing_preferred = session.exec(
                select(ProviderListing).where(
                    ProviderListing.item_id == item.id,
                    ProviderListing.is_preferred == True,
                )
            ).first()
            listing = ProviderListing(
                item_id=item.id,
                provider_id=provider.id,
                external_id=svc.get("external_id"),
                cost_price=cost_price_zar,
                is_preferred=existing_preferred is None,
            )
            session.add(listing)
        session.commit()

    print(f"Seeded {len(services)} services for provider '{default_supplier}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed services from JSON")
    parser.add_argument("--file", required=True, help="Path to services JSON file")
    parser.add_argument("--provider", help="Provider name (optional, uses supplier from JSON)")
    args = parser.parse_args()
    seed_services(args.file, args.provider)
