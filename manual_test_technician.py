#!/usr/bin/env python3
"""Manual integration test for Technician workflow.

Run with:
  python manual_test_technician.py

Expects:
- Alembic migration 004 applied
- App imports cleanly
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
import uuid

from app.main import app
from app.models.user import User, UserRole
from app.models.technician import Technician, TechnicianStatus
from app.database import get_session
import app.database as db_module


def setup_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    db_module.engine = engine
    return engine


def teardown_db(original_engine):
    db_module.engine = original_engine


def get_client():
    return TestClient(app)


def test_workflow():
    original_engine = db_module.engine
    try:
        engine = setup_db()
        client = get_client()

        print("\n=== STEP 1: Register CLIENT ===")
        r = client.post("/auth/register", json={"email": "client@test.com", "password": "pass123"})
        print("register:", r.status_code, r.text)
        assert r.status_code == 200, f"expected 200, got {r.status_code}"
        user_id = r.json()["id"]

        with Session(engine) as session:
            user_obj = session.exec(select(User).where(User.email == "client@test.com")).first()
            assert user_obj.role.value == "CLIENT"

        print("\n=== STEP 2: Login + request technician ===")
        r = client.post("/auth/login", data={"username": "client@test.com", "password": "pass123"})
        print("login:", r.status_code)
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post("/technician/technicians/request", json={"specialization": "Screen Repair"}, headers=headers)
        print("request:", r.status_code, r.text)
        assert r.status_code == 201, f"expected 201, got {r.status_code}"
        assert r.json()["status"] == "PENDING"

        print("\n=== STEP 3: Register ADMIN and promote ===")
        r = client.post("/auth/register", json={"email": "admin@test.com", "password": "admin123"})
        print("register admin:", r.status_code, r.text)
        assert r.status_code == 200
        with Session(engine) as session:
            admin_user = session.exec(select(User).where(User.email == "admin@test.com")).first()
            admin_user.role = UserRole.ADMIN
            session.commit()

        print("\n=== STEP 4: Admin lists pending requests ===")
        r = client.post("/auth/login", data={"username": "admin@test.com", "password": "admin123"})
        admin_token = r.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        r = client.get("/admin/technicians/requests", headers=admin_headers)
        print("list pending:", r.status_code, r.text)
        assert r.status_code == 200, f"expected 200, got {r.status_code}"
        pending = r.json()
        assert len(pending) == 1
        tech_id = pending[0]["id"]

        print("\n=== STEP 5: Admin approves ===")
        r = client.post(f"/admin/technicians/{tech_id}/review", json={"action": "approve"}, headers=admin_headers)
        print("approve:", r.status_code, r.text)
        assert r.status_code == 200, f"expected 200, got {r.status_code}"
        assert r.json()["status"] == "APPROVED"

        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == "client@test.com")).first()
            assert user.role.value == "TECHNICIAN"
            tech = session.exec(select(Technician).where(Technician.user_id == str(user.id))).first()
            assert tech.status == TechnicianStatus.APPROVED
            assert tech.reviewed_by is not None

        print("\n=== STEP 6: Duplicate request blocked ===")
        r = client.post("/technician/technicians/request", json={"specialization": "Battery"}, headers=headers)
        print("duplicate:", r.status_code, r.text)
        assert r.status_code == 400

        print("\n=== STEP 7: Admin reject ===")
        r = client.post("/auth/register", json={"email": "client2@test.com", "password": "pass123"})
        assert r.status_code == 200
        user2_id = r.json()["id"]

        r = client.post("/auth/login", data={"username": "client2@test.com", "password": "pass123"})
        token2 = r.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        r = client.post("/technician/technicians/request", json={"specialization": "Software"}, headers=headers2)
        assert r.status_code == 201
        tech2_id = r.json()["id"]

        r = client.post(f"/admin/technicians/{tech2_id}/review", json={"action": "reject"}, headers=admin_headers)
        print("reject:", r.status_code, r.text)
        assert r.status_code == 200
        assert r.json()["status"] == "REJECTED"
        with Session(engine) as session:
            user2 = session.exec(select(User).where(User.email == "client2@test.com")).first()
            assert user2.role.value == "CLIENT"

        print("\n=== ALL CHECKS PASSED ===")
    finally:
        teardown_db(original_engine)


if __name__ == "__main__":
    test_workflow()
