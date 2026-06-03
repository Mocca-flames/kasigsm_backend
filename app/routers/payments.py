from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
import uuid
import httpx
from decimal import Decimal

from app.database import get_session
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.payment import PaymentInitiate, PaymentVerify
from app.config import settings
from app.utils.security import get_current_user
from app.services.fulfillment import fulfill_order
from app.utils.email import send_email

router = APIRouter()


@router.post("/initiate")
def initiate_payment(payment_in: PaymentInitiate, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    order = session.exec(
        select(Order).where(Order.id == uuid.UUID(payment_in.order_id), Order.user_id == user.id)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order is not pending")
    
    amount_kobo = int(order.total_amount * 100)
    
    payload = {
        "email": user.email,
        "amount": amount_kobo,
        "reference": f"PAY-{order.id.hex[:12].upper()}",
        "callback_url": payment_in.return_url or settings.PAYSTACK_CALLBACK_URL,
    }
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    with httpx.Client() as client:
        response = client.post(
            f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=headers,
        )
    
    data = response.json()
    
    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Payment initiation failed"))
    
    order.payment_ref = data["data"]["reference"]
    order.payment_gateway = "paystack"
    session.commit()
    
    return {
        "authorization_url": data["data"]["authorization_url"],
        "reference": data["data"]["reference"],
    }


@router.post("/verify")
def verify_payment(payment_in: PaymentVerify, session = Depends(get_session)):
    reference = payment_in.reference
    
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    
    with httpx.Client() as client:
        response = client.get(
            f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=headers,
        )
    
    data = response.json()
    
    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Verification failed"))
    
    transaction_data = data["data"]
    
    if transaction_data["status"] != "success":
        return {"status": "pending", "message": "Payment not successful"}
    
    order = session.exec(
        select(Order).where(Order.payment_ref == reference)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == OrderStatus.PAID:
        return {"status": "already_processed", "message": "Order already paid"}
    
    paid_amount = Decimal(transaction_data["amount"]) / 100
    if paid_amount != order.total_amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")
    
    order.status = OrderStatus.PAID
    session.commit()
    
    user = session.exec(select(User).where(User.id == order.user_id)).first()
    send_email(user.email, "Order Paid!", f"Your order {order.id} has been paid successfully.")
    fulfill_order(order, session)
    
    return {"status": "success", "order_id": str(order.id)}


@router.get("/verify/{reference}")
def verify_payment_get(reference: str, session = Depends(get_session)):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    
    with httpx.Client() as client:
        response = client.get(
            f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=headers,
        )
    
    data = response.json()
    
    if not data.get("status"):
        raise HTTPException(status_code=400, detail=data.get("message", "Verification failed"))
    
    transaction_data = data["data"]
    
    if transaction_data["status"] != "success":
        raise HTTPException(status_code=400, detail="Payment not successful")
    
    order = session.exec(
        select(Order).where(Order.payment_ref == reference)
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == OrderStatus.PAID:
        return {"status": "already_processed", "order_id": str(order.id)}
    
    paid_amount = Decimal(transaction_data["amount"]) / 100
    if paid_amount != order.total_amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")
    
    order.status = OrderStatus.PAID
    session.commit()
    
    user = session.exec(select(User).where(User.id == order.user_id)).first()
    send_email(user.email, "Order Paid!", f"Your order {order.id} has been paid successfully.")
    fulfill_order(order, session)
    
    return {"status": "success", "order_id": str(order.id)}