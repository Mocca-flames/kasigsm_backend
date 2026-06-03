from typing import Optional
from pydantic import BaseModel
from decimal import Decimal


class PaymentInitiate(BaseModel):
    order_id: str
    return_url: Optional[str] = None


class PaymentVerify(BaseModel):
    reference: str