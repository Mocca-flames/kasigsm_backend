from fastapi import APIRouter, Depends, Query
from sqlmodel import select, or_, func
from typing import Optional, List
from app.database import get_session
from app.models.device_catalog import (
    IssueCategory,
    Chipset,
    DeviceBrand,
    Tool,
    ToolCapability,
    DeviceCompatibility,
)
from app.schemas.admin_device_catalog import (
    ChipsetCreate,
    ChipsetEdit,
    DeviceBrandCreate,
    DeviceBrandEdit,
    IssueCategoryCreate,
    IssueCategoryEdit,
    ToolCreate,
    ToolEdit,
    ToolCapabilityCreate,
    ToolCapabilityEdit,
    DeviceCompatibilityCreate,
    DeviceCompatibilityEdit,
)
from app.utils.security import require_admin

router = APIRouter()


# Health check-style confirmation that admin device routes are mounted
@router.get("/ping")
def admin_device_ping():
    return {"ok": True, "scope": "admin_device_catalog"}


# Issue categories

@router.get("/device-catalog/issues", response_model=List[dict])
def list_admin_issues(
    q: Optional[str] = Query(default=None),
    session=Depends(get_session),
    admin=Depends(require_admin),
):
    stmt = select(IssueCategory)
    if q:
        stmt = stmt.where(or_(IssueCategory.label.ilike(f"%{q}%"), IssueCategory.slug.ilike(f"%{q}%")))
    rows = session.exec(stmt.order_by(IssueCategory.label)).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "label": r.label,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/device-catalog/issues", response_model=dict)
def create_issue(payload: IssueCategoryCreate, session=Depends(get_session), admin=Depends(require_admin)):
    existing = session.exec(select(IssueCategory).where(IssueCategory.slug == payload.slug)).first()
    if existing:
        raise ValueError(f"IssueCategory with slug '{payload.slug}' already exists")
    row = IssueCategory(slug=payload.slug, label=payload.label, is_active=payload.is_active)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "slug": row.slug, "label": row.label, "is_active": row.is_active}


@router.patch("/device-catalog/issues/{issue_id}", response_model=dict)
def update_issue(issue_id: str, payload: IssueCategoryEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(IssueCategory).where(IssueCategory.id == issue_id)).first()
    if not row:
        raise ValueError("Issue not found")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != row.slug:
        dup = session.exec(select(IssueCategory).where(IssueCategory.slug == data["slug"], IssueCategory.id != issue_id)).first()
        if dup:
            raise ValueError("IsoCategory slug already in use")
        row.slug = data["slug"]
    for k in ("label", "is_active"):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "slug": row.slug, "label": row.label, "is_active": row.is_active}


@router.delete("/device-catalog/issues/{issue_id}")
def delete_issue(issue_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(IssueCategory).where(IssueCategory.id == issue_id)).first()
    if not row:
        raise ValueError("Issue not found")
    session.delete(row)
    session.commit()
    return {"message": "Issue deleted"}


# Chipsets

@router.get("/device-catalog/chipsets", response_model=List[dict])
def list_chipsets(q: Optional[str] = Query(default=None), session=Depends(get_session), admin=Depends(require_admin)):
    stmt = select(Chipset)
    if q:
        stmt = stmt.where(or_(Chipset.label.ilike(f"%{q}%"), Chipset.key.ilike(f"%{q}%")))
    rows = session.exec(stmt.order_by(Chipset.key)).all()
    return [
        {
            "id": str(r.id),
            "key": r.key,
            "label": r.label,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/device-catalog/chipsets", response_model=dict)
def create_chipset(payload: ChipsetCreate, session=Depends(get_session), admin=Depends(require_admin)):
    existing = session.exec(select(Chipset).where(Chipset.key == payload.key)).first()
    if existing:
        raise ValueError("Chipset key already exists")
    row = Chipset(key=payload.key, label=payload.label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "key": row.key, "label": row.label}


@router.patch("/device-catalog/chipsets/{chipset_id}", response_model=dict)
def update_chipset(chipset_id: str, payload: ChipsetEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(Chipset).where(Chipset.id == chipset_id)).first()
    if not row:
        raise ValueError("Chipset not found")
    data = payload.model_dump(exclude_unset=True)
    if "key" in data and data["key"] != row.key:
        dup = session.exec(select(Chipset).where(Chipset.key == data["key"], Chipset.id != chipset_id)).first()
        if dup:
            raise ValueError("in_chipset_key_already_in_use")
        row.key = data["key"]
    for k in ("label",):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "key": row.key, "label": row.label}


@router.delete("/device-catalog/chipsets/{chipset_id}")
def delete_chipset(chipset_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(Chipset).where(Chipset.id == chipset_id)).first()
    if not row:
        raise ValueError("Chipset not found")
    session.delete(row)
    session.commit()
    return {"message": "Chipset deleted"}


# Brands

@router.get("/device-catalog/brands", response_model=List[dict])
def list_brands(q: Optional[str] = Query(default=None), session=Depends(get_session), admin=Depends(require_admin)):
    stmt = select(DeviceBrand)
    if q:
        stmt = stmt.where(or_(DeviceBrand.name.ilike(f"%{q}%"), DeviceBrand.slug.ilike(f"%{q}%")))
    rows = session.exec(stmt.order_by(DeviceBrand.name)).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "name": r.name,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/device-catalog/brands", response_model=dict)
def create_brand(payload: DeviceBrandCreate, session=Depends(get_session), admin=Depends(require_admin)):
    existing = session.exec(select(DeviceBrand).where(DeviceBrand.slug == payload.slug)).first()
    if existing:
        raise ValueError("Brand slug already exists")
    row = DeviceBrand(slug=payload.slug, name=payload.name, is_active=payload.is_active)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "slug": row.slug, "name": row.name, "is_active": row.is_active}


