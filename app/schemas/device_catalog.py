from pydantic import BaseModel
from typing import Optional, List


class IssueOut(BaseModel):
    slug: str
    label: str


class ChipsetOut(BaseModel):
    key: str
    label: str


class DeviceBrandOut(BaseModel):
    slug: str
    name: str


class DeviceScanRequest(BaseModel):
    model_number: Optional[str] = None
    brand: Optional[str] = None
    chipset: Optional[str] = None
    firmware: Optional[str] = None
    imei: Optional[str] = None


class DeviceScanResponse(BaseModel):
    detected_brand: Optional[str]
    detected_model: Optional[str]
    detected_chipset: Optional[str]
    firmware: Optional[str]
    issues: list[IssueOut]


class RecommendationRequest(BaseModel):
    issue_slug: str
    brand_slug: Optional[str] = None
    chipset_key: Optional[str] = None


class ToolRecommendation(BaseModel):
    slug: str
    name: str
    description: Optional[str]
    website_url: Optional[str]
    reason: Optional[str]
    rent_slug: Optional[str] = None
    rent_price_final: Optional[float] = None
    rent_currency: Optional[str] = None
    full_slug: Optional[str] = None
    full_price_final: Optional[float] = None
    full_currency: Optional[str] = None


class RecommendationResponse(BaseModel):
    issue: IssueOut
    tools: list[ToolRecommendation]


class ScanServiceRequest(BaseModel):
    issues: list[str]
    brand_slug: Optional[str] = None
    chipset_key: Optional[str] = None
    top: int = 3


class ScanServiceResponse(BaseModel):
    services: list[ToolRecommendation]
