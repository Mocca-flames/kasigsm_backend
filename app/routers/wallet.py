from fastapi import APIRouter, Depends, HTTPException
from typing import List
from decimal import Decimal
from sqlmodel import select
import uuid

from app.database import get_session
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.wallet import Wallet, WalletTransaction, WalletTopUp, WalletTransactionType, WalletTopUpStatus
from app.schemas.wallet import (
    WalletPublic,
    WalletTopUpRequest,
    WalletTopUpReview,
    WalletAdminCredit,
    WalletPayRequest,
)
from app.utils.wallet import get_or_create_wallet
from app.services.wallet_service import (
    approve_top_up,
    reject_top_up,
    admin_credit,
    debit_for_order,
)
from app.utils.security import get_current_user, require_admin
from app.config import settings

router = APIRouter()


@router.get("/me", response_model=WalletPublic)
def get_my_wallet(user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    wallet = get_or_create_wallet(session, user.id)
    return WalletPublic(
        id=str(wallet.id),
        balance=wallet.balance,
        status=wallet.status.value,
        client_ref=wallet.client_ref,
        is_low_balance=bool(wallet.balance <= settings.WALLET_LOW_BALANCE_THRESHOLD),
    )


@router.post("/top-up", response_model=dict)
def create_top_up(top_up_in: WalletTopUpRequest, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    amount = top_up_in.amount
    if amount % settings.WALLET_TOPUP_STEP != 0:
        raise HTTPException(status_code=400, detail=f"Amount must be a multiple of {settings.WALLET_TOPUP_STEP}")
    if amount < settings.WALLET_TOPUP_MIN or amount > settings.WALLET_TOPUP_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Amount must be between {settings.WALLET_TOPUP_MIN} and {settings.WALLET_TOPUP_MAX}",
        )

    wallet = get_or_create_wallet(session, user.id)
    top_up = WalletTopUp(wallet_id=wallet.id, amount=amount, reference=top_up_in.reference, proof_note=top_up_in.proof_note)
    session.add(top_up)
    session.commit()
    session.refresh(top_up)

    return {
        "id": str(top_up.id),
        "wallet_id": str(wallet.id),
        "amount": amount,
        "reference": top_up.reference,
        "status": top_up.status.value,
        "client_ref": wallet.client_ref,
        "message": "Top-up request submitted. Admin will review shortly.",
    }


@router.get("/transactions", response_model=List[dict])
def list_transactions(user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    wallet = session.exec(select(Wallet).where(Wallet.user_id == user.id)).first()
    if not wallet:
        return []

    txs = session.exec(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
    ).all()
    return [
        {
            "id": str(t.id),
            "amount": t.amount,
            "type": t.type.value,
            "reference": t.reference,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txs
    ]


@router.post("/pay", response_model=dict)
def pay_with_wallet(pay_in: WalletPayRequest, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    order = session.exec(
        select(Order).where(Order.id == pay_in.order_id, Order.user_id == user.id)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order is not pending")

    wallet = get_or_create_wallet(session, user.id)
    try:
        wallet, tx = debit_for_order(session, wallet, order.total_amount, order.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    order.status = OrderStatus.PAID
    order.payment_gateway = "wallet"
    order.payment_ref = f"WALLET-{order.id.hex[:8]}"
    session.add(order)
    session.commit()
    session.refresh(order)

    from app.services.email import send_order_paid_email

    user = session.exec(select(User).where(User.id == order.user_id)).first()
    if user:
        send_order_paid_email(user.email, str(order.id), float(order.total_amount), order.currency, len(order.items))

    return {
        "order_id": str(order.id),
        "status": order.status.value,
        "wallet_balance": wallet.balance,
        "wallet_status": wallet.status.value,
    }


@router.post("/top-ups/{top_up_id}/review", response_model=dict)
def review_top_up(
    top_up_id: str,
    review_in: WalletTopUpReview,
    admin = Depends(require_admin),
    session = Depends(get_session),
):
    top_up = session.exec(select(WalletTopUp).where(WalletTopUp.id == top_up_id)).first()
    if not top_up:
        raise HTTPException(status_code=404, detail="Top-up not found")

    if top_up.status != WalletTopUpStatus.PENDING:
        raise HTTPException(status_code=400, detail="Top-up already reviewed")

    if review_in.approved:
        wallet, top_up, tx = approve_top_up(session, top_up, review_in.note)
    else:
        top_up = reject_top_up(session, top_up, review_in.note)
        session.refresh(top_up)
        wallet = session.exec(select(Wallet).where(Wallet.id == top_up.wallet_id)).first()

    return {
        "id": str(top_up.id),
        "wallet_id": str(wallet.id) if wallet else None,
        "amount": top_up.amount,
        "reference": top_up.reference,
        "status": top_up.status.value,
        "reviewed_at": top_up.reviewed_at.isoformat() if top_up.reviewed_at else None,
        "wallet_balance": wallet.balance if wallet else None,
    }


@router.get("/top-ups", response_model=List[dict])
def list_top_ups(status: str = None, admin = Depends(require_admin), session = Depends(get_session)):
    stmt = select(WalletTopUp)
    if status:
        stmt = stmt.where(WalletTopUp.status == WalletTopUpStatus(status))
    top_ups = session.exec(stmt.order_by(WalletTopUp.created_at.desc())).all()
    return [
        {
            "id": str(t.id),
            "wallet_id": str(t.wallet_id),
            "amount": t.amount,
            "reference": t.reference,
            "proof_note": t.proof_note,
            "status": t.status.value,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
        }
        for t in top_ups
    ]


@router.patch("/{wallet_id}/credit", response_model=dict)
def credit_wallet(
    wallet_id: str,
    credit_in: WalletAdminCredit,
    admin = Depends(require_admin),
    session = Depends(get_session),
):
    if credit_in.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wallet = session.exec(select(Wallet).where(Wallet.id == wallet_id)).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet, tx = admin_credit(session, wallet, credit_in.amount, credit_in.description)
    return {
        "wallet_id": str(wallet.id),
        "balance": wallet.balance,
        "status": wallet.status.value,
        "transaction_id": str(tx.id),
        "amount": tx.amount,
    }


@router.get("/all", response_model=List[dict])
def list_all_wallets(session = Depends(get_session), admin = Depends(require_admin)):
    wallets = session.exec(select(Wallet, User).join(User, User.id == Wallet.user_id)).all()
    results = []
    for wallet, user in wallets:
        results.append({
            "id": str(wallet.id),
            "user_id": str(wallet.user_id),
            "email": user.email,
            "client_ref": wallet.client_ref,
            "balance": wallet.balance,
            "status": wallet.status.value,
            "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
        })
    return results
