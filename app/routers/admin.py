from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, File, Query
from typing import List, Optional, Dict
from decimal import Decimal
import shutil
import uuid
import os
from sqlmodel import select, func
import json
import csv
import io
import re
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from app.database import get_session
from app.models.item import Item, ItemType, Provider, ProviderListing
from app.models.user import User, UserRole
from app.models.technician import Technician, TechnicianStatus
from app.models.order import Order, OrderStatus, OrderItem
from app.models.credential import Credential
from app.models.wallet import Wallet
from app.models.banner import Banner
from app.models.category import Category, ProviderCategoryMarkup
from app.schemas.item import ItemDetail, ItemCreate, ItemEdit, BulkMarkupResponse
from app.schemas.banner import BannerCreate, BannerEdit, BannerPublic
from app.schemas.technician import TechnicianResponse, TechnicianReview
from app.schemas.order import OrderFulfill, StatsSummaryResponse
from app.services.pricing import get_price_detail
from app.services.search import resolve_category
from app.utils.encryption import encrypt_payload
from app.utils.security import require_admin, get_current_user
from app.utils.media import resolve_media_url
from app.utils.slug import DEVICE_PREFIXES, slug_tokens, token_matches_slug, slug_search_score, brand_from_slug

router = APIRouter()


def build_item_detail(item: Item, session) -> ItemDetail:
    detail = get_price_detail(item, session)
    media_url = resolve_media_url(item.thumbnail)

    low_stock = False
    if item.item_type == ItemType.SERVICE:
        total = session.exec(
            select(func.count(Credential.id)).where(Credential.item_id == item.id)
        ).first() or 0
        used = session.exec(
            select(func.count(Credential.id)).where(Credential.item_id == item.id, Credential.is_used == True)
        ).first() or 0
        remaining = total - used
        low_stock = remaining < 3

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
        price_final=detail["price_final"],
        currency=item.currency,
        delivery_time=item.delivery_time,
        stock=item.stock,
        is_visible=item.is_visible,
        low_stock=low_stock,
        provider_listings=[
            {
                "provider": listing.provider.name if listing.provider else "",
                "cost_price": listing.cost_price,
                "currency": item.currency,
                "is_preferred": listing.is_preferred,
            }
            for listing in item.provider_listings
        ],
        effective_markup=detail["effective_markup"],
        markup_source=detail["markup_source"],
    )