@router.patch("/device-catalog/brands/{brand_id}", response_model=dict)
def update_brand(brand_id: str, payload: DeviceBrandEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(DeviceBrand).where(DeviceBrand.id == brand_id)).first()
    if not row:
        raise ValueError("Brand not found")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != row.slug:
        dup = session.exec(select(DeviceBrand).where(DeviceBrand.slug == data["slug"], DeviceBrand.id != brand_id)).first()
        if dup:
            raise ValueError("Brand slug already in use")
        row.slug = data["slug"]
    for k in ("name", "is_active"):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "slug": row.slug, "name": row.name, "is_active": row.is_active}


@router.delete("/device-catalog/brands/{brand_id}")
def delete_brand(brand_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(DeviceBrand).where(DeviceBrand.id == brand_id)).first()
    if not row:
        raise ValueError("Brand not found")
    session.delete(row)
    session.commit()
    return {"message": "Brand deleted"}


# Tools

@router.get("/device-catalog/tools", response_model=List[dict])
def list_admin_tools(q: Optional[str] = Query(default=None), session=Depends(get_session), admin=Depends(require_admin)):
    stmt = select(Tool)
    if q:
        stmt = stmt.where(or_(Tool.name.ilike(f"%{q}%"), Tool.slug.ilike(f"%{q}%")))
    rows = session.exec(stmt.order_by(Tool.name)).all()
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "name": r.name,
            "description": r.description,
            "website_url": r.website_url,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/device-catalog/tools", response_model=dict)
def create_tool(payload: ToolCreate, session=Depends(get_session), admin=Depends(require_admin)):
    existing = session.exec(select(Tool).where(Tool.slug == payload.slug)).first()
    if existing:
        raise ValueError("Tool slug already exists")
    row = Tool(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        website_url=payload.website_url,
        is_active=payload.is_active,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": str(row.id),
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "website_url": row.website_url,
        "is_active": row.is_active,
    }


@router.patch("/device-catalog/tools/{tool_id}", response_model=dict)
def update_tool(tool_id: str, payload: ToolEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(Tool).where(Tool.id == tool_id)).first()
    if not row:
        raise ValueError("Tool not found")
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != row.slug:
        dup = session.exec(select(Tool).where(Tool.slug == data["slug"], Tool.id != tool_id)).first()
        if dup:
            raise ValueError("Tool slug already in use")
        row.slug = data["slug"]
    for k in ("name", "description", "website_url", "is_active"):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "slug": row.slug, "name": row.name, "description": row.description, "website_url": row.website_url, "is_active": row.is_active}


@router.delete("/device-catalog/tools/{tool_id}")
def delete_tool(tool_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(Tool).where(Tool.id == tool_id)).first()
    if not row:
        raise ValueError("Tool not found")
    session.delete(row)
    session.commit()
    return {"message": "Tool deleted"}


# Tool capabilities

