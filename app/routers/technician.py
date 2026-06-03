from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from uuid import UUID
from app.database import get_session
from app.models.user import User
from app.models.technician import Technician, TechnicianStatus
from app.schemas.technician import TechnicianRequest, TechnicianResponse
from app.utils.security import get_current_user

router = APIRouter()


@router.post("/technicians/request", response_model=TechnicianResponse, status_code=201)
def request_technician(
    req: TechnicianRequest,
    session = Depends(get_session),
    user = Depends(get_current_user)
):
    if user.role.value == "ADMIN":
        raise HTTPException(status_code=400, detail="Admins cannot request technician access")
    existing = session.exec(select(Technician).where(Technician.user_id == user.id)).first()
    if existing and existing.status == TechnicianStatus.PENDING:
        raise HTTPException(status_code=400, detail="Pending technician request already exists")
    technician = Technician(user_id=user.id, specialization=req.specialization)
    session.add(technician)
    session.commit()
    session.refresh(technician)
    return TechnicianResponse(
        id=str(technician.id),
        user_id=str(technician.user_id),
        email=user.email,
        role=user.role.value,
        status=technician.status.value,
        specialization=technician.specialization,
        created_at=technician.created_at.isoformat() if technician.created_at else None,
    )
