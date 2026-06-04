import uuid
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Field, Column, String, DateTime, select
from app.utils.encryption import encrypt_payload, decrypt_payload


class OTP(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_type=String, nullable=False, index=True)
    code_hash: str = Field(sa_type=String, nullable=False)
    purpose: str = Field(sa_type=String, nullable=False, default="REGISTER")
    is_used: bool = Field(default=False)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


def _generate_code() -> str:
    import random
    return f"{random.randint(100000, 999999)}"


def create_otp(session, email: str, purpose: str = "REGISTER") -> str:
    code = _generate_code()
    otp = OTP(
        email=email,
        code_hash=encrypt_payload(code),
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    session.add(otp)
    session.commit()
    session.refresh(otp)
    return code


def verify_otp(session, email: str, code: str, purpose: str = "REGISTER") -> OTP | None:
    otp = session.exec(
        select(OTP).where(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.expires_at > datetime.now(timezone.utc),
        ).order_by(OTP.created_at.desc())
    ).first()
    if not otp:
        return None
    try:
        stored = decrypt_payload(otp.code_hash)
    except Exception:
        return None
    if stored != code:
        return None
    otp.is_used = True
    session.add(otp)
    session.commit()
    session.refresh(otp)
    return otp
