from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlmodel import select, func
import json

from app.database import get_session
from app.models.promo import PromoCode, PromoCodeUsage, DiscountType
from app.models.item import Item
from app.models.user import User
from app.models.order import Order


class PromoValidationError(Exception):
    pass


def _get_session():
    from app.database import engine
    from sqlmodel import Session
    return Session(engine)


def validate_promo_code(code: str, user_id: Optional[str], order_items: List[dict], session=None, order_amount: Optional[Decimal] = None) -> dict:
    if session is None:
        session = _get_session()

    code_upper = code.strip().upper()
    promo = session.exec(select(PromoCode).where(PromoCode.code == code_upper)).first()

    if not promo:
        raise PromoValidationError("Promo code not found")

    if not promo.is_active:
        raise PromoValidationError("This promo code is not active")

    now = datetime.now(timezone.utc)

    if promo.valid_from and now < promo.valid_from:
        raise PromoValidationError("This promo code is not yet valid")

    if promo.valid_until and now > promo.valid_until:
        raise PromoValidationError("This promo code has expired")

    if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
        raise PromoValidationError("This promo code has reached its maximum number of uses")

    if user_id:
        if promo.max_uses_per_user is not None:
            user_uses = session.exec(
                select(func.count(PromoCodeUsage.id)).where(
                    PromoCodeUsage.promo_code_id == promo.id,
                    PromoCodeUsage.user_id == user_id,
                )
            ).first() or 0
            if user_uses >= promo.max_uses_per_user:
                raise PromoValidationError("You have already used this promo code the maximum number of times")

    if order_amount is None:
        order_amount = Decimal("0")
        for oi in order_items:
            item = session.exec(select(Item).where(Item.id == oi.get("item_id"))).first()
            if not item:
                continue
            from app.services.pricing import get_price_final
            price = get_price_final(item, session)
            order_amount += price * oi.get("quantity", 1)

    if promo.min_order_amount is not None and order_amount < promo.min_order_amount:
        raise PromoValidationError(f"Minimum order amount is {promo.min_order_amount} ZAR")

    if promo.applicable_categories:
        applicable = [c.strip() for c in promo.applicable_categories.split(",") if c.strip()]
        if applicable:
            eligible = False
            for oi in order_items:
                item = session.exec(select(Item).where(Item.id == oi.get("item_id"))).first()
                if item and item.category in applicable:
                    eligible = True
                    break
            if not eligible:
                raise PromoValidationError("This promo code is not applicable to items in your cart")

    if promo.applicable_items:
        applicable_ids = [i.strip() for i in promo.applicable_items.split(",") if i.strip()]
        if applicable_ids:
            eligible = False
            for oi in order_items:
                if str(oi.get("item_id")) in applicable_ids:
                    eligible = True
                    break
            if not eligible:
                raise PromoValidationError("This promo code is not applicable to items in your cart")

    discount_amount = calculate_discount(promo, order_amount)

    return {
        "promo": promo,
        "order_amount": order_amount,
        "discount_amount": discount_amount,
    }


def calculate_discount(promo: PromoCode, order_amount: Decimal) -> Decimal:
    if promo.discount_type == DiscountType.PERCENTAGE:
        discount = order_amount * (promo.discount_value / Decimal("100"))
        if promo.max_discount_amount is not None:
            discount = min(discount, promo.max_discount_amount)
        return discount
    else:
        return min(promo.discount_value, order_amount)


def apply_promo_code(code: str, user_id: Optional[str], order_id: str, order_amount: Decimal, discount_amount: Decimal, session=None):
    if session is None:
        session = _get_session()

    result = validate_promo_code(code, user_id, [], session=session)

    promo = result["promo"]

    usage = PromoCodeUsage(
        promo_code_id=promo.id,
        user_id=user_id,
        order_id=order_id,
        discount_amount=discount_amount,
        order_amount=order_amount,
    )
    session.add(usage)

    promo.current_uses += 1
    session.add(promo)
    session.commit()
    session.refresh(usage)

    return usage
