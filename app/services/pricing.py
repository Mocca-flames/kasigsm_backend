from decimal import Decimal
from sqlmodel import select
from app.models.item import Item, ProviderListing
from app.models.category import ProviderCategoryMarkup


def _find_active_preferred(item: Item) -> ProviderListing | None:
    active_listings = [
        pl for pl in item.provider_listings
        if pl.is_active and pl.provider and pl.provider.is_active
    ]
    return active_listings[0] if active_listings else None


def resolve_markup(item: Item, preferred_listing: ProviderListing, session) -> Decimal:
    if preferred_listing and preferred_listing.provider_id and preferred_listing.is_active:
        override = session.exec(
            select(ProviderCategoryMarkup).where(
                ProviderCategoryMarkup.provider_id == preferred_listing.provider_id,
                ProviderCategoryMarkup.category == item.category,
            )
        ).first()
        if override:
            return override.price_markup
    return item.price_markup


def get_markup_source(item: Item, preferred_listing: ProviderListing, session) -> str:
    if preferred_listing and preferred_listing.provider_id and preferred_listing.is_active:
        override = session.exec(
            select(ProviderCategoryMarkup).where(
                ProviderCategoryMarkup.provider_id == preferred_listing.provider_id,
                ProviderCategoryMarkup.category == item.category,
            )
        ).first()
        if override:
            return "provider_category"
    return "item"


def get_price_final(item: Item, session) -> Decimal:
    preferred = _find_active_preferred(item)
    markup = resolve_markup(item, preferred, session)
    return (preferred.cost_price + markup) if preferred else markup


def get_price_detail(item: Item, session):
    preferred = _find_active_preferred(item)
    markup = resolve_markup(item, preferred, session)
    markup_source = get_markup_source(item, preferred, session)
    price_final = (preferred.cost_price + markup) if preferred else markup
    return {
        "price_final": price_final,
        "effective_markup": markup,
        "markup_source": markup_source,
        "preferred": preferred,
    }
