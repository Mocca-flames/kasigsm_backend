import argparse
import json
import re
from decimal import Decimal
from sqlmodel import select, func
from app.database import get_session
from app.models.item import Item, Provider, ProviderListing, ItemType
from app.models.category import Category
from app.config import settings


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9-]+', '-', text)
    return text.strip('-')


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


def seed_services(file_path: str, provider_name: str = None) -> None:
    session = next(get_session())

    with open(file_path) as f:
        data = json.load(f)

    services = data.get("services", [])
    default_supplier = data.get("supplier", provider_name or "Unknown")
    default_service_type = data.get("services_type", "Tool Rental")

    provider = session.exec(select(Provider).where(Provider.name == default_supplier)).first()
    if not provider:
        provider = Provider(name=default_supplier)
        session.add(provider)
        session.commit()

    category = session.exec(select(Category).where(Category.name == default_service_type)).first()
    if not category:
        slug = re.sub(r'[^a-z0-9-]+', '-', default_service_type.lower()).strip('-')
        category = Category(name=default_service_type, slug=slug)
        session.add(category)
        session.commit()

    rate = Decimal(str(settings.USD_TO_ZAR_RATE))

    for svc in services:
        title = svc.get("title")
        raw_price = Decimal(str(svc.get("price", 0)))
        currency = svc.get("currency", "USD")
        delivery_time = svc.get("delivery_time")

        cost_price_zar = raw_price * rate if currency == "USD" else raw_price

        slug = slugify(title)

        item = session.exec(select(Item).where(Item.slug == slug)).first()
        if item:
            item.title = title
            if delivery_time is not None:
                item.delivery_time = delivery_time
        else:
            uid = make_uid(session, default_supplier, default_service_type)
            item = Item(
                uid=uid,
                slug=slug,
                title=title,
                item_type=ItemType.SERVICE,
                category=default_service_type,
                is_visible=True,
                currency="ZAR",
                delivery_time=delivery_time,
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
