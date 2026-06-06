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
from app.schemas.item import UserRegister, Token, OTPVerify, ForgotPassword, ResetPassword
from app.utils.email import send_welcome_email, send_otp_email, send_password_reset_email, send_password_changed_email, send_email
from app.models.otp import create_otp, verify_otp
from app.models.password_reset import create_password_reset, get_valid_password_reset
from app.dependencies import rate_limit_auth, rate_limit_otp, login_throttle, rate_limiter
from app.utils.wallet import get_or_create_wallet

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

    get_or_create_wallet(session, user.id)

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
    
    if not user:
        rate_limiter.record_failure(login_key)
        raise HTTPException(status_code=404, detail="User not found. Please register.")
    
    if not user.is_active:
        rate_limiter.record_failure(login_key)
        raise HTTPException(status_code=403, detail="Account not active. Please verify your email.")
    
    if not bcrypt.checkpw(form_data.password.encode(), user.password_hash.encode()):
        rate_limiter.record_failure(login_key)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    rate_limiter.clear(login_key)
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.email, "exp": datetime.utcnow() + access_token_expires, "reset": int(user.password_reset_at.timestamp()) if user.password_reset_at else 0},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/forgot-password", response_model=dict)
def forgot_password(payload: ForgotPassword, request: Request, session = Depends(get_session)):
    rate_limit_auth(request)
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    reset = create_password_reset(session, user.id, user.email)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset.token}"
    send_password_reset_email(user.email, reset_link)
    return {"message": "If an account exists for this email, a password reset link has been sent."}


@router.post("/reset-password", response_model=dict)
def reset_password(payload: ResetPassword, session = Depends(get_session)):
    reset = get_valid_password_reset(session, payload.token)
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = session.exec(select(User).where(User.id == reset.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = bcrypt.hashpw(payload.new_password.encode(), bcrypt.gensalt()).decode()
    user.password_reset_at = datetime.now(timezone.utc)
    session.add(user)
    reset.is_used = True
    session.add(reset)
    session.commit()
    send_email(to_email=user.email, subject="Password changed", body="Your password has been reset successfully.")
    return {"message": "Password reset successful"}
