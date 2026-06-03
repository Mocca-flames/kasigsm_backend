import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, Enum as SAEnum, DateTime


class TechnicianStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Technician(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, unique=True)
    status: TechnicianStatus = Field(
        sa_column=Column(SAEnum(TechnicianStatus), nullable=False, default=TechnicianStatus.PENDING)
    )
    specialization: Optional[str] = Field(sa_type=String, nullable=True)
    reviewed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True, default=None)
    )
    reviewed_by: Optional[uuid.UUID] = Field(foreign_key="user.id", default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
