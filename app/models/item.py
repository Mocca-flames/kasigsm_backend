import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel, Column, JSON, String, Enum as SAEnum, DateTime, Text, Index


class ItemType(str, PyEnum):
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"


class Item(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    uid: str = Field(sa_type=String, unique=True, index=True, default=None)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    title: str = Field(sa_type=String, nullable=False)
    description: Optional[str] = Field(sa_type=Text, default=None)
    item_type: ItemType = Field(sa_column=Column(SAEnum(ItemType), nullable=False))
    category: str = Field(sa_type=String, nullable=False)
    thumbnail: Optional[str] = Field(sa_type=String, default=None)
    price_markup: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: str = Field(default="ZAR", sa_type=String(3))
    delivery_time: Optional[str] = Field(sa_type=String, default=None)
    stock: Optional[int] = Field(default=None)
    is_visible: bool = Field(default=True)
    is_archived: bool = Field(default=False)
    meta: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    )

    __table_args__ = (
        Index("ix_item_visibility_category", "is_visible", "is_archived", "item_type", "category"),
    )

    provider_listings: list["ProviderListing"] = Relationship(back_populates="item")
    order_items: list["OrderItem"] = Relationship(back_populates="item")
    credentials: list["Credential"] = Relationship(back_populates="item")


class Provider(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(sa_type=String, unique=True, nullable=False)
    base_url: Optional[str] = Field(sa_type=String, default=None)
    logo_url: Optional[str] = Field(sa_type=String, default=None)
    notes: Optional[str] = Field(sa_type=Text, default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )

    listings: list["ProviderListing"] = Relationship(back_populates="provider")


class ProviderListing(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    item_id: uuid.UUID = Field(foreign_key="item.id", nullable=False)
    provider_id: uuid.UUID = Field(foreign_key="provider.id", nullable=False)
    external_id: Optional[str] = Field(sa_type=String, default=None)
    cost_price: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    is_preferred: bool = Field(default=False)
    is_active: bool = Field(default=True)

    __table_args__ = (
        Index("ix_providerlisting_item", "item_id", "is_active"),
        Index("ix_providerlisting_provider", "provider_id", "is_active"),
    )

    item: Item = Relationship(back_populates="provider_listings")
    provider: Provider = Relationship(back_populates="listings")