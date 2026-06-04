import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel, Column, String, Enum as SAEnum, DateTime, Text


class WalletStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class WalletTransactionType(str, PyEnum):
    TOPUP = "TOPUP"
    DEBIT = "DEBIT"
    ADMIN_CREDIT = "ADMIN_CREDIT"
    REFUND = "REFUND"


class WalletTopUpStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Wallet(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, unique=True, index=True)
    balance: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    status: WalletStatus = Field(
        sa_column=Column(SAEnum(WalletStatus), nullable=False, default=WalletStatus.ACTIVE)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    )

    user: "User" = Relationship()
    transactions: list["WalletTransaction"] = Relationship(back_populates="wallet")
    top_ups: list["WalletTopUp"] = Relationship(back_populates="wallet")


class WalletTransaction(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id", nullable=False, index=True)
    amount: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    type: WalletTransactionType = Field(
        sa_column=Column(SAEnum(WalletTransactionType), nullable=False)
    )
    reference: Optional[str] = Field(sa_type=String, default=None)
    description: Optional[str] = Field(sa_type=Text, default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )

    wallet: Wallet = Relationship(back_populates="transactions")


class WalletTopUp(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id", nullable=False, index=True)
    amount: Decimal = Field(max_digits=12, decimal_places=2, nullable=False)
    reference: Optional[str] = Field(sa_type=String, default=None)
    status: WalletTopUpStatus = Field(
        sa_column=Column(SAEnum(WalletTopUpStatus), nullable=False, default=WalletTopUpStatus.PENDING)
    )
    proof_note: Optional[str] = Field(sa_type=Text, default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )
    reviewed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), default=None)
    )

    wallet: Wallet = Relationship(back_populates="top_ups")
