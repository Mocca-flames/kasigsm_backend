from typing import Optional, List
from pydantic import BaseModel


class SearchValidateRequest(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    service_type: Optional[str] = None
    location: Optional[str] = None
    item_ids: Optional[List[str]] = None


class SearchValidateResponse(BaseModel):
    valid: bool
    valid_query: bool
    valid_category: bool
    valid_service_type: bool
    valid_location: bool
    total_matches: int
    accessible_matches: int
    items: List["ItemPublic"]
    validation_messages: List[str] = []
