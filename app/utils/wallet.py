import random
import string
from datetime import datetime, timezone

from sqlmodel import select

from app.config import settings
from app.models.wallet import Wallet, WalletStatus, WalletTransactionType


def _generate_client_ref() -> str:
    letter = random.choice(string.ascii_uppercase)
    digits = f"{random.randint(0, 99999):05d}"
    return f"{letter}{digits}"


def ensure_client_ref_unique(session, ref: str) -> None:
    existing = session.exec(select(Wallet).where(Wallet.client_ref == ref)).first()
    if existing:
        raise RuntimeError(f"Client ref collision: {ref}")


def generate_unique_client_ref(session, max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        ref = _generate_client_ref()
        if not session.exec(select(Wallet).where(Wallet.client_ref == ref)).first():
            return ref
    raise RuntimeError("Failed to generate unique client_ref")


def get_or_create_wallet(session, user_id, auto_disable_expired=True):
    wallet = session.exec(select(Wallet).where(Wallet.user_id == user_id)).first()
    if wallet:
        if auto_disable_expired and wallet.status == WalletStatus.ACTIVE:
            if _is_wallet_expired(wallet):
                wallet.status = WalletStatus.DISABLED
                session.add(wallet)
                session.commit()
                session.refresh(wallet)
    else:
        client_ref = generate_unique_client_ref(session)
        wallet = Wallet(user_id=user_id, client_ref=client_ref)
        session.add(wallet)
        session.commit()
        session.refresh(wallet)
    return wallet


def _is_wallet_expired(wallet: Wallet) -> bool:
    if not wallet.updated_at:
        return False
    if not settings.wallet_expiry_days:
        return False
    now = datetime.now(timezone.utc)
    delta = now - wallet.updated_at
    return delta.days >= settings.wallet_expiry_days
