import argparse
import json
import re
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from app.database import engine
from app.models.item import Item, Provider, ProviderListing, ItemType
from app.config import settings


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


def seed_products(file_path: str) -> None:
    with Session(engine) as session:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        supplier_name = data.get("supplier", "Unknown Supplier")
        services_type = data.get("services_type", "General")
        services = data.get("services", [])

        provider = session.exec(
            select(Provider).where(Provider.name == supplier_name)
        ).first()
        if not provider:
            provider = Provider(name=supplier_name, base_url=data.get("supplier_url"))
            session.add(provider)
            session.commit()
            session.refresh(provider)

        created = 0
        skipped = 0

        for svc in services:
            title = svc.get("title", "").strip()
            if not title:
                skipped += 1
                continue

            slug = generate_slug(title)

            existing_item = session.exec(
                select(Item).where(Item.slug == slug)
            ).first()

            if existing_item:
                item = existing_item
            else:
                usd_price = Decimal(str(svc.get("price", 0)))
                zar_price = convert_usd_to_zar(usd_price)

                item = Item(
                    slug=slug,
                    uid=slug,
                    title=title,
                    description=svc.get("description"),
                    item_type=ItemType.SERVICE,
                    category=services_type,
                    thumbnail=svc.get("thumbnail"),
                    price_markup=zar_price,
                    currency="ZAR",
                    delivery_time=svc.get("delivery_time"),
                    stock=None,
                    is_visible=True,
                    is_archived=False,
                )
                session.add(item)
                session.commit()
                session.refresh(item)
                created += 1

            existing_listing = session.exec(
                select(ProviderListing).where(
                    ProviderListing.item_id == item.id,
                    ProviderListing.provider_id == provider.id,
                )
            ).first()

            if not existing_listing:
                usd_cost = Decimal(str(svc.get("price", 0)))
                zar_cost = convert_usd_to_zar(usd_cost)

                has_any_listing = session.exec(
                    select(ProviderListing).where(ProviderListing.item_id == item.id)
                ).first()

                listing = ProviderListing(
                    item_id=item.id,
                    provider_id=provider.id,
                    cost_price=zar_cost,
                    is_preferred=has_any_listing is None,
                    is_active=True,
                )
                session.add(listing)

        session.commit()
        print(f"Seeded provider '{supplier_name}' | category '{services_type}'")
        print(f"Created: {created} items | Skipped: {skipped} | Total services: {len(services)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed products from supplier JSON")
    parser.add_argument("--file", required=True, help="Path to supplier JSON file")
    args = parser.parse_args()
    seed_products(args.file)
