from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum


class ItemType(str, Enum):
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"


class ProviderListingPublic(BaseModel):
    provider: str
    cost_price: Decimal
    currency: str
    is_preferred: bool


class ItemPublic(BaseModel):
    id: str
    uid: Optional[str] = None
    slug: str
    title: str
    description: Optional[str]
    item_type: ItemType
    category: str
    thumbnail: Optional[str] = None
    media_url: Optional[str] = None
    price_final: Decimal
    currency: str
    delivery_time: Optional[str]
    stock: Optional[int]
    meta: Optional[dict] = None


class ItemsPageResponse(BaseModel):
    items: List[ItemPublic]
    total: int
    page: int
    limit: int


class ItemDetail(BaseModel):
    id: str
    uid: Optional[str] = None
    slug: str
    title: str
    description: Optional[str]
    item_type: ItemType
    category: str
    thumbnail: Optional[str] = None
    media_url: Optional[str] = None
    price_final: Decimal
    currency: str
    delivery_time: Optional[str]
    stock: Optional[int]
    is_visible: bool
    low_stock: bool = False
    provider_listings: list[ProviderListingPublic] = []
    effective_markup: Optional[Decimal] = None
    markup_source: Optional[Literal["item", "provider_category"]] = None
    meta: Optional[dict] = None


class ItemCreate(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    item_type: ItemType
    category: str
    thumbnail: Optional[str] = None
    price_markup: Decimal = Decimal("0")
    currency: str = "ZAR"
    delivery_time: Optional[str] = None
    stock: Optional[int] = None


class ItemEdit(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    thumbnail: Optional[str] = None
    price_markup: Optional[Decimal] = None
    currency: Optional[str] = None
    delivery_time: Optional[str] = None
    stock: Optional[int] = None
    is_visible: Optional[bool] = None
    uid: Optional[str] = None


class OTPVerify(BaseModel):
    email: str
    code: str = Field(..., alias="otp")


class CategoryMarkup(BaseModel):
    category: str
    price_markup: Decimal


class CategoryMarkupUpdate(BaseModel):
    category: str
    percentage: Decimal


class BulkMarkupResponse(BaseModel):
    message: str
    category: str
    markup_type: Literal["flat", "percentage"]
    items_updated: int
    updated_items: list[dict]


class CategoryMarkupDetail(BaseModel):
    id: str
    category: str
    price_markup: Decimal


class UserRegister(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPassword(BaseModel):
    email: str


class ResetPassword(BaseModel):
    token: str
    new_password: str


class ForgotPassword(BaseModel):
    email: str


class ResetPassword(BaseModel):
    token: str
    new_password: str