@router.get("/items", response_model=List[ItemDetail])
def list_all_items(
    session = Depends(get_session),
    q: Optional[str] = Query(default=None, description="Search by title, slug tokens, phone model, brand (iphone, samsung, xiaomi, etc.)"),
    item_type: Optional[ItemType] = Query(default=None),
    category: Optional[str] = Query(default=None),
    service_type: Optional[str] = Query(default=None, description="Filter SERVICE items by service_type meta field value"),
    service: Optional[str] = Query(default=None, description="Filter items whose title/slug contains 'service' keyword"),
    product: Optional[bool] = Query(default=None, description="Filter by type: true=PRODUCT, false=SERVICE"),
    brand: Optional[str] = Query(default=None, description="Filter by phone/device brand from slug (iphone, samsung, xiaomi, huawei, etc.)"),
    with_media: bool = Query(default=False, description="When true, resolve and include full media_url for all items"),
    alphabetize: bool = Query(default=False, description="When enabled without a query, sort result alphabetically by title"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(Item).where(Item.is_archived == False, Item.is_visible == True)

    if item_type:
        stmt = stmt.where(Item.item_type == item_type)
    if category:
        resolved_category, _ = resolve_category(category)
        stmt = stmt.where(Item.category == (resolved_category or category))

    rows = list(session.exec(stmt).all())

    if q:
        q_lower = q.lower().strip()
        q_tokens = [t for t in re.split(r"[\s-]+", q_lower) if t]

        def _score(item: Item) -> int:
            score = 0
            score += slug_search_score(item.slug, q)

            q_in_title = q_lower in item.title.lower()
            if q_in_title:
                score += 3

            title_lower = item.title.lower()
            for qt in q_tokens:
                if qt in title_lower:
                    score += 1

            try:
                price_match = int(qt)
                if str(price_match) in title_lower or "price" in title_lower:
                    score += 1
            except ValueError:
                pass

            return score

        scored = [(_score(i), i) for i in rows]
        scored.sort(key=lambda x: -x[0])
        rows = [i for s, i in scored if s > 0]

    if brand and not q:
        norm_brand = brand.lower().strip()
        def _brand_match(item: Item) -> bool:
            item_brand = brand_from_slug(item.slug)
            if item_brand is None:
                return False
            if item_brand == norm_brand:
                return True
            if item_brand.startswith(norm_brand) or norm_brand.startswith(item_brand):
                return True
            return False

        rows = [i for i in rows if _brand_match(i)]

    if product is not None:
        target_type = ItemType.PRODUCT if product else ItemType.SERVICE
        rows = [i for i in rows if i.item_type == target_type]

    if service_type:
        rows = [i for i in rows if i.meta and i.meta.get("service_type", "").lower() == service_type.lower()]

    if service and not q:
        svc_lower = service.lower()
        rows = [i for i in rows if svc_lower in i.title.lower() or svc_lower in i.slug.lower()]

    if alphabetize and not q:
        rows.sort(key=lambda i: i.title.lower())

    total = len(rows)
    items = rows[offset:offset + limit]

    if not items:
        return []

    return _build_admin_items(items, session, include_media=with_media)


def _build_admin_items(items: List[Item], session, include_media: bool = False) -> List[ItemDetail]:
    item_ids = [item.id for item in items]

    listings = session.exec(
        select(ProviderListing).where(ProviderListing.item_id.in_(item_ids), ProviderListing.is_active == True)
    ).all()

    preferred_by_item = {}
    for pl in listings:
        if pl.provider and pl.provider.is_active:
            preferred_by_item.setdefault(pl.item_id, []).append(pl)

    provider_ids = {pl.provider_id for pl in listings if pl.provider and pl.provider.is_active}
    categories = {item.category for item in items}
    markups = {}
    if provider_ids and categories:
        markup_rows = session.exec(
            select(ProviderCategoryMarkup).where(
                ProviderCategoryMarkup.provider_id.in_(list(provider_ids)),
                ProviderCategoryMarkup.category.in_(list(categories)),
            )
        ).all()
        for m in markup_rows:
            markups[(m.provider_id, m.category)] = m.price_markup

    cred_counts = {}
    if items:
        cred_rows = session.exec(
            select(Credential.item_id, func.count(Credential.id))
            .where(Credential.item_id.in_(item_ids))
            .group_by(Credential.item_id)
        ).all()
        for item_id, total in cred_rows:
            cred_counts[item_id] = {"total": total, "used": 0}

    used_rows = session.exec(
        select(Credential.item_id, func.count(Credential.id))
        .where(Credential.item_id.in_(item_ids), Credential.is_used == True)
        .group_by(Credential.item_id)
    ).all()
    for item_id, used in used_rows:
        if item_id in cred_counts:
            cred_counts[item_id]["used"] = used

    results = []
    for item in items:
        pref_list = preferred_by_item.get(item.id, [])
        preferred = pref_list[0] if pref_list else None
        markup = item.price_markup
        markup_source = "item"
        if preferred and preferred.provider_id and preferred.is_active:
            override = markups.get((preferred.provider_id, item.category))
            if override is not None:
                markup = override
                markup_source = "provider_category"

        price_final = (preferred.cost_price + markup) if preferred else markup

        cc = cred_counts.get(item.id, {"total": 0, "used": 0})
        remaining = cc["total"] - cc["used"]
        low_stock = remaining < 3

        media_url = resolve_media_url(item.thumbnail) if include_media else None

        results.append(ItemDetail(
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
            low_stock=low_stock,
            provider_listings=[
                {
                    "provider": listing.provider.name if listing.provider else "",
                    "cost_price": listing.cost_price,
                    "currency": item.currency,
                    "is_preferred": listing.is_preferred,
                }
                for listing in pref_list
            ],
            effective_markup=markup,
            markup_source=markup_source,
        ))
    return results


@router.get("/providers", response_model=list[dict])
def list_providers(session = Depends(get_session)):
    providers = session.exec(select(Provider)).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "is_active": p.is_active,
            "base_url": p.base_url,
            "notes": p.notes,
        }
        for p in providers
    ]


@router.get("/categories", response_model=list[dict])
def list_categories(session = Depends(get_session)):
    categories = session.exec(select(Category).order_by(Category.name)).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in categories
    ]


