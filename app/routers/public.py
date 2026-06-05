from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from sqlmodel import select
from datetime import datetime, timezone

from app.database import get_session
from app.models.item import Item, ItemType, Provider, ProviderListing
from app.schemas.item import ItemPublic, ItemDetail
from app.services.pricing import get_price_final
from app.utils.media import resolve_media_url
from app.services.search import resolve_category
from app.utils.slug import token_matches_slug, slug_tokens, DEVICE_PREFIXES
from app.models.banner import Banner
from app.config import settings
import re

router = APIRouter()


@router.get("/items", response_model=List[ItemPublic])
def list_items(
    item_type: Optional[ItemType] = None,
    category: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search by title or slug tokens for phones/devices/brands"),
    session = Depends(get_session)
):
    active_item_ids = (
        select(ProviderListing.item_id)
        .join(Provider)
        .where(
            ProviderListing.is_active == True,
            Provider.is_active == True,
        )
    )
    stmt = select(Item).where(
        Item.is_visible == True,
        Item.is_archived == False,
        Item.id.in_(active_item_ids),
    )
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
    if category:
        resolved_category, _ = resolve_category(category)
        stmt = stmt.where(Item.category == (resolved_category or category))
    items = session.exec(stmt).all()

    if search:
        q = search.lower().strip()
        q_tokens = [t for t in re.split(r"[\s-]+", q) if t]

        def _relevant(item: Item):
            slug_score = 0
            title_score = 0
            if token_matches_slug(item.slug, search):
                slug_score += 2
            if q in item.title.lower():
                title_score += 1
                for qt in q_tokens:
                    if qt in item.title.lower():
                        title_score += 1
                        break
            tokens = slug_tokens(item.slug)
            normalized = [DEVICE_PREFIXES.get(t, t) for t in tokens]
            for qt in q_tokens:
                nqt = DEVICE_PREFIXES.get(qt, qt)
                if any(nqt == t or t.startswith(nqt) or nqt.startswith(t) for t in normalized):
                    slug_score += 1
            return slug_score + title_score

        ranked = sorted(items, key=lambda i: -_relevant(i))
        items = [r for r in ranked if _relevant(r) > 0 or q in r.title.lower()]

    results = []
    for item in items:
        price_final = get_price_final(item, session)
        results.append(ItemPublic(
            id=str(item.id),
            uid=item.uid,
            slug=item.slug,
            title=item.title,
            description=item.description,
            item_type=item.item_type,
            category=item.category,
            thumbnail=item.thumbnail,
            media_url=resolve_media_url(item.thumbnail),
            price_final=price_final,
            currency=item.currency,
            delivery_time=item.delivery_time,
            stock=item.stock,
        ))
    return results


@router.get("/items/{slug}", response_model=ItemDetail)
def get_item(slug: str, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.slug == slug)).first()
    if not item or not item.is_visible or item.is_archived:
        raise HTTPException(status_code=404, detail="Item not found")
    
    price_final = get_price_final(item, session)
    active_listings = [pl for pl in item.provider_listings if pl.is_active and pl.provider and pl.provider.is_active]
    thumbnail_url = item.thumbnail or ""
    media_url = None
    if thumbnail_url:
        if thumbnail_url.startswith("http"):
            media_url = thumbnail_url
        elif thumbnail_url.startswith("/"):
            media_url = thumbnail_url
        else:
            media_url = f"{settings.MEDIA_PUBLIC_URL}/{thumbnail_url.lstrip('/')}"
    
    return ItemDetail(
        id=str(item.id),
        uid=item.uid,
        slug=item.slug,
        title=item.title,
        description=item.description,
        item_type=item.item_type,
        category=item.category,
        thumbnail=item.thumbnail,
        media_url=media_url,
        price_final=price_final,
        currency=item.currency,
        delivery_time=item.delivery_time,
        stock=item.stock,
        is_visible=item.is_visible,
        provider_listings=[
            {
                "provider": "",
                "cost_price": listing.cost_price,
                "currency": item.currency,
                "is_preferred": listing.is_preferred,
            }
            for listing in active_listings
        ],
    )


@router.get("/banners", response_model=List[dict])
def list_active_banners(session=Depends(get_session)):
    now = datetime.now(timezone.utc)
    stmt = select(Banner).where(Banner.is_active == True)
    banners = session.exec(stmt).all()
    
    active_banners = []
    for b in banners:
        if b.starts_at and b.starts_at > now:
            continue
        if b.ends_at and b.ends_at < now:
            continue
        active_banners.append({
            "id": str(b.id),
            "title": b.title,
            "content": b.content,
            "image_url": b.image_url,
            "link_url": b.link_url,
            "is_dismissible": b.is_dismissible,
        })
    
    return active_banners