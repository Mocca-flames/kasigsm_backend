"""Seed initial data: admin user and auth accounts"""

import uuid
from sqlmodel import Session, select
from app.database import get_session
from app.models.user import User, UserRole
from app.models.technician import Technician, TechnicianStatus
from datetime import datetime, timezone

ADMIN_EMAIL = "admin@kasi.co.za"
ADMIN_PASSWORD = "Maurice@12!"
TEST_CLIENT_EMAIL = "client@test.com"
TEST_CLIENT_PASSWORD = "testpass123"


def get_or_create_admin(session: Session) -> User:
    admin = session.exec(select(User).where(User.email == ADMIN_EMAIL)).first()
    if not admin:
        import bcrypt
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
            role=UserRole.ADMIN,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        print(f"Created admin: {ADMIN_EMAIL}")
    else:
        admin.role = UserRole.ADMIN
        session.commit()
        print(f"Admin exists: {ADMIN_EMAIL}")
    return admin


def get_or_create_client(session: Session) -> User:
    client = session.exec(select(User).where(User.email == TEST_CLIENT_EMAIL)).first()
    if not client:
        import bcrypt
        client = User(
            email=TEST_CLIENT_EMAIL,
            password_hash=bcrypt.hashpw(TEST_CLIENT_PASSWORD.encode(), bcrypt.gensalt()).decode(),
            role=UserRole.CLIENT,
        )
        session.add(client)
        session.commit()
        session.refresh(client)
        print(f"Created test client: {TEST_CLIENT_EMAIL}")
    else:
        print(f"Test client exists: {TEST_CLIENT_EMAIL}")
    return client


def seed_auth():
    with next(get_session()) as session:
        admin = get_or_create_admin(session)
        client = get_or_create_client(session)
        
        existing_tech = session.exec(
            select(Technician).where(Technician.user_id == client.id)
        ).first()
        if not existing_tech:
            tech = Technician(
                user_id=client.id,
                status=TechnicianStatus.APPROVED,
                specialization="General Repairs",
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=admin.id,
            )
            session.add(tech)
            session.commit()
            client.role = UserRole.TECHNICIAN
            session.commit()
            print(f"Created technician entry for {TEST_CLIENT_EMAIL}")
        else:
            print(f"Technician entry exists for {TEST_CLIENT_EMAIL}")


if __name__ == "__main__":
    seed_auth()
