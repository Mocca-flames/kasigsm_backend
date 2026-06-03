from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from app.models.technician import Technician
from app.models.user import User, UserRole
import uuid

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    user = User(email="test@test.com", password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    print("user id:", repr(user.id), type(user.id))
    
    tech = Technician(user_id=user.id)
    session.add(tech)
    session.commit()
    session.refresh(tech)
    print("tech id:", repr(tech.id), type(tech.id))
    print("tech user_id:", repr(tech.user_id), type(tech.user_id))
    
    uid = str(user.id)
    print("str(user.id):", repr(uid), type(uid))
    
    q = select(Technician).where(Technician.user_id == uid)
    stmt = str(q.compile(engine))
    print("query:", stmt)
    result = session.exec(q).first()
    print("result:", result)
