"""Tests for Technician workflow"""

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
import pytest
import uuid

from app.main import app
from app.models.user import User, UserRole
from app.models.technician import Technician, TechnicianStatus


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="client")
def client_fixture(engine):
    import app.database as db
    original_engine = db.engine
    db.engine = engine
    try:
        yield TestClient(app)
    finally:
        db.engine = original_engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


def test_technician_workflow(client: TestClient, session: Session):
    """Test complete technician workflow: register -> request approval -> list requests -> approve"""

    # Step 1: Register as CLIENT
    register_data = {"email": "testclient@example.com", "password": "testpass123"}
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Verify user is created with CLIENT role
    user = session.get(User, uuid.UUID(user_id))
    assert user.role.value == "CLIENT"

    # Promote second registered user to ADMIN
    admin_user = session.exec(select(User).where(User.email == "admin@example.com")).first()
    admin_user.role = UserRole.ADMIN
    session.commit()
    session.refresh(admin_user)
    login_response = client.post(
        "/auth/login",
        data={"username": "testclient@example.com", "password": "testpass123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request technician status
    request_response = client.post(
        "/technician/technicians/request",
        json={"specialization": "Screen Repair"},
        headers=headers,
    )
    assert request_response.status_code == 201
    tech_data = request_response.json()
    assert tech_data["status"] == "PENDING"
    assert tech_data["specialization"] == "Screen Repair"

    # Step 3: Admin approves the request
    # Create admin user
    admin_data = {"email": "admin@example.com", "password": "adminpass123"}
    client.post("/auth/register", json=admin_data)
    admin_login = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # List pending requests
    list_response = client.get("/admin/technicians/requests", headers=admin_headers)
    assert list_response.status_code == 200
    pending_requests = list_response.json()
    assert len(pending_requests) == 1
    assert pending_requests[0]["status"] == "PENDING"

    # Approve the request
    tech_id = pending_requests[0]["id"]
    approve_response = client.post(
        f"/admin/technicians/{tech_id}/review",
        json={"action": "approve"},
        headers=admin_headers,
    )
    assert approve_response.status_code == 200
    approved_data = approve_response.json()
    assert approved_data["status"] == "APPROVED"

    # Verify user role changed to TECHNICIAN
    session.refresh(user)
    assert user.role.value == "TECHNICIAN"

    # Verify technician status is APPROVED
    technician = session.exec(
        select(Technician).where(Technician.user_id == user_id)
    ).first()
    assert technician.status == TechnicianStatus.APPROVED
    assert technician.reviewed_by is not None


def test_cannot_request_twice(client: TestClient, session: Session):
    """Test that user cannot submit multiple pending requests"""

    # Register and login
    client.post("/auth/register", json={"email": "usertest@example.com", "password": "pass123"})
    login_resp = client.post(
        "/auth/login",
        data={"username": "usertest@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First request
    r1 = client.post("/technician/technicians/request", json={}, headers=headers)
    assert r1.status_code == 201

    # Second request
    r2 = client.post("/technician/technicians/request", json={}, headers=headers)
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]


def test_admin_cannot_request(client: TestClient, session: Session):
    """Ensure admin cannot request technician access"""

    client.post("/auth/register", json={"email": "adminuser@example.com", "password": "admin"})
    login_resp = client.post(
        "/auth/login",
        data={"username": "adminuser@example.com", "password": "admin"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/technician/technicians/request", json={}, headers=headers)
    assert r.status_code == 400
