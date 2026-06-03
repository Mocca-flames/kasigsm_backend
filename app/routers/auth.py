from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from sqlmodel import select
import bcrypt
from jose import jwt

from app.database import get_session
from app.models.user import User
from app.config import settings
from app.schemas.item import UserRegister, Token
from app.utils.email import send_email

router = APIRouter()


@router.post("/register", response_model=dict)
def register(user_in: UserRegister, session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = bcrypt.hashpw(user_in.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=user_in.email, password_hash=password_hash)
    session.add(user)
    session.commit()
    send_email(user.email, "Welcome!", "Your account has been created successfully.")
    return {"id": str(user.id), "email": user.email}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not bcrypt.checkpw(form_data.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.email, "exp": datetime.utcnow() + access_token_expires},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return Token(access_token=access_token, token_type="bearer")