from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class BannerCreate(BaseModel):
    slug: str
    title: str
    content: str
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    is_active: bool = False
    is_dismissible: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class BannerEdit(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_dismissible: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class BannerPublic(BaseModel):
    id: str
    slug: str
    title: str
    content: str
    image_url: Optional[str]
    link_url: Optional[str]
    is_dismissible: bool