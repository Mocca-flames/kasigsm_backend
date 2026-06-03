from fastapi import APIRouter, Depends, HTTPException
from typing import List
from decimal import Decimal
from sqlmodel import select
import uuid

from app.database import get_session
from app.models.item import Item
from app.models.order import Order, OrderItem, OrderStatus
from app.models.credential import Credential
from app.schemas.order import OrderCreate, OrderPublic, OrderItemPublic, CredentialPublic
from app.services.pricing import get_price_final
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter()


def decrypt_payload(encrypted: str) -> str:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    import binascii
    
    key = bytes.fromhex(settings.ENCRYPTION_KEY)
    iv = binascii.unhexlify(encrypted[:32])
    ciphertext = binascii.unhexlify(encrypted[32:])
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted.decode()


@router.post("/orders", response_model=OrderPublic)
def create_order(order_in: OrderCreate, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    total = Decimal("0")
    order_items = []
    
    for oi in order_in.items:
        item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
        if not item or not item.is_visible or item.is_archived:
            raise HTTPException(status_code=400, detail=f"Item {oi.item_id} not available")
        if item.stock is not None and item.stock < oi.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for item {oi.item_id}")
        
        price_final = get_price_final(item, session)
        
        total += price_final * oi.quantity
        order_items.append(OrderItem(
            item_id=oi.item_id,
            quantity=oi.quantity,
            unit_price=price_final
        ))
        
        if item.stock is not None:
            item.stock -= oi.quantity
            session.commit()
    
    order = Order(user_id=user.id, status=OrderStatus.PENDING, total_amount=total, items=order_items)
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return OrderPublic(
        id=str(order.id),
        status=order.status.value,
        total_amount=order.total_amount,
        currency=order.currency,
        created_at=order.created_at.isoformat(),
        items=[OrderItemPublic(
            id=str(oi.id),
            item_id=str(oi.item_id),
            quantity=oi.quantity,
            unit_price=oi.unit_price
        ) for oi in order.items]
    )


@router.get("/orders", response_model=List[OrderPublic])
def list_orders(user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")


@router.get("/orders/{order_id}", response_model=OrderPublic)
def get_order(order_id: str, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    orders = session.exec(select(Order).where(Order.user_id == user.id)).all()
    return [_order_to_public(o, session) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderPublic)
def get_order(order_id: str, user = Depends(get_current_user), session = Depends(get_session)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")
    
    order = session.exec(select(Order).where(Order.id == uuid.UUID(order_id), Order.user_id == user.id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return _order_to_public(order, session)


def _order_to_public(order: Order, session) -> OrderPublic:
    items = []
    for oi in order.items:
        creds = []
        if order.status == OrderStatus.PAID:
            credentials = session.exec(
                select(Credential).where(Credential.order_item_id == oi.id)
            ).all()
            for cred in credentials:
                try:
                    decrypted = decrypt_payload(cred.payload)
                except Exception:
                    decrypted = "[encrypted]"
                creds.append(CredentialPublic(
                    id=str(cred.id),
                    item_id=str(cred.item_id),
                    payload=decrypted
                ))
        
        items.append(OrderItemPublic(
            id=str(oi.id),
            item_id=str(oi.item_id),
            quantity=oi.quantity,
            unit_price=oi.unit_price,
            credentials=creds if creds else None
        ))
    
    return OrderPublic(
        id=str(order.id),
        status=order.status.value,
        total_amount=order.total_amount,
        currency=order.currency,
        created_at=order.created_at.isoformat(),
        items=items
    )