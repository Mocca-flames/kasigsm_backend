from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from sqlmodel import select, func
import uuid

from app.database import get_session
from app.models.promo import PromoCode, PromoCodeUsage, DiscountType
from app.schemas.promo import (
    PromoCodeCreate,
    PromoCodeEdit,
    PromoCodePublic,
    PromoCodeUsagePublic,
    PromoCodeValidateRequest,
    PromoCodeValidateResponse,
    PromoCodeApplyRequest,
    PromoCodeApplyResponse,
)
from app.services.promo import validate_promo_code, calculate_discount, apply_promo_code, PromoValidationError
from app.utils.security import require_admin, get_current_user

router = APIRouter()


@router.get("/promo-codes", response_model=List[PromoCodePublic])
def list_promo_codes(
    active_only: bool = Query(default=False),
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    stmt = select(PromoCode)
    if active_only:
        stmt = stmt.where(PromoCode.is_active == True)
    promo_codes = session.exec(stmt.order_by(PromoCode.created_at.desc())).all()
    return [_promo_to_public(p) for p in promo_codes]


@router.get("/promo-codes/{promo_id}", response_model=PromoCodePublic)
def get_promo_code(
    promo_id: str,
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    promo = session.exec(select(PromoCode).where(PromoCode.id == uuid.UUID(promo_id))).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return _promo_to_public(promo)


@router.post("/promo-codes", response_model=PromoCodePublic)
def create_promo_code(
    promo_in: PromoCodeCreate,
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    existing = session.exec(select(PromoCode).where(PromoCode.code == promo_in.code)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")

    promo = PromoCode(**promo_in.dict())
    session.add(promo)
    session.commit()
    session.refresh(promo)
    return _promo_to_public(promo)


@router.patch("/promo-codes/{promo_id}", response_model=PromoCodePublic)
def update_promo_code(
    promo_id: str,
    promo_in: PromoCodeEdit,
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    promo = session.exec(select(PromoCode).where(PromoCode.id == uuid.UUID(promo_id))).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    update_data = promo_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promo, field, value)

    session.add(promo)
    session.commit()
    session.refresh(promo)
    return _promo_to_public(promo)


@router.delete("/promo-codes/{promo_id}")
def delete_promo_code(
    promo_id: str,
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    promo = session.exec(select(PromoCode).where(PromoCode.id == uuid.UUID(promo_id))).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    session.delete(promo)
    session.commit()
    return {"message": "Promo code deleted"}


@router.get("/promo-codes/{promo_id}/usages", response_model=List[PromoCodeUsagePublic])
def list_promo_usages(
    promo_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session = Depends(get_session),
    admin = Depends(require_admin),
):
    promo = session.exec(select(PromoCode).where(PromoCode.id == uuid.UUID(promo_id))).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    stmt = (
        select(PromoCodeUsage)
        .where(PromoCodeUsage.promo_code_id == promo.id)
        .order_by(PromoCodeUsage.used_at.desc())
        .offset(offset)
        .limit(limit)
    )
    usages = session.exec(stmt).all()
    return [_usage_to_public(u) for u in usages]


@router.post("/promo-codes/validate", response_model=PromoCodeValidateResponse)
def validate_promo_code_endpoint(
    req: PromoCodeValidateRequest,
    user = Depends(get_current_user),
    session = Depends(get_session),
):
    user_id = str(user.id) if user else None
    try:
        result = validate_promo_code(
            code=req.code,
            user_id=user_id,
            order_items=[],
            session=session,
            order_amount=req.order_amount,
        )
        promo = result["promo"]
        return PromoCodeValidateResponse(
            valid=True,
            code=promo.code,
            discount_type=promo.discount_type.value,
            discount_value=promo.discount_value,
            discount_amount=result["discount_amount"],
        )
    except PromoValidationError as e:
        return PromoCodeValidateResponse(
            valid=False,
            code=req.code.strip().upper(),
            discount_type="",
            discount_value=Decimal("0"),
            discount_amount=Decimal("0"),
            message=str(e),
        )


@router.post("/promo-codes/apply", response_model=PromoCodeApplyResponse)
def apply_promo_code_endpoint(
    req: PromoCodeApplyRequest,
    user = Depends(get_current_user),
    session = Depends(get_session),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    code_upper = req.code.strip().upper()

    try:
        result = validate_promo_code(
            code=code_upper,
            user_id=str(user.id),
            order_items=[],
            session=session,
        )
        promo = result["promo"]
        discount_amount = result["discount_amount"]
        final_amount = result["order_amount"] - discount_amount
        if final_amount < 0:
            final_amount = Decimal("0")

        return PromoCodeApplyResponse(
            valid=True,
            code=promo.code,
            discount_type=promo.discount_type.value,
            discount_value=promo.discount_value,
            discount_amount=discount_amount,
            final_amount=final_amount,
        )
    except PromoValidationError as e:
        return PromoCodeApplyResponse(
            valid=False,
            code=code_upper,
            discount_type="",
            discount_value=Decimal("0"),
            discount_amount=Decimal("0"),
            final_amount=Decimal("0"),
            message=str(e),
        )


def _promo_to_public(promo: PromoCode) -> PromoCodePublic:
    return PromoCodePublic(
        id=str(promo.id),
        code=promo.code,
        description=promo.description,
        discount_type=promo.discount_type.value,
        discount_value=promo.discount_value,
        min_order_amount=promo.min_order_amount,
        max_discount_amount=promo.max_discount_amount,
        max_uses=promo.max_uses,
        max_uses_per_user=promo.max_uses_per_user,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        is_active=promo.is_active,
        current_uses=promo.current_uses,
        created_at=promo.created_at,
    )


def _usage_to_public(usage: PromoCodeUsage) -> PromoCodeUsagePublic:
    return PromoCodeUsagePublic(
        id=str(usage.id),
        promo_code_id=str(usage.promo_code_id),
        user_id=str(usage.user_id) if usage.user_id else None,
        order_id=str(usage.order_id) if usage.order_id else None,
        discount_amount=usage.discount_amount,
        order_amount=usage.order_amount,
        used_at=usage.used_at,
    )
