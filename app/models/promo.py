import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel, Column, String, Enum as SAEnum, DateTime


class DiscountType(str, PyEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"


class PromoCode(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(sa_type=String(50), unique=True, nullable=False, index=True)
    description: Optional[str] = Field(sa_type=String(255), default=None)
    discount_type: DiscountType = Field(
        sa_column=Column(SAEnum(DiscountType), nullable=False)
    )
    discount_value: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    min_order_amount: Optional[Decimal] = Field(max_digits=12, decimal_places=2, default=None)
    max_discount_amount: Optional[Decimal] = Field(max_digits=12, decimal_places=2, default=None)
    max_uses: Optional[int] = Field(default=None)
    max_uses_per_user: Optional[int] = Field(default=None)
    valid_from: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)), default=None
    )
    valid_until: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)), default=None
    )
    applicable_categories: Optional[str] = Field(sa_type=String, default=None)
    applicable_items: Optional[str] = Field(sa_type=String, default=None)
    is_active: bool = Field(default=True, nullable=False)
    current_uses: int = Field(default=0, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    )

    usages: list["PromoCodeUsage"] = Relationship(back_populates="promo_code")


class PromoCodeUsage(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    promo_code_id: uuid.UUID = Field(foreign_key="promocode.id", nullable=False)
    user_id: Optional[uuid.UUID] = Field(foreign_key="user.id", default=None)
    order_id: Optional[uuid.UUID] = Field(foreign_key="order.id", default=None)
    discount_amount: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    order_amount: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    used_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )

    promo_code: PromoCode = Relationship(back_populates="usages")
