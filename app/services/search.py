from typing import Optional, List, Dict, Tuple
from sqlmodel import select, or_
from app.database import get_session
from app.models.item import Item
from app.schemas.search import SearchValidateRequest
from app.services.pricing import get_price_final


# Extended category map for convenience - clickable options
CATEGORY_ALIASES = {
    "remote": "Remote Services",
    "remotes": "Remote Services",
    "remote service": "Remote Services",
    "tool": "Tool Rental",
    "tools": "Tool Rental",
    "tool rental": "Tool Rental",
    "rental": "Tool Rental",
    "mdm": "Remote Services",  # MDM removal is handled remotely
    "mdm removal": "Remote Services",
    "activation": "Remote Services",
    "activation lock": "Remote Services",
    "bypass": "Remote Services",
    "icloud": "Remote Services",
    "frp": "Remote Services",
    "unlock": "Remote Services",
    "imei": "Remote Services",
    "check": "Remote Services",
    "report": "Remote Services",
}


def resolve_category(input_category: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Resolve the input to a proper category and return any validation messages."""
    if not input_category:
        return None, []
    
    normalized = input_category.lower().strip()
    
    if normalized in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[normalized], []
    
    return input_category, [f"Category '{input_category}' is not a standard category. Results may be limited."]


def build_search_query(request: SearchValidateRequest) -> Tuple[str, List[str]]:
    """Build SQL query filters and return filters for debugging."""
    filters = []
    params = {}
    
    if request.q:
        filters.append("LOWER(i.title) LIKE :q")
        params["q"] = f"%{request.q.lower()}%"
    
    if request.category:
        filters.append("i.category = :category")
        params["category"] = request.category
    
    if request.item_ids:
        filters.append("i.id IN :item_ids")
        params["item_ids"] = tuple(request.item_ids)
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    return f"SELECT * FROM item i WHERE {where_clause} AND i.is_visible = true AND i.is_archived = false", params


def search_service(request: SearchValidateRequest, user_is_authenticated: bool = False) -> Dict:
    """Execute the search validation and return results."""
    from app.schemas.item import ItemPublic
    from app.models.item import ItemType
    
    # Auto-resolve category alias if provided
    resolved_category, category_messages = resolve_category(request.category)
    
    # Build validation messages
    validation_messages = []
    validation_messages.extend(category_messages)
    
    has_any_param = any([request.q, request.category, request.item_ids])
    if not has_any_param:
        validation_messages.append("No search parameters provided. Showing all visible services.")
    
    # Build and run query
    sql, params = build_search_query(request)
    if resolved_category:
        params["category"] = resolved_category
    
    session = next(get_session())
    stmt = select(Item).where(Item.is_visible == True, Item.is_archived == False)
    
    if request.q:
        stmt = stmt.where(Item.title.ilike(f"%{request.q}%"))
    if resolved_category:
        stmt = stmt.where(Item.category == resolved_category)
    if request.item_ids:
        stmt = stmt.where(Item.id.in_(request.item_ids))
    
    items = session.exec(stmt).all()
    
    accessible_matches = 0 if not user_is_authenticated else len(items)
    
    results = []
    for item in items:
        price_final = get_price_final(item, session)
        
        results.append(ItemPublic(
            id=str(item.id),
            uid=item.uid,
            slug=item.slug,
            title=item.title,
            description=item.description,
            item_type=item.item_type,
            category=item.category,
            thumbnail=item.thumbnail,
            price_final=price_final,
            currency=item.currency,
            delivery_time=item.delivery_time,
            stock=item.stock,
        ))
    
    return {
        "items": results,
        "total_matches": len(results),
        "accessible_matches": accessible_matches,
        "valid_query": True,
        "valid_category": resolved_category is not None,
        "valid_service_type": True,
        "valid_location": request.location is None,
        "validation_messages": validation_messages,
    }
