from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from decimal import Decimal
from sqlmodel import select
from datetime import datetime, timezone

from app.database import get_session
from app.models.item import Item, ItemType, Provider, ProviderListing
from app.schemas.item import ItemPublic, ItemDetail
from app.services.pricing import get_price_final
from app.utils.media import resolve_media_url

router = APIRouter()


@router.get("/items", response_model=List[ItemPublic])
def list_items(
    item_type: Optional[ItemType] = None,
    category: Optional[str] = None,
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
        stmt = stmt.where(Item.category == category)
    items = session.exec(stmt).all()
    
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