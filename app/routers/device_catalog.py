from fastapi import APIRouter, Depends, Query
from sqlmodel import select, or_
from sqlmodel.sql.expression import desc
from typing import Optional
from app.database import get_session
from app.models.device_catalog import Chipset, DeviceBrand, IssueCategory, Tool, ToolCapability, DeviceCompatibility
from app.schemas.device_catalog import (
    DeviceScanRequest,
    DeviceScanResponse,
    RecommendationRequest,
    RecommendationResponse,
    IssueOut,
    ChipsetOut,
    DeviceBrandOut,
    ToolRecommendation,
)
from app.models.item import Item

router = APIRouter()


@router.get("/device/chipsets")
def list_chipsets(session=Depends(get_session)):
    rows = session.exec(select(Chipset).order_by(Chipset.key)).all()
    return [ChipsetOut(key=r.key, label=r.label) for r in rows]


@router.get("/device/brands")
def list_brands(session=Depends(get_session)):
    rows = session.exec(select(DeviceBrand).where(DeviceBrand.is_active == True).order_by(DeviceBrand.name)).all()
    return [DeviceBrandOut(slug=r.slug, name=r.name) for r in rows]


@router.get("/device/issues")
def list_issues(session=Depends(get_session)):
    rows = session.exec(select(IssueCategory).where(IssueCategory.is_active == True).order_by(IssueCategory.label)).all()
    return [IssueOut(slug=r.slug, label=r.label) for r in rows]


@router.post("/device/scan", response_model=DeviceScanResponse)
def scan_device(payload: DeviceScanRequest, session=Depends(get_session)):
    model = (payload.model_number or "").strip()
    brand = (payload.brand or "").strip()
    chipset = (payload.chipset or "").strip()

    detected_brand = brand or None
    detected_chipset = chipset or None

    if not detected_brand or not detected_chipset:
        lowered = model.lower()
        if lowered.startswith("sm-") or lowered.startswith("samsung") or "galaxy" in lowered:
            detected_brand = detected_brand or "samsung"
            detected_chipset = detected_chipset or "exynos"
        elif "iphone" in lowered or lowered.startswith("a") or lowered.startswith("mn") or lowered.startswith("my"):
            detected_brand = detected_brand or "apple"
            detected_chipset = detected_chipset or "apple"
        elif "pixel" in lowered or "google" in lowered:
            detected_brand = detected_brand or "google"
            detected_chipset = detected_chipset or "tensor"
        elif "mt" in lowered or "mediatek" in lowered or "dimensity" in lowered:
            detected_brand = detected_brand or "generic"
            detected_chipset = detected_chipset or "mediatek"
        elif lowered.startswith("sd") or "snapdragon" in lowered:
            detected_brand = detected_brand or "generic"
            detected_chipset = detected_chipset or "snapdragon"

    issues = [
        IssueOut(slug="frp", label="FRP Lock"),
        IssueOut(slug="network_lock", label="Network Lock"),
        IssueOut(slug="mdm", label="MDM Lock"),
        IssueOut(slug="icloud", label="iCloud Lock"),
        IssueOut(slug="password", label="Password / Pattern Lock"),
        IssueOut(slug="corrupt_os", label="Corrupt OS"),
    ]

    return DeviceScanResponse(
        detected_brand=detected_brand,
        detected_model=payload.model_number,
        detected_chipset=detected_chipset,
        firmware=payload.firmware,
        issues=issues,
    )


@router.post("/device/recommend", response_model=RecommendationResponse)
def recommend_tools(payload: RecommendationRequest, session=Depends(get_session)):
    q_caps = select(Tool).join(ToolCapability, ToolCapability.tool_id == Tool.id).where(
        ToolCapability.issue_slug == payload.issue_slug,
        Tool.is_active == True,
        ToolCapability.is_active == True,
    )

    if payload.brand_slug:
        q_caps = q_caps.join(DeviceCompatibility, DeviceCompatibility.tool_id == Tool.id).where(
            or_(
                DeviceCompatibility.brand_slug == payload.brand_slug,
                DeviceCompatibility.brand_slug == None,  # noqa: E711
            ),
            DeviceCompatibility.is_active == True,
        )

    if payload.chipset_key:
        q_caps = q_caps.where(
            or_(
                DeviceCompatibility.chipset_key == payload.chipset_key,
                DeviceCompatibility.chipset_key == None,  # noqa: E711
            )
        )

    tools = session.exec(q_caps.distinct().order_by(desc(Tool.id))).all()

    issue = session.exec(select(IssueCategory).where(IssueCategory.slug == payload.issue_slug)).first()

    tool_out: list[ToolRecommendation] = []
    for t in tools:
        caps = session.exec(
            select(ToolCapability).where(ToolCapability.tool_id == t.id, ToolCapability.issue_slug == payload.issue_slug)
        ).all()
        notes = caps[0].notes if caps else None
        tool_out.append(
            ToolRecommendation(
                slug=t.slug,
                name=t.name,
                description=t.description,
                website_url=t.website_url,
                reason=notes,
            )
        )

    return RecommendationResponse(
        issue=IssueOut(slug=issue.slug, label=issue.label) if issue else IssueOut(slug=payload.issue_slug, label=payload.issue_slug),
        tools=tool_out,
    )


@router.get("/tools")
def list_tools(
    issue: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    chipset: Optional[str] = Query(None),
    session=Depends(get_session),
):
    q = select(Tool).where(Tool.is_active == True)

    if issue:
        q = q.join(ToolCapability, ToolCapability.tool_id == Tool.id).where(ToolCapability.issue_slug == issue)

    if brand:
        q = q.join(DeviceCompatibility, DeviceCompatibility.tool_id == Tool.id).where(
            or_(
                DeviceCompatibility.brand_slug == brand,
                DeviceCompatibility.brand_slug == None,  # noqa: E711
            ),
            DeviceCompatibility.is_active == True,
        )

    if chipset:
        q = q.where(
            or_(
                DeviceCompatibility.chipset_key == chipset,
                DeviceCompatibility.chipset_key == None,  # noqa: E711
            )
        )

    rows = session.exec(q.distinct().order_by(Tool.name)).all()
    return [{"id": str(r.id), "slug": r.slug, "name": r.name, "website_url": r.website_url} for r in rows]
