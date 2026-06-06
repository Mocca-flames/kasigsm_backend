from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
from sqlmodel import select

from app.database import get_session
from app.models.user import User
from app.config import settings

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session = Depends(get_session)
) -> Optional[User]:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=403, detail="Invalid token")
        reset_claim = payload.get("reset")
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(status_code=403, detail="User not found")
        if reset_claim is not None and int(reset_claim) != int(user.password_reset_at.timestamp()):
            raise HTTPException(status_code=403, detail="Session invalidated. Please log in again.")
        return user
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")


def require_admin(user: Optional[User] = Depends(get_current_user)):
    if not user or user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_technician(user: Optional[User] = Depends(get_current_user)):
    if not user or user.role.value not in ("ADMIN", "TECHNICIAN"):
        raise HTTPException(status_code=403, detail="Technician access required")
    return user