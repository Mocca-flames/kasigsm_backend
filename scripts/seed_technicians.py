from datetime import datetime, timezone
from sqlmodel import select
from app.database import get_session
from app.models.technician import Technician, TechnicianStatus
from app.models.user import User, UserRole


def seed_technicians():
    with next(get_session()) as session:
        users = session.exec(select(User)).all()
        if not users:
            print("No users found. Create users first.")
            return

        technicians_data = [
            {"email": "technician@example.com", "specialization": "Screen Repair"},
            {"email": "tech2@example.com", "specialization": "Battery Replacement"},
            {"email": "tech3@example.com", "specialization": "Software Flashing"},
        ]

        for tech_data in technicians_data:
            user = session.exec(select(User).where(User.email == tech_data["email"])).first()
            if not user:
                print(f"User {tech_data['email']} not found. Skipping.")
                continue

            technician = Technician(
                user_id=user.id,
                specialization=tech_data["specialization"],
                status=TechnicianStatus.APPROVED,
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=user.id,
            )
            session.add(technician)
            user.role = UserRole.TECHNICIAN

        session.commit()
        print(f"Seeded {len(technicians_data)} technicians")
