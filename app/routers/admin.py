from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, File
from typing import List, Optional
from decimal import Decimal
from sqlmodel import select, func
import json
import csv
import io
import re
from datetime import datetime, timezone
from app.database import get_session
from app.models.item import Item, ItemType, Provider
from app.models.user import User, UserRole
from app.models.technician import Technician, TechnicianStatus
from app.models.order import Order, OrderStatus
from app.models.credential import Credential
from app.models.banner import Banner
from app.models.category import Category, ProviderCategoryMarkup
from app.schemas.item import ItemDetail, ItemCreate, ItemEdit
from app.schemas.banner import BannerCreate, BannerEdit, BannerPublic
from app.schemas.technician import TechnicianResponse, TechnicianReview
from app.services.pricing import get_price_detail
from app.utils.encryption import encrypt_payload
from app.utils.security import require_admin, get_current_user

router = APIRouter()


def build_item_detail(item: Item, session) -> ItemDetail:
    detail = get_price_detail(item, session)

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
def list_all_items(session = Depends(get_session)):
    items = session.exec(select(Item)).all()
    return [build_item_detail(item, session) for item in items]


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
    
    category.is_active = False
    session.commit()
    return {"message": f"Category '{category.name}' deactivated"}


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