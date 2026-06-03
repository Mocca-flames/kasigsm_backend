import argparse
import json
from decimal import Decimal

from sqlmodel import select

from app.database import get_session
from app.models.item import Item, Provider, ProviderListing, ItemType


def seed_products(file_path: str, provider_name: str) -> None:
    session = next(get_session())
    
    with open(file_path) as f:
        products = json.load(f)
    
    provider = session.exec(select(Provider).where(Provider.name == provider_name)).first()
    if not provider:
        provider = Provider(name=provider_name)
        session.add(provider)
        session.commit()
    
    for prod in products:
        item = session.exec(
            select(Item).where(Item.slug == prod["slug"])
        ).first()
        
        if not item:
            item = Item(
                slug=prod["slug"],
                title=prod["title"],
                description=prod.get("description"),
                item_type=ItemType.PRODUCT,
                category=prod["category"],
                stock=prod.get("stock", 0),
                is_visible=True,
            )
            session.add(item)
            session.commit()
        
        listing = session.exec(
            select(ProviderListing).where(
                ProviderListing.item_id == item.id,
                ProviderListing.provider_id == provider.id
            )
        ).first()
        
        if not listing:
            cost_price = Decimal(prod.get("price", "0"))
            existing = session.exec(
                select(ProviderListing).where(ProviderListing.item_id == item.id)
            ).first()
            is_preferred = existing is None
            
            listing = ProviderListing(
                item_id=item.id,
                provider_id=provider.id,
                cost_price=cost_price,
                is_preferred=is_preferred,
                external_id=prod.get("external_id"),
            )
            session.add(listing)
    
    session.commit()
    print(f"Seeded {len(products)} products for provider '{provider_name}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed products from JSON")
    parser.add_argument("--file", required=True, help="Path to products JSON file")
    parser.add_argument("--provider", required=True, help="Provider name")
    args = parser.parse_args()
    seed_products(args.file, args.provider)