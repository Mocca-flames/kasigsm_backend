import uuid
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Field, Column, String, DateTime


class PasswordReset(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(sa_type=String, nullable=False, index=True)
    email: str = Field(sa_type=String, nullable=False, index=True)
    token: str = Field(sa_type=String, nullable=False, unique=True, index=True)
    is_used: bool = Field(default=False)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    )


def _generate_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


def create_password_reset(session, user_id: uuid.UUID, email: str) -> PasswordReset:
    token = _generate_token()
    reset = PasswordReset(
        user_id=user_id,
        email=email,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(reset)
    session.commit()
    session.refresh(reset)
    return reset


def get_valid_password_reset(session, token: str) -> PasswordReset | None:
    from sqlmodel import select
    return session.exec(
        select(PasswordReset).where(
            PasswordReset.token == token,
            PasswordReset.is_used == False,
            PasswordReset.expires_at > datetime.now(timezone.utc),
        ).order_by(PasswordReset.created_at.desc())
    ).first()
