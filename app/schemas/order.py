from typing import Optional, List, Dict
from pydantic import BaseModel
from decimal import Decimal


class CredentialAssignment(BaseModel):
    order_item_id: str
    payload: str


class OrderFulfill(BaseModel):
    credentials: List[CredentialAssignment]


class OrderItemCreate(BaseModel):
    item_id: str
    quantity: int


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    promo_code: Optional[str] = None


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
    subtotal: Decimal
    discount_code: Optional[str] = None
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    created_at: str
    items: list[OrderItemPublic]


class StatsSummaryResponse(BaseModel):
    period_days: int
    total_orders: int
    orders_by_status: Dict[str, int]
    total_revenue: Decimal
    total_clients: int
    total_items: int
    low_stock_items: int
    fulfilled_orders: int
    pending_fulfillment: int
    refunded_orders: int
