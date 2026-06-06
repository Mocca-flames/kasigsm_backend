from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from sqlmodel import select, or_
from datetime import datetime, timezone

from app.database import get_session
from app.models.item import Item, ItemType, Provider, ProviderListing
from app.schemas.item import ItemPublic, ItemDetail, ItemsPageResponse
from app.services.pricing import get_price_final_bulk, build_markup_map, get_price_final
from app.utils.media import resolve_media_url
from app.services.search import resolve_category
from app.utils.slug import token_matches_slug, slug_tokens, DEVICE_PREFIXES, matches_slug_query
from app.models.banner import Banner
from app.schemas.banner import BannerPublic
import re

router = APIRouter()


def _slug_search_score(slug: str, query: str) -> int:
    q_lower = query.lower().strip()
    q_tokens = [t for t in re.split(r"[\s-]+", q_lower) if t]
    if not q_tokens:
        return 0
    score = 0
    if q_lower in slug.lower():
        score += 10
    tokens = slug_tokens(slug)
    normalized = [DEVICE_PREFIXES.get(t, t) for t in tokens]
    all_match = True
    token_match = 0
    for qt in q_tokens:
        nqt = DEVICE_PREFIXES.get(qt, qt)
        matched = any(nqt == t or t.startswith(nqt) or nqt.startswith(t) for t in normalized)
        if matched:
            token_match += 1
        else:
            all_match = False
    if all_match and q_tokens:
        score += 5
    score += token_match
    return score


@router.get("/items", response_model=ItemsPageResponse)
def list_items(
    item_type: Optional[ItemType] = None,
    category: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search by title or slug tokens for phones/devices/brands"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session = Depends(get_session)
):
    resolved_category = None
    category_messages = []
    if category:
        resolved_category, category_messages = resolve_category(category)

    if item_type == ItemType.SERVICE and not (resolved_category or category):
        resolved_category = "Remote Services"
        search_categories = ["Remote Services", "Tool Rental"]
    else:
        search_categories = [resolved_category] if resolved_category else None

    active_subq = (
        select(ProviderListing.item_id)
        .join(Provider)
        .where(
            ProviderListing.is_active == True,
            Provider.is_active == True,
        )
    )

    q = search.lower().strip() if search else None

    stmt = select(Item).where(
        Item.is_visible == True,
        Item.is_archived == False,
        Item.id.in_(active_subq),
    )
    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
    if search_categories:
        stmt = stmt.where(Item.category.in_(search_categories))
    elif resolved_category:
        stmt = stmt.where(Item.category == resolved_category)

    if q:
        stmt = stmt.where(
            or_(
                Item.title.ilike(f"%{q}%"),
                Item.slug.op("~*")(re.escape(q)),
            )
        )

    total_stmt = stmt
    total = len(session.exec(total_stmt).all())

    stmt = stmt.order_by(Item.created_at.desc()).offset((page - 1) * limit).limit(limit)
    items = session.exec(stmt).all()

    markup_map = build_markup_map(items, session)

    results = []
    filtered_items = []
    for item in items:
        if q and not matches_slug_query(item.slug, search) and q not in item.title.lower():
            continue
        filtered_items.append(item)

    if q:
        filtered_items.sort(key=lambda i: -_slug_search_score(i.slug, search))

    for item in filtered_items:
        price_final = get_price_final_bulk(item, markup_map)
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
            meta=item.meta,
        ))

    return {"items": results, "total": total, "page": page, "limit": limit}


@router.get("/items/{slug}", response_model=ItemDetail)
def get_item(slug: str, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.slug == slug)).first()
    if not item or not item.is_visible or item.is_archived:
        raise HTTPException(status_code=404, detail="Item not found")
    
    price_final = get_price_final(item, session)
    active_listings = [pl for pl in item.provider_listings if pl.is_active and pl.provider and pl.provider.is_active]
    media_url = resolve_media_url(item.thumbnail)

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
        meta=item.meta,
    )


@router.get("/banners", response_model=List[BannerPublic])
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
        active_banners.append(BannerPublic(
            id=str(b.id),
            slug=b.slug,
            title=b.title,
            content=b.content,
            image_url=resolve_media_url(b.image_url),
            link_url=b.link_url,
            is_dismissible=b.is_dismissible,
            starts_at=b.starts_at,
            ends_at=b.ends_at,
        ))
    
    return active_banners