@router.post("/categories", response_model=dict)
def create_category(name: str, description: Optional[str] = None, session = Depends(get_session)):
    existing = session.exec(select(Category).where(Category.name == name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{name}' already exists")
    
    slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
    category = Category(name=name, slug=slug, description=description)
    session.add(category)
    session.commit()
    session.refresh(category)
    return {
        "id": str(category.id),
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_active": category.is_active,
    }


@router.patch("/categories/{category_id}", response_model=dict)
def update_category(category_id: str, name: Optional[str] = None, is_active: Optional[bool] = None, session = Depends(get_session)):
    category = session.exec(select(Category).where(Category.id == category_id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if name is not None:
        existing = session.exec(select(Category).where(Category.name == name, Category.id != category_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{name}' already exists")
        category.name = name
        category.slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
    if is_active is not None:
        category.is_active = is_active
    
    session.commit()
    session.refresh(category)
    return {
        "id": str(category.id),
        "name": category.name,
        "slug": category.slug,
        "is_active": category.is_active,
    }


@router.delete("/categories/{category_id}")
def delete_category(category_id: str, session = Depends(get_session)):
    category = session.exec(select(Category).where(Category.id == category_id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    dependent = session.exec(select(Item).where(Item.category == category.name)).first()
    if dependent:
        raise HTTPException(status_code=400, detail=f"Cannot deactivate category '{category.name}': items still reference it")
    
    session.delete(category)
    session.commit()
    return {"message": f"Category '{category.name}' deleted"}


@router.get("/providers/{provider_id}/markups", response_model=list[dict])
def list_provider_markups(provider_id: str, session = Depends(get_session)):
    provider = session.exec(select(Provider).where(Provider.id == provider_id)).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    markups = session.exec(
        select(ProviderCategoryMarkup).where(ProviderCategoryMarkup.provider_id == provider_id)
    ).all()
    return [
        {
            "id": str(m.id),
            "category": m.category,
            "price_markup": m.price_markup,
        }
        for m in markups
    ]


@router.post("/providers/{provider_id}/markups", response_model=dict)
def upsert_provider_markup(provider_id: str, category: str, price_markup: Decimal, session = Depends(get_session)):
    provider = session.exec(select(Provider).where(Provider.id == provider_id)).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    existing = session.exec(
        select(ProviderCategoryMarkup).where(
            ProviderCategoryMarkup.provider_id == provider_id,
            ProviderCategoryMarkup.category == category,
        )
    ).first()
    
    if existing:
        existing.price_markup = price_markup
        session.commit()
        session.refresh(existing)
        return {
            "id": str(existing.id),
            "provider_id": str(existing.provider_id),
            "category": existing.category,
            "price_markup": existing.price_markup,
        }
    
    markup = ProviderCategoryMarkup(provider_id=provider_id, category=category, price_markup=price_markup)
    session.add(markup)
    session.commit()
    session.refresh(markup)
    return {
        "id": str(markup.id),
        "provider_id": str(markup.provider_id),
        "category": markup.category,
        "price_markup": markup.price_markup,
    }


@router.delete("/providers/{provider_id}/markups/{category}")
def delete_provider_markup(provider_id: str, category: str, session = Depends(get_session)):
    markup = session.exec(
        select(ProviderCategoryMarkup).where(
            ProviderCategoryMarkup.provider_id == provider_id,
            ProviderCategoryMarkup.category == category,
        )
    ).first()
    if not markup:
        raise HTTPException(status_code=404, detail="Markup not found")
    
    session.delete(markup)
    session.commit()
    return {"message": f"Markup for category '{category}' removed"}


@router.post("/categories/{category_name}/markup/bulk", response_model=BulkMarkupResponse)
def bulk_category_markup(
    category_name: str,
    markup: Decimal,
    session = Depends(get_session),
    admin = Depends(require_admin)
):
    category = session.exec(select(Category).where(Category.name == category_name)).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
    
    items = session.exec(
        select(Item).where(Item.category == category_name, Item.is_archived == False)
    ).all()
    
    updated = []
    for item in items:
        item.price_markup = markup
        session.add(item)
        updated.append({
            "id": str(item.id),
            "title": item.title,
            "new_price_markup": markup,
        })
    
    session.commit()
    
    return BulkMarkupResponse(
        message=f"Bulk markup applied to {len(updated)} items",
        category=category_name,
        markup_type="flat",
        items_updated=len(updated),
        updated_items=updated,
    )


@router.post("/categories/{category_name}/markup/bulk-percentage", response_model=BulkMarkupResponse)
def bulk_category_markup_percentage(
    category_name: str,
    percentage: Decimal,
    session = Depends(get_session),
    admin = Depends(require_admin)
):
    if percentage < 0 or percentage > 100:
        raise HTTPException(status_code=400, detail="Percentage must be between 0 and 100")
    
    category = session.exec(select(Category).where(Category.name == category_name)).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
    
    items = session.exec(
        select(Item).where(Item.category == category_name, Item.is_archived == False)
    ).all()
    
    updated = []
    for item in items:
        preferred = None
        for pl in item.provider_listings:
            if pl.is_active and pl.provider and pl.provider.is_active:
                preferred = pl
                break
        
        if preferred:
            new_markup = (preferred.cost_price * percentage) / Decimal("100")
            item.price_markup = new_markup.quantize(Decimal("0.01"))
            updated.append({
                "id": str(item.id),
                "title": item.title,
                "cost_price": preferred.cost_price,
                "new_price_markup": item.price_markup,
            })
        else:
            item.price_markup = Decimal("0")
            updated.append({
                "id": str(item.id),
                "title": item.title,
                "cost_price": None,
                "new_price_markup": Decimal("0"),
            })
        
        session.add(item)
    
    session.commit()
    
    return BulkMarkupResponse(
        message=f"Bulk percentage markup applied to {len(updated)} items",
        category=category_name,
        markup_type="percentage",
        items_updated=len(updated),
        updated_items=updated,
    )


SUPPORTED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def _sanitize_filename(filename: str) -> str:
    base, ext = os.path.splitext(filename)
    ext = ext.lower().strip(".")
    base = base.replace(" ", "-")
    return f"{uuid.uuid4().hex}.{ext}"


def _safe_local_path(filename: str) -> str:
    dest = os.path.join(settings.MEDIA_ROOT, filename)
    if not dest.startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise ValueError("Invalid target path")
    return dest


def _save_upload(upload_file: UploadFile) -> str:
    upload_file.file.seek(0, os.SEEK_END)
    size = upload_file.file.tell()
    upload_file.file.seek(0)
    if size > settings.MAX_UPLOAD_BYTES:
        raise ValueError("File too large")
    ext = upload_file.filename.split(".")[-1].lower().strip()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type")
    safe_name = _sanitize_filename(upload_file.filename)
    dest = _safe_local_path(safe_name)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return f"{settings.MEDIA_PUBLIC_URL}/{safe_name}"


@router.post("/upload", response_model=dict)
def upload_media(file: UploadFile = File(...)):
    try:
        url = _save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        file.file.close()
    return {"url": url}


@router.patch("/providers/{provider_id}/logo", response_model=dict)
def update_provider_logo(provider_id: str, logo_url: Optional[str] = None, file: UploadFile = File(None), session = Depends(get_session)):
    provider = session.exec(select(Provider).where(Provider.id == provider_id)).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if file is not None:
        try:
            provider.logo_url = _save_upload(file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            file.file.close()
    elif logo_url is not None:
        provider.logo_url = logo_url
    else:
        raise HTTPException(status_code=400, detail="Provide either file or logo_url")
    session.commit()
    session.refresh(provider)
    return {"id": str(provider.id), "logo_url": provider.logo_url}


@router.patch("/items/{item_id}/thumbnail", response_model=dict)
def update_item_thumbnail(item_id: str, thumbnail_url: Optional[str] = None, file: UploadFile = File(None), session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if file is not None:
        try:
            item.thumbnail = _save_upload(file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            file.file.close()
    elif thumbnail_url is not None:
        item.thumbnail = thumbnail_url
    else:
        raise HTTPException(status_code=400, detail="Provide either file or thumbnail_url")
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"id": str(item.id), "thumbnail": item.thumbnail, "media_url": resolve_media_url(item.thumbnail)}


@router.patch("/providers/{provider_id}", response_model=dict)
def toggle_provider(provider_id: str, is_active: bool, session = Depends(get_session)):
    provider = session.exec(select(Provider).where(Provider.id == provider_id)).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider.is_active = is_active
    session.commit()
    session.refresh(provider)
    return {"id": str(provider.id), "name": provider.name, "is_active": provider.is_active}


@router.post("/items", response_model=ItemDetail)
def create_item(item_in: ItemCreate, session = Depends(get_session)):
    valid_cat = session.exec(select(Category).where(Category.name == item_in.category)).first()
    if not valid_cat:
        all_cats = [c.name for c in session.exec(select(Category)).all()]
        raise HTTPException(
            status_code=400,
            detail=f"Category '{item_in.category}' is not recognized. Valid categories: {all_cats}"
        )
    
    meta = {}
    if item_in.uid:
        meta["uid"] = item_in.uid
    
    item = Item(
        slug=item_in.slug,
        title=item_in.title,
        description=item_in.description,
        item_type=item_in.item_type,
        category=item_in.category,
        thumbnail=item_in.thumbnail,
        price_markup=item_in.price_markup,
        currency=item_in.currency,
        delivery_time=item_in.delivery_time,
        stock=item_in.stock,
        is_visible=True,
        meta=meta if meta else None,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    
    return build_item_detail(item, session)


@router.patch("/items/{item_id}", response_model=ItemDetail)
def edit_item(item_id: str, item_in: ItemEdit, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    for field, value in item_in.model_dump(exclude_unset=True).items():
        if field == "category" and value is not None:
            valid_cat = session.exec(select(Category).where(Category.name == value)).first()
            if not valid_cat:
                all_cats = [c.name for c in session.exec(select(Category)).all()]
                raise HTTPException(
                    status_code=400,
                    detail=f"Category '{value}' is not recognized. Valid categories: {all_cats}"
                )
        if field == "uid":
            if value is not None:
                item.uid = value
        else:
            setattr(item, field, value)
    session.commit()
    session.refresh(item)
    
    return build_item_detail(item, session)


@router.patch("/items/{item_id}/markup", response_model=ItemDetail)
def set_markup(item_id: str, markup: Decimal, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.price_markup = markup
    session.commit()
    session.refresh(item)
    
    return build_item_detail(item, session)


@router.patch("/items/{item_id}/visibility", response_model=ItemDetail)
def toggle_visibility(item_id: str, is_visible: bool, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_visible = is_visible
    session.commit()
    session.refresh(item)
    
    return build_item_detail(item, session)


@router.delete("/items/{item_id}")
def soft_delete_item(item_id: str, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_archived = True
    session.commit()
    return {"message": "Item archived"}


@router.get("/users", response_model=list[dict])
def list_users(session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return [{"id": str(u.id), "email": u.email, "role": u.role.value, "is_active": u.is_active} for u in users]


@router.patch("/users/{user_id}", response_model=dict)
def update_user(user_id: str, is_active: bool, session = Depends(get_session)):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    session.commit()
    return {"id": str(user.id), "email": user.email, "is_active": user.is_active}


@router.get("/orders", response_model=list[dict])
def list_orders(status: str = None, session = Depends(get_session)):
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == OrderStatus(status))
    orders = session.exec(stmt).all()
    return [{"id": str(o.id), "status": o.status.value, "total_amount": o.total_amount} for o in orders]


@router.patch("/orders/{order_id}/status", response_model=dict)
def update_order_status(order_id: str, status: str, session = Depends(get_session)):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = OrderStatus(status)
    session.commit()
    return {"id": str(order.id), "status": order.status.value}


@router.post("/credentials/bulk", response_model=dict)
def bulk_upload_credentials(
    item_id: str,
    credentials_file: UploadFile = File(...),
    session = Depends(get_session),
    admin = Depends(require_admin)
):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.item_type != ItemType.SERVICE:
        raise HTTPException(status_code=400, detail="Credentials can only be uploaded for SERVICE items")
    
    content = credentials_file.file.read()
    credentials_file.file.close()
    
    credentials = []
    ext = credentials_file.filename.split('.')[-1].lower()
    
    if ext == 'json':
        data = json.loads(content)
        credentials = data if isinstance(data, list) else [data]
    elif ext == 'csv':
        reader = csv.DictReader(io.StringIO(content.decode()))
        credentials = list(reader)
    else:
        raise HTTPException(status_code=400, detail="File must be JSON or CSV")
    
    created = 0
    for cred in credentials:
        if isinstance(cred, dict):
            payload = json.dumps(cred)
        else:
            payload = str(cred)
        
        encrypted = encrypt_payload(payload)
        credential = Credential(item_id=item_id, payload=encrypted)
        session.add(credential)
        created += 1
    
    session.commit()
    return {"item_id": item_id, "credentials_added": created}


@router.get("/credentials/{item_id}", response_model=dict)
def get_credential_pool(item_id: str, session = Depends(get_session)):
    item = session.exec(select(Item).where(Item.id == item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    total = session.exec(
        select(func.count(Credential.id)).where(Credential.item_id == item_id)
    ).first() or 0
    
    used = session.exec(
        select(func.count(Credential.id)).where(Credential.item_id == item_id, Credential.is_used == True)
    ).first() or 0
    
    remaining = total - used
    
    return {
        "item_id": item_id,
        "item_title": item.title,
        "total": total,
        "used": used,
        "remaining": remaining,
        "low_stock": remaining < 3
    }


@router.get("/banners", response_model=List[dict])
def list_banners(session=Depends(get_session)):
    banners = session.exec(select(Banner)).all()
    return [{
        "id": str(b.id),
        "slug": b.slug,
        "title": b.title,
        "content": b.content,
        "image_url": b.image_url,
        "link_url": b.link_url,
        "is_active": b.is_active,
        "is_dismissible": b.is_dismissible,
        "starts_at": b.starts_at.isoformat() if b.starts_at else None,
        "ends_at": b.ends_at.isoformat() if b.ends_at else None,
        "created_at": b.created_at.isoformat()
    } for b in banners]


@router.post("/banners", response_model=dict)
def create_banner(banner_in: BannerCreate, session=Depends(get_session)):
    banner = Banner(
        slug=banner_in.slug,
        title=banner_in.title,
        content=banner_in.content,
        image_url=banner_in.image_url,
        link_url=banner_in.link_url,
        is_active=banner_in.is_active,
        is_dismissible=banner_in.is_dismissible,
        starts_at=banner_in.starts_at,
        ends_at=banner_in.ends_at,
    )
    session.add(banner)
    session.commit()
    session.refresh(banner)
    return {
        "id": str(banner.id),
        "slug": banner.slug,
        "title": banner.title,
        "content": banner.content,
        "image_url": banner.image_url,
        "link_url": banner.link_url,
        "is_active": banner.is_active,
        "is_dismissible": banner.is_dismissible,
        "starts_at": banner.starts_at.isoformat() if banner.starts_at else None,
        "ends_at": banner.ends_at.isoformat() if banner.ends_at else None,
    }


@router.patch("/banners/{banner_id}", response_model=dict)
def edit_banner(banner_id: str, banner_in: BannerEdit, session=Depends(get_session)):
    banner = session.exec(select(Banner).where(Banner.id == banner_id)).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    for field, value in banner_in.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    session.commit()
    session.refresh(banner)
    
    return {
        "id": str(banner.id),
        "slug": banner.slug,
        "title": banner.title,
        "content": banner.content,
        "image_url": banner.image_url,
        "link_url": banner.link_url,
        "is_active": banner.is_active,
        "is_dismissible": banner.is_dismissible,
        "starts_at": banner.starts_at.isoformat() if banner.starts_at else None,
        "ends_at": banner.ends_at.isoformat() if banner.ends_at else None,
    }


@router.delete("/banners/{banner_id}")
def delete_banner(banner_id: str, session=Depends(get_session)):
    banner = session.exec(select(Banner).where(Banner.id == banner_id)).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    session.delete(banner)
    session.commit()
    return {"message": "Banner deleted"}


@router.patch("/banners/{banner_id}/toggle", response_model=dict)
def toggle_banner(banner_id: str, is_active: bool, session=Depends(get_session)):
    banner = session.exec(select(Banner).where(Banner.id == banner_id)).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    banner.is_active = is_active
    session.commit()
    session.refresh(banner)
    return {
        "id": str(banner.id),
        "is_active": banner.is_active,
    }


@router.patch("/banners/{banner_id}/image", response_model=dict)
def upload_banner_image(banner_id: str, image_url: Optional[str] = None, file: UploadFile = File(None), session=Depends(get_session)):
    banner = session.exec(select(Banner).where(Banner.id == banner_id)).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    if file is not None:
        try:
            banner.image_url = _save_upload(file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            file.file.close()
    elif image_url is not None:
        banner.image_url = image_url
    else:
        raise HTTPException(status_code=400, detail="Provide either file or image_url")
    session.commit()
    session.refresh(banner)
    return {
        "id": str(banner.id),
        "image_url": banner.image_url,
        "media_url": resolve_media_url(banner.image_url),
    }


@router.get("/technicians/requests", response_model=list[TechnicianResponse])
def list_technician_requests(session = Depends(get_session), admin = Depends(require_admin)):
    technicians = session.exec(
        select(Technician, User).where(Technician.status == TechnicianStatus.PENDING).join(User, Technician.user_id == User.id)
    ).all()
    results = []
    for tech, usr in technicians:
        results.append(TechnicianResponse(
            id=str(tech.id),
            user_id=str(tech.user_id),
            email=usr.email,
            role=usr.role.value,
            status=tech.status.value,
            specialization=tech.specialization,
            created_at=tech.created_at.isoformat() if tech.created_at else None,
        ))
    return results


@router.get("/technicians", response_model=list[TechnicianResponse])
def list_all_technicians(session = Depends(get_session), admin = Depends(require_admin)):
    technicians = session.exec(
        select(Technician, User).join(User, Technician.user_id == User.id)
    ).all()
    results = []
    for tech, usr in technicians:
        results.append(TechnicianResponse(
            id=str(tech.id),
            user_id=str(tech.user_id),
            email=usr.email,
            role=usr.role.value,
            status=tech.status.value,
            specialization=tech.specialization,
            created_at=tech.created_at.isoformat() if tech.created_at else None,
        ))
    return results


@router.get("/orders/fulfillment-queue", response_model=list[dict])
def list_fulfillment_queue(session = Depends(get_session), admin = Depends(require_admin)):
    orders = session.exec(
        select(Order).where(Order.status == OrderStatus.PAID)
    ).all()
    queue = []
    for order in orders:
        needs_fulfillment = False
        for oi in order.items:
            item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
            if item and item.item_type.value == "SERVICE":
                already_credentialed = session.exec(
                    select(Credential).where(Credential.order_item_id == oi.id)
                ).first()
                if not already_credentialed:
                    needs_fulfillment = True
                    break
        if needs_fulfillment:
            queue.append({
                "id": str(order.id),
                "status": order.status.value,
                "total_amount": order.total_amount,
                "currency": order.currency,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items": [
                    {
                        "id": str(oi.id),
                        "item_id": str(oi.item_id),
                        "quantity": oi.quantity,
                        "unit_price": oi.unit_price,
                    }
                    for oi in order.items
                ],
            })
    return queue


@router.get("/orders/{order_id}/ready", response_model=dict)
def get_order_fulfillment_detail(order_id: str, session = Depends(get_session), admin = Depends(require_admin)):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Order is not PAID")
    
    items_detail = []
    for oi in order.items:
        item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
        if not item:
            continue
        items_detail.append({
            "order_item_id": str(oi.id),
            "item_id": str(item.id),
            "title": item.title,
            "item_type": item.item_type.value,
            "quantity": oi.quantity,
            "unit_price": oi.unit_price,
        })
    
    return {
        "id": str(order.id),
        "status": order.status.value,
        "total_amount": order.total_amount,
        "currency": order.currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": items_detail,
    }


@router.post("/orders/{order_id}/fulfill", response_model=dict)
def fulfill_order_manual(order_id: str, fulfill_in: OrderFulfill, session = Depends(get_session), admin = Depends(require_admin)):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Order is not PAID")
    
    order_item_ids = {str(oi.id) for oi in order.items}
    
    for cred_assignment in fulfill_in.credentials:
        try:
            oi_id = uuid.UUID(cred_assignment.order_item_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid order_item_id: {cred_assignment.order_item_id}")
        
        if str(oi_id) not in order_item_ids:
            raise HTTPException(status_code=400, detail=f"order_item_id {oi_id} does not belong to this order")
        
        oi = session.exec(select(OrderItem).where(OrderItem.id == oi_id)).first()
        if not oi:
            raise HTTPException(status_code=404, detail=f"Order item not found: {oi_id}")
        
        item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
        if not item or item.item_type.value != "SERVICE":
            raise HTTPException(status_code=400, detail="Credentials can only be assigned to SERVICE items")
        
        already = session.exec(
            select(Credential).where(Credential.order_item_id == oi_id)
        ).first()
        if already:
            raise HTTPException(status_code=400, detail=f"Order item {oi_id} already has credentials assigned")
        
        encrypted = encrypt_payload(cred_assignment.payload)
        credential = Credential(item_id=oi.item_id, payload=encrypted, order_item_id=oi_id)
        session.add(credential)
    
    session.commit()
    
    user = session.exec(select(User).where(User.id == order.user_id)).first()
    if user:
        from app.services.email import send_credential_ready_email
        send_credential_ready_email(user.email, str(order.id), "Credentials assigned by admin")
    
    return {"order_id": str(order.id), "status": "fulfilled", "credentials_assigned": len(fulfill_in.credentials)}


@router.post("/orders/{order_id}/reject", response_model=dict)
def reject_order(order_id: str, session = Depends(get_session), admin = Depends(require_admin)):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Order is not PAID")
    
    order.status = OrderStatus.CANCELLED
    session.add(order)
    session.commit()
    
    wallet = session.exec(select(Wallet).where(Wallet.user_id == order.user_id)).first()
    if wallet:
        from app.services.wallet_service import refund_to_wallet
        try:
            wallet, tx = refund_to_wallet(session, wallet, order.total_amount, f"Refund for cancelled order {order.id}")
        except ValueError:
            wallet = None
    
    return {"order_id": str(order.id), "status": OrderStatus.CANCELLED.value}


@router.post("/technicians/{tech_id}/review", response_model=TechnicianResponse)
def review_technician(
    tech_id: str,
    review: TechnicianReview,
    session = Depends(get_session),
    admin = Depends(require_admin)
):
    technician = session.exec(select(Technician).where(Technician.id == tech_id)).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Technician request not found")
    if technician.status != TechnicianStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already reviewed")
    if review.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be approve or reject")
    user = session.exec(select(User).where(User.id == technician.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    technician.status = TechnicianStatus.APPROVED if review.action == "approve" else TechnicianStatus.REJECTED
    technician.reviewed_at = datetime.now(timezone.utc)
    technician.reviewed_by = admin.id
    if review.action == "approve":
        user.role = UserRole.TECHNICIAN
    session.commit()
    session.refresh(technician)
    session.refresh(user)
    return TechnicianResponse(
        id=str(technician.id),
        user_id=str(technician.user_id),
        email=user.email,
        role=user.role.value,
        status=technician.status.value,
        specialization=technician.specialization,
        created_at=technician.created_at.isoformat() if technician.created_at else None,
    )


@router.get("/stats/summary", response_model=StatsSummaryResponse)
def get_stats_summary(
    days: int = 30,
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    period_orders = session.exec(
        select(Order).where(Order.created_at >= cutoff)
    ).all()

    total_orders = len(period_orders)
    orders_by_status: Dict[str, int] = {}
    total_revenue = Decimal("0")
    fulfilled_orders = 0
    refunded_orders = 0

    for order in period_orders:
        status_val = order.status.value
        orders_by_status[status_val] = orders_by_status.get(status_val, 0) + 1
        if status_val == OrderStatus.FULFILLED:
            fulfilled_orders += 1
        if status_val == OrderStatus.REFUNDED:
            refunded_orders += 1
        if status_val in (OrderStatus.PAID, OrderStatus.FULFILLED):
            total_revenue += order.total_amount

    pending_fulfillment = orders_by_status.get(OrderStatus.PAID.value, 0) + orders_by_status.get(OrderStatus.PENDING.value, 0)

    total_clients = session.exec(
        select(func.count(User.id)).where(User.role == UserRole.CLIENT, User.is_active == True)
    ).first() or 0

    total_items = session.exec(
        select(func.count(Item.id)).where(Item.is_archived == False)
    ).first() or 0

    low_stock_items = 0

    return StatsSummaryResponse(
        period_days=days,
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        total_revenue=total_revenue,
        total_clients=total_clients,
        total_items=total_items,
        low_stock_items=low_stock_items,
        fulfilled_orders=fulfilled_orders,
        pending_fulfillment=pending_fulfillment,
        refunded_orders=refunded_orders,
    )