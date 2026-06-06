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


def get_price_final(item: Item, session) -> Decimal:
    preferred = _find_active_preferred(item)
    markup = resolve_markup(item, preferred, session)
    return (preferred.cost_price + markup) if preferred else markup


def get_price_detail(item: Item, session):
    preferred = _find_active_preferred(item)
    markup = resolve_markup(item, preferred, session)
    markup_source = (
        "provider_category"
        if preferred and preferred.provider_id and preferred.is_active
        and session.exec(
            select(ProviderCategoryMarkup).where(
                ProviderCategoryMarkup.provider_id == preferred.provider_id,
                ProviderCategoryMarkup.category == item.category,
            )
        ).first()
        else "item"
    )
    price_final = (preferred.cost_price + markup) if preferred else markup
    return {
        "price_final": price_final,
        "effective_markup": markup,
        "markup_source": markup_source,
        "preferred": preferred,
    }


def build_markup_map(items: list[Item], session) -> dict:
    provider_ids = {pl.provider_id for item in items for pl in item.provider_listings if pl.is_active and pl.provider_id}
    categories = {item.category for item in items}
    markup_map: dict[tuple, Decimal] = {}
    if not provider_ids or not categories:
        return markup_map
    stmt = select(ProviderCategoryMarkup).where(
        ProviderCategoryMarkup.provider_id.in_(provider_ids),
        ProviderCategoryMarkup.category.in_(categories),
    )
    rows = session.exec(stmt).all()
    for row in rows:
        markup_map[(row.provider_id, row.category)] = row.price_markup
    return markup_map


def get_price_final_bulk(item: Item, markup_map: dict) -> Decimal:
    preferred = _find_active_preferred(item)
    key = (preferred.provider_id, item.category) if preferred and preferred.provider_id else None
    markup = markup_map.get(key, item.price_markup) if key else item.price_markup
    return (preferred.cost_price + markup) if preferred else markup
