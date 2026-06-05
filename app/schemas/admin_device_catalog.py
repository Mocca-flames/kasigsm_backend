from typing import Optional
from pydantic import BaseModel


class ChipsetCreate(BaseModel):
    key: str
    label: str


class ChipsetEdit(BaseModel):
    key: Optional[str] = None
    label: Optional[str] = None


class DeviceBrandCreate(BaseModel):
    slug: str
    name: str
    is_active: bool = True


class DeviceBrandEdit(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class IssueCategoryCreate(BaseModel):
    slug: str
    label: str
    is_active: bool = True


class IssueCategoryEdit(BaseModel):
    slug: Optional[str] = None
    label: Optional[str] = None
    is_active: Optional[bool] = None


class ToolCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    website_url: Optional[str] = None
    is_active: bool = True


class ToolEdit(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    is_active: Optional[bool] = None


class ToolCapabilityCreate(BaseModel):
    tool_id: str
    issue_slug: str
    platform: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ToolCapabilityEdit(BaseModel):
    tool_id: Optional[str] = None
    issue_slug: Optional[str] = None
    platform: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceCompatibilityCreate(BaseModel):
    tool_id: str
    brand_slug: Optional[str] = None
    chipset_key: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class DeviceCompatibilityEdit(BaseModel):
    tool_id: Optional[str] = None
    brand_slug: Optional[str] = None
    chipset_key: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
