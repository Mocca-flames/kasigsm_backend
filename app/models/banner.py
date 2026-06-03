import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Column, String, Text, Boolean, DateTime, SQLModel


class Banner(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    title: str = Field(sa_type=String, nullable=False)
    content: str = Field(sa_type=Text, nullable=False)
    image_url: Optional[str] = Field(sa_type=String, default=None)
    link_url: Optional[str] = Field(sa_type=String, default=None)
    is_active: bool = Field(default=False)
    is_dismissible: bool = Field(default=True)
    starts_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    ends_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    )