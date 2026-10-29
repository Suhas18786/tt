from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_faculty, get_current_user, require_admin
from ..models import ConflictReport, Faculty, Generation, Subject, TeachingAssignment, User
from ..schemas import ConflictReportIn, ConflictResolveIn
from ..services import generation as svc

router = APIRouter(tags=["faculty portal"])


@router.get("/me/timetable")
def my_timetable(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fac = current_faculty(user, db)
    gens = db.query(Generation).filter(Generation.status == "published").order_by(Generation.id).all()
    sessions, config, gen_ids = [], None, []
    for g in gens:
        mine = [s for s in svc.serialize_sessions(db, svc.load_sessions(db, g.id)) if s["faculty_id"] == fac.id]
        if mine:
            sessions += mine
            config = config or {"working_days": g.config["working_days"], "periods": g.config["periods"],
                                "blocked_slots": g.config.get("blocked_slots", [])}
            gen_ids.append(g.id)
    return {"faculty_id": fac.id, "faculty_name": fac.full_name, "generation_ids": gen_ids,
            "config": config, "sessions": sessions}


@router.get("/me/workload")
def my_workload(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fac = current_faculty(user, db)
    rows = (db.query(TeachingAssignment, Subject).join(Subject, Subject.id == TeachingAssignment.subject_id)
            .filter(TeachingAssignment.faculty_id == fac.id).all())
    return {"faculty": {"id": fac.id, "name": fac.full_name, "max_hours_per_day": fac.max_hours_per_day,
                        "max_hours_per_week": fac.max_hours_per_week},
            "assignments": [{"assignment_id": ta.id, "batch_id": ta.batch_id, "subject_code": s.code,
                             "subject_name": s.name, "weekly_hours": s.weekly_hours, "type": s.subject_type}
                            for ta, s in rows],
            "total_hours": sum(s.weekly_hours for _, s in rows)}


def _report_out(r: ConflictReport, fac_name: str):
    return {"id": r.id, "faculty_id": r.faculty_id, "faculty_name": fac_name, "generation_id": r.generation_id,
            "message": r.message, "status": r.status, "admin_note": r.admin_note,
            "created_at": r.created_at.isoformat(), "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None}


@router.post("/conflict-reports", status_code=201)
def create_report(data: ConflictReportIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fac = current_faculty(user, db)
    r = ConflictReport(faculty_id=fac.id, generation_id=data.generation_id, message=data.message)
    db.add(r)
    db.commit()
    return _report_out(r, fac.full_name)


@router.get("/conflict-reports")
def list_reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(ConflictReport, Faculty).join(Faculty, Faculty.id == ConflictReport.faculty_id)
    if user.role != "admin":
        q = q.filter(Faculty.user_id == user.id)
    return [_report_out(r, f.full_name) for r, f in q.order_by(ConflictReport.id.desc()).limit(200)]


@router.post("/conflict-reports/{rid}/resolve")
def resolve_report(rid: int, data: ConflictResolveIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.get(ConflictReport, rid)
    if r is None:
        raise HTTPException(404, "Report not found")
    r.status, r.admin_note, r.resolved_at = "resolved", data.admin_note, datetime.now(timezone.utc)
    db.commit()
    fac = db.get(Faculty, r.faculty_id)
    return _report_out(r, fac.full_name)
