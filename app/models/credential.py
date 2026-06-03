import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel, Column, DateTime, Text


class Credential(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    item_id: uuid.UUID = Field(foreign_key="item.id", nullable=False)
    payload: str = Field(sa_column=Column(Text, nullable=False))
    is_used: bool = Field(default=False)
    order_item_id: Optional[uuid.UUID] = Field(foreign_key="orderitem.id", default=None)
    assigned_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), default=None)
    )

    item: "Item" = Relationship(back_populates="credentials")
    order_item: Optional["OrderItem"] = Relationship(back_populates="credential")