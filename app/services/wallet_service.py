from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import select

from app.config import settings
from app.models.wallet import Wallet, WalletTransaction, WalletTopUp, WalletStatus, WalletTransactionType, WalletTopUpStatus
from app.utils.email import send_wallet_topup_approved_email, send_wallet_low_balance_email


def _now():
    return datetime.now(timezone.utc)


def approve_top_up(session, top_up: WalletTopUp, admin_note: str | None = None):
    wallet = session.exec(select(Wallet).where(Wallet.id == top_up.wallet_id)).first()
    if not wallet:
        raise ValueError("Wallet not found")

    if top_up.status != WalletTopUpStatus.PENDING:
        raise ValueError("Top-up is not pending")

    wallet.balance = (wallet.balance or Decimal("0")) + top_up.amount
    if wallet.status == WalletStatus.DISABLED:
        wallet.status = WalletStatus.ACTIVE

    if top_up.balance is None:
        top_up.balance = wallet.balance

    top_up.status = WalletTopUpStatus.APPROVED
    top_up.reviewed_at = _now()
    session.add(top_up)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=top_up.amount,
        type=WalletTransactionType.TOPUP,
        reference=top_up.reference,
        description=admin_note,
    )
    session.add(tx)

    session.commit()
    session.refresh(top_up)
    session.refresh(wallet)

    from app.models.user import User
    if wallet.user_id:
        user = session.exec(select(User).where(User.id == wallet.user_id)).first()
        if user and user.email:
            send_wallet_topup_approved_email(user.email, float(top_up.amount), float(wallet.balance), top_up.reference)

    if wallet.balance <= settings.wallet_low_balance_threshold:
        if user and user.email:
            send_wallet_low_balance_email(user.email, float(wallet.balance))

    return wallet, top_up, tx


def reject_top_up(session, top_up: WalletTopUp, admin_note: str | None = None):
    if top_up.status != WalletTopUpStatus.PENDING:
        raise ValueError("Top-up is not pending")

    top_up.status = WalletTopUpStatus.REJECTED
    top_up.reviewed_at = _now()
    session.add(top_up)
    session.commit()
    session.refresh(top_up)
    return top_up


def admin_credit(session, wallet: Wallet, amount: Decimal, description: str | None = None):
    if amount <= 0:
        raise ValueError("Amount must be positive")

    wallet.balance = (wallet.balance or Decimal("0")) + amount
    if wallet.status == WalletStatus.DISABLED:
        wallet.status = WalletStatus.ACTIVE

    session.add(wallet)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=amount,
        type=WalletTransactionType.ADMIN_CREDIT,
        description=description,
    )
    session.add(tx)
    session.commit()
    session.refresh(wallet)
    session.refresh(tx)
    return wallet, tx


def debit_for_order(session, wallet: Wallet, amount: Decimal, order_id):
    if not amount or amount <= 0:
        raise ValueError("Invalid debit amount")

    if wallet.status != WalletStatus.ACTIVE:
        raise ValueError("Wallet is not active")

    current = Decimal(str(wallet.balance or 0))
    if current < amount:
        raise ValueError("Insufficient wallet balance")

    wallet.balance = current - amount
    if wallet.balance == 0:
        wallet.status = WalletStatus.DISABLED

    session.add(wallet)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=-amount,
        type=WalletTransactionType.DEBIT,
        reference=str(order_id),
        description=f"Order payment {order_id}",
    )
    session.add(tx)
    session.commit()
    session.refresh(wallet)
    session.refresh(tx)
    return wallet, tx


def refund_to_wallet(session, wallet: Wallet, amount: Decimal, description: str | None = None):
    if amount <= 0:
        raise ValueError("Refund amount must be positive")

    wallet.balance = (wallet.balance or Decimal("0")) + amount
    if wallet.status == WalletStatus.DISABLED:
        wallet.status = WalletStatus.ACTIVE

    session.add(wallet)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=amount,
        type=WalletTransactionType.REFUND,
        description=description,
    )
    session.add(tx)
    session.commit()
    session.refresh(wallet)
    session.refresh(tx)
    return wallet, tx
