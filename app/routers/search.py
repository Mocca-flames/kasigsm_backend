from fastapi import APIRouter, Depends
from typing import Optional
from sqlmodel import select
from app.database import get_session
from app.models.item import Item
from app.schemas.search import SearchValidateRequest


router = APIRouter()


@router.post("/search/validate")
def validate_search(request: SearchValidateRequest, session = Depends(get_session)):
    stmt = select(Item).where(Item.is_visible == True, Item.is_archived == False)

    if request.q:
        stmt = stmt.where(Item.title.ilike(f"%{request.q}%"))
    if request.category:
        stmt = stmt.where(Item.category == request.category)
    if request.item_ids:
        stmt = stmt.where(Item.id.in_(request.item_ids))

    items = session.exec(stmt).all()

    return {
        "valid": True,
        "total_matches": len(items),
        "items": [{"id": str(item.id), "title": item.title, "category": item.category} for item in items],
    }
