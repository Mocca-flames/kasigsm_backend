import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, Text, Boolean, DateTime, Index


class Category(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    description: Optional[str] = Field(sa_column=Column(Text), default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


class ProviderCategoryMarkup(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    provider_id: uuid.UUID = Field(nullable=False, index=True)
    category: str = Field(sa_type=String, nullable=False, index=True)
    price_markup: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)

    __table_args__ = (
        Index("uq_provider_category", "provider_id", "category", unique=True),
    )
