from sqlmodel import select
from datetime import datetime

from app.database import get_session
from app.models.credential import Credential
from app.models.item import Item
from app.utils.email import send_credential_ready_email


def fulfill_service_order(order, session):
    assigned = False
    for oi in order.items:
        item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
        if not item or item.item_type.value != "SERVICE":
            continue
        
        needed = oi.quantity
        available = session.exec(
            select(Credential).where(
                Credential.item_id == oi.item_id,
                Credential.is_used == False
            )
        ).all()
        
        for cred in available[:needed]:
            cred.is_used = True
            cred.order_item_id = oi.id
            cred.assigned_at = datetime.utcnow()
            session.commit()
            assigned = True
    
    return assigned


def fulfill_product_order(order, session):
    for oi in order.items:
        item = session.exec(select(Item).where(Item.id == oi.item_id)).first()
        if not item or item.item_type.value != "PRODUCT":
            continue
        
        if item.stock is not None:
            item.stock = max(0, item.stock - oi.quantity)
            session.commit()


def fulfill_order(order, session):
    service_assigned = fulfill_service_order(order, session)
    fulfill_product_order(order, session)
    return service_assigned