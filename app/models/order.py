import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel, Column, String, Enum as SAEnum, DateTime


class OrderStatus(str, PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class Order(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    status: OrderStatus = Field(
        sa_column=Column(SAEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    )
    payment_ref: Optional[str] = Field(sa_type=String, default=None)
    payment_gateway: Optional[str] = Field(sa_type=String, default=None)
    total_amount: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    currency: str = Field(default="ZAR", sa_type=String(3))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    )

    items: list["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="order.id", nullable=False)
    item_id: uuid.UUID = Field(foreign_key="item.id", nullable=False)
    quantity: int = Field(nullable=False)
    unit_price: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)

    order: Order = Relationship(back_populates="items")
    item: "Item" = Relationship(back_populates="order_items")
    credential: Optional["Credential"] = Relationship(back_populates="order_item")