from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal


class OrderItemCreate(BaseModel):
    item_id: str
    quantity: int


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class CredentialPublic(BaseModel):
    id: str
    item_id: str
    payload: str


class OrderItemPublic(BaseModel):
    id: str
    item_id: str
    quantity: int
    unit_price: Decimal
    credentials: Optional[List[CredentialPublic]] = None


class OrderPublic(BaseModel):
    id: str
    status: str
    total_amount: Decimal
    currency: str
    created_at: str
    items: list[OrderItemPublic]