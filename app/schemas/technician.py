from typing import Optional
from pydantic import BaseModel


class TechnicianRequest(BaseModel):
    specialization: Optional[str] = None


class TechnicianResponse(BaseModel):
    id: str
    user_id: str
    email: str
    role: str
    status: str
    specialization: Optional[str] = None
    created_at: Optional[str] = None


class TechnicianReview(BaseModel):
    action: str
