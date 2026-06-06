import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, Enum as SAEnum, DateTime


class UserRole(str, PyEnum):
    CLIENT = "CLIENT"
    ADMIN = "ADMIN"
    TECHNICIAN = "TECHNICIAN"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_type=String, unique=True, nullable=False, index=True)
    password_hash: str = Field(sa_type=String, nullable=False)
    role: UserRole = Field(
        sa_column=Column(SAEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    )
    client_ref: Optional[str] = Field(sa_type=String(6), default=None, unique=True, index=True)
    is_active: bool = Field(default=True)
    password_reset_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )