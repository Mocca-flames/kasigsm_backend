from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from sqlmodel import select
import time
import bcrypt
from jose import jwt

from app.database import get_session
from app.models.user import User
from app.config import settings
from app.schemas.item import UserRegister, Token, OTPVerify
from app.utils.email import send_welcome_email, send_otp_email
from app.models.otp import create_otp, verify_otp
from app.dependencies import rate_limit_auth, rate_limit_otp, login_throttle

router = APIRouter()


@router.post("/register", response_model=dict)
def register(user_in: UserRegister, request: Request, session = Depends(get_session)):
    rate_limit_otp(request)
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Email registered but not verified. Please check your inbox or resend OTP.")
    
    password_hash = bcrypt.hashpw(user_in.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=user_in.email, password_hash=password_hash, is_active=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    code = create_otp(session, user.email, purpose="REGISTER")
    send_otp_email(user.email, code)
    
    return {"id": str(user.id), "email": user.email, "message": "Account created. Please verify your email with the OTP sent."}


@router.post("/verify-otp", response_model=dict)
def verify_otp_endpoint(otp_in: OTPVerify, request: Request, session = Depends(get_session)):
    rate_limit_otp(request)
    otp = verify_otp(session, otp_in.email, otp_in.code, purpose="REGISTER")
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    user = session.exec(select(User).where(User.email == otp_in.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    session.add(user)
    session.commit()
    session.refresh(user)
    
    send_welcome_email(user.email)
    
    return {"id": str(user.id), "email": user.email, "message": "Email verified. Account activated."}


@router.post("/resend-otp", response_model=dict)
def resend_otp(email: str, request: Request, session = Depends(get_session)):
    rate_limit_otp(request)
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="Account already verified")
    
    code = create_otp(session, user.email, purpose="REGISTER")
    send_otp_email(user.email, code)
    return {"message": "OTP resent"}


@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session = Depends(get_session)):
    rate_limit_auth(request)
    login_key = login_throttle(request)
    
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not bcrypt.checkpw(form_data.password.encode(), user.password_hash.encode()):
        from app.dependencies import rate_limiter
        rate_limiter.record_failure(login_key)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    from app.dependencies import rate_limiter
    rate_limiter.clear(login_key)
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email first.")
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.email, "exp": datetime.utcnow() + access_token_expires},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return Token(access_token=access_token, token_type="bearer")