@router.get("/device-catalog/tools/{tool_id}/capabilities", response_model=List[dict])
def list_tool_capabilities(tool_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    rows = session.exec(select(ToolCapability).where(ToolCapability.tool_id == tool_id).order_by(ToolCapability.issue_slug)).all()
    return [
        {
            "id": str(r.id),
            "tool_id": str(r.tool_id),
            "issue_slug": r.issue_slug,
            "platform": r.platform,
            "notes": r.notes,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.post("/device-catalog/tools/{tool_id}/capabilities", response_model=dict)
def create_tool_capability(tool_id: str, payload: ToolCapabilityCreate, session=Depends(get_session), admin=Depends(require_admin)):
    if str(payload.tool_id) != tool_id:
        raise ValueError("tool_id mismatch")
    existing = session.exec(
        select(ToolCapability).where(ToolCapability.tool_id == tool_id, ToolCapability.issue_slug == payload.issue_slug)
    ).first()
    if existing:
        raise ValueError("Capability already exists for this issue")
    row = ToolCapability(
        tool_id=tool_id,
        issue_slug=payload.issue_slug,
        platform=payload.platform,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": str(row.id),
        "tool_id": str(row.tool_id),
        "issue_slug": row.issue_slug,
        "platform": row.platform,
        "notes": row.notes,
        "is_active": row.is_active,
    }


@router.patch("/device-catalog/tools/{tool_id}/capabilities/{cap_id}", response_model=dict)
def update_tool_capability(tool_id: str, cap_id: str, payload: ToolCapabilityEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(ToolCapability).where(ToolCapability.id == cap_id, ToolCapability.tool_id == tool_id)).first()
    if not row:
        raise ValueError("Capability not found")
    data = payload.model_dump(exclude_unset=True)
    for k in ("issue_slug", "platform", "notes", "is_active"):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": str(row.id),
        "tool_id": str(row.tool_id),
        "issue_slug": row.issue_slug,
        "platform": row.platform,
        "notes": row.notes,
        "is_active": row.is_active,
    }


@router.delete("/device-catalog/tools/{tool_id}/capabilities/{cap_id}")
def delete_tool_capability(tool_id: str, cap_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(ToolCapability).where(ToolCapability.id == cap_id, ToolCapability.tool_id == tool_id)).first()
    if not row:
        raise ValueError("Capability not found")
    session.delete(row)
    session.commit()
    return {"message": "Capability deleted"}


# Device compatibilities

@router.get("/device-catalog/tools/{tool_id}/compatibilities", response_model=List[dict])
def list_tool_compatibilities(tool_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    rows = session.exec(select(DeviceCompatibility).where(DeviceCompatibility.tool_id == tool_id).order_by(DeviceCompatibility.brand_slot, DeviceCompatibility.chipset_key)).all()
    return [
        {
            "id": str(r.id),
            "tool_id": str(r.tool_id),
            "brand_slug": r.brand_slug,
            "chipset_key": r.chipset_key,
            "notes": r.notes,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.post("/device-catalog/tools/{tool_id}/compatibilities", response_model=dict)
def create_compatibility(tool_id: str, payload: DeviceCompatibilityCreate, session=Depends(get_session), admin=Depends(require_admin)):
    if str(payload.tool_id) != tool_id:
        raise ValueError("tool_id mismatch")
    row = DeviceCompatibility(
        tool_id=tool_id,
        brand_slug=payload.brand_slug,
        chipset_key=payload.chipset_key,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": str(row.id),
        "tool_id": str(row.tool_id),
        "brand_slug": row.brand_slug,
        "chipset_key": row.chipset_key,
        "notes": row.notes,
        "is_active": row.is_active,
    }


@router.patch("/device-catalog/tools/{tool_id}/compatibilities/{compat_id}", response_model=dict)
def update_compatibility(tool_id: str, compat_id: str, payload: DeviceCompatibilityEdit, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(DeviceCompatibility).where(DeviceCompatibility.id == compat_id, DeviceCompatibility.tool_id == tool_id)).first()
    if not row:
        raise ValueError("Compatibility not found")
    data = payload.model_dump(exclude_unset=True)
    for k in ("brand_slug", "chipset_key", "notes", "is_active"):
        if k in data:
            setattr(row, k, data[k])
    session.add(row)
    session.commit()
    session.refresh(row)
    return {
        "id": str(row.id),
        "tool_id": str(row.tool_id),
        "brand_slug": row.brand_slug,
        "chipset_key": row.chipset_key,
        "notes": row.notes,
        "is_active": row.is_active,
    }


@router.delete("/device-catalog/tools/{tool_id}/compatibilities/{compat_id}")
def delete_compatibility(tool_id: str, compat_id: str, session=Depends(get_session), admin=Depends(require_admin)):
    row = session.exec(select(DeviceCompatibility).where(DeviceCompatibility.id == compat_id, DeviceCompatibility.tool_id == tool_id)).first()
    if not row:
        raise ValueError("Compatibility not found")
    session.delete(row)
    session.commit()
    return {"message": "Compatibility deleted"}
