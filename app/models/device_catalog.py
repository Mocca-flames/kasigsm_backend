import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from sqlmodel import Field, SQLModel, Column, String, Text, Boolean, DateTime, Index, ForeignKey, Relationship
from sqlalchemy.dialects.postgresql import UUID


class IssueCategory(SQLModel, table=True):
    __tablename__ = "issue_category"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    label: str = Field(sa_type=String, nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


class Chipset(SQLModel, table=True):
    __tablename__ = "chipset"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    label: str = Field(sa_type=String, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


class DeviceBrand(SQLModel, table=True):
    __tablename__ = "device_brand"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    name: str = Field(sa_type=String, nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


class Tool(SQLModel, table=True):
    __tablename__ = "device_tool"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    name: str = Field(sa_type=String, nullable=False)
    description: Optional[str] = Field(sa_column=Column(Text), default=None)
    website_url: Optional[str] = Field(sa_type=String, default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


class ToolCapability(SQLModel, table=True):
    __tablename__ = "tool_capability"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="device_tool.id", nullable=False, index=True)
    issue_slug: str = Field(sa_type=String, nullable=False, index=True)
    platform: Optional[str] = Field(sa_type=String, default=None)
    notes: Optional[str] = Field(sa_type=String, default=None)
    is_active: bool = Field(default=True)

    __table_args__ = (
        Index("uq_tool_issue", "tool_id", "issue_slug", unique=True),
    )


class DeviceCompatibility(SQLModel, table=True):
    __tablename__ = "device_compatibility"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tool_id: uuid.UUID = Field(foreign_key="device_tool.id", nullable=False, index=True)
    brand_slug: Optional[str] = Field(sa_type=String, default=None, index=True)
    chipset_key: Optional[str] = Field(sa_type=String, default=None, index=True)
    notes: Optional[str] = Field(sa_type=String, default=None)
    is_active: bool = Field(default=True)

    __table_args__ = (
        Index("uq_tool_brand_chipset", "tool_id", "brand_slug", "chipset_key", unique=True),
    )
