from typing import Optional
from pydantic import BaseModel
from decimal import Decimal


class WalletPublic(BaseModel):
    id: str
    balance: Decimal
    status: str
    client_ref: Optional[str] = None
    is_low_balance: bool = False


class WalletTopUpRequest(BaseModel):
    amount: Decimal
    reference: Optional[str] = None
    proof_note: Optional[str] = None


class WalletTopUpReview(BaseModel):
    approved: bool
    note: Optional[str] = None


class WalletAdminCredit(BaseModel):
    amount: Decimal
    description: Optional[str] = None


class WalletPayRequest(BaseModel):
    order_id: str
