from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, validator


class PromoCodeValidateRequest(BaseModel):
    code: str
    order_amount: Decimal


class PromoCodeValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    message: Optional[str] = None


class PromoCodeApplyRequest(BaseModel):
    code: str


class PromoCodeApplyResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    message: Optional[str] = None


class PromoCodeCreate(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_categories: Optional[str] = None
    applicable_items: Optional[str] = None
    is_active: bool = True

    @validator("discount_type")
    def validate_discount_type(cls, v):
        if v not in ("PERCENTAGE", "FIXED_AMOUNT"):
            raise ValueError("discount_type must be PERCENTAGE or FIXED_AMOUNT")
        return v

    @validator("discount_value")
    def validate_discount_value(cls, v, values):
        if "discount_type" in values:
            if values["discount_type"] == "PERCENTAGE" and (v < 0 or v > 100):
                raise ValueError("Percentage discount must be between 0 and 100")
            if values["discount_type"] == "FIXED_AMOUNT" and v < 0:
                raise ValueError("Fixed amount discount must be >= 0")
        return v

    @validator("code")
    def validate_code(cls, v):
        code = v.strip().upper()
        if not code or len(code) < 3:
            raise ValueError("Promo code must be at least 3 characters")
        if not code.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Promo code must contain only letters, numbers, hyphens, and underscores")
        return code


class PromoCodeEdit(BaseModel):
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_categories: Optional[str] = None
    applicable_items: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("discount_type")
    def validate_discount_type(cls, v):
        if v is not None and v not in ("PERCENTAGE", "FIXED_AMOUNT"):
            raise ValueError("discount_type must be PERCENTAGE or FIXED_AMOUNT")
        return v


class PromoCodePublic(BaseModel):
    id: str
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool
    current_uses: int
    created_at: Optional[datetime] = None


class PromoCodeUsagePublic(BaseModel):
    id: str
    promo_code_id: str
    user_id: Optional[str] = None
    order_id: Optional[str] = None
    discount_amount: Decimal
    order_amount: Decimal
    used_at: Optional[datetime] = None
