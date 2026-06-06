"""Remove all data for the GSM Tech Africa provider and keep only GSM Cheap."""

from sqlmodel import select
from app.database import get_session
from app.models.item import Item, ProviderListing, Provider


def purge_gsm_tech_africa():
    session = next(get_session())
    
    provider = session.exec(
        select(Provider).where(Provider.name == "GSM Tech Africa")
    ).first()
    
    if not provider:
        print("No GSM Tech Africa provider found.")
        return
    
    provider_id = provider.id
    
    listings = session.exec(
        select(ProviderListing).where(ProviderListing.provider_id == provider_id)
    ).all()
    
    print(f"Found {len(listings)} listings for GSM Tech Africa")
    
    removed_items = 0
    removed_listings = 0
    for listing in listings:
        item_id = listing.item_id
        other_listings = session.exec(
            select(ProviderListing).where(
                ProviderListing.item_id == item_id,
                ProviderListing.provider_id != provider_id
            )
        ).first()
        if not other_listings:
            session.delete(session.get(Item, item_id))
            removed_items += 1
        session.delete(listing)
        removed_listings += 1
    
    session.commit()
    session.delete(provider)
    session.commit()
    print(f"Purged GSM Tech Africa: {removed_listings} listings and {removed_items} items removed.")


if __name__ == "__main__":
    purge_gsm_tech_africa()
