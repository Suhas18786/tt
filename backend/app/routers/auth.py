import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Faculty, User
from ..schemas import LoginIn, PasswordChangeIn
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("timetable.auth")


def user_payload(db: Session, u: User) -> dict:
    fac = db.query(Faculty).filter(Faculty.user_id == u.id).first()
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
            "faculty_id": fac.id if fac else None}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    # Same error for unknown user and wrong password (no account enumeration).
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        log.warning("failed login for %s", data.email)
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer",
            "user": user_payload(db, user)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_payload(db, user)


@router.post("/change-password", status_code=204)
def change_password(data: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
