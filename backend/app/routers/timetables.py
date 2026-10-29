import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import Generation, PublicationHistory, User
from ..schemas import GenerateIn, MoveIn
from ..services import generation as svc
from ..services.exports import render_pdf, render_xlsx

router = APIRouter(prefix="/timetables", tags=["timetables"])
log = logging.getLogger("timetable.api")


@router.post("/generate", status_code=201)
def generate(data: GenerateIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Runs the CP-SAT solver (synchronously; bounded by time_limit_seconds) and stores the result."""
    gen = svc.run_generation(db, user.id, data.model_dump(exclude_unset=True))
    return svc.serialize_generation(db, gen)


@router.get("")
def list_timetables(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Generation)
    if user.role != "admin":
        q = q.filter(Generation.status == "published")
    if status:
        q = q.filter(Generation.status == status)
    return [svc.serialize_generation(db, g, detail=False) for g in q.order_by(Generation.id.desc()).limit(200)]


@router.get("/history")
def history(db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = db.query(PublicationHistory).order_by(PublicationHistory.id.desc()).limit(200).all()
    return [{"id": r.id, "generation_id": r.generation_id, "generation_name": r.generation_name, "action": r.action,
             "user_id": r.user_id, "note": r.note, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/{gen_id}")
def get_timetable(gen_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    gen = svc.get_generation(db, gen_id)
    if user.role != "admin" and gen.status != "published":
        raise HTTPException(403, "Only published timetables are visible to faculty")
    return svc.serialize_generation(db, gen)


@router.delete("/{gen_id}", status_code=204)
def delete_timetable(gen_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    gen = svc.get_generation(db, gen_id)
    if gen.status == "published":
        raise HTTPException(409, "Unpublish the timetable before deleting it.")
    db.delete(gen)
    db.commit()


@router.post("/{gen_id}/save-draft")
def save_draft(gen_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    gen = svc.get_generation(db, gen_id)
    if gen.status not in ("preview", "draft"):
        raise HTTPException(409, f"Cannot save a '{gen.status}' timetable as a draft.")
    gen.status = "draft"
    svc.log_history(db, gen, "saved_draft", user.id)
    db.commit()
    return svc.serialize_generation(db, gen, detail=False)


@router.post("/{gen_id}/publish")
def publish(gen_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    gen = svc.publish(db, user.id, gen_id)
    return svc.serialize_generation(db, gen, detail=False)


@router.post("/{gen_id}/unpublish")
def unpublish(gen_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    gen = svc.get_generation(db, gen_id, lock=True)
    if gen.status != "published":
        raise HTTPException(409, "Timetable is not published")
    gen.status = "draft"
    gen.published_at = None
    svc.log_history(db, gen, "unpublished", user.id)
    db.commit()
    return svc.serialize_generation(db, gen, detail=False)


@router.post("/{gen_id}/move")
def move(gen_id: int, data: MoveIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    gen = svc.get_generation(db, gen_id, lock=not data.dry_run)
    return svc.move_session(db, user.id, gen, data.session_id, data.day, data.start_period, data.room_id, data.dry_run)


@router.get("/{gen_id}/validate")
def validate(gen_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    gen = svc.get_generation(db, gen_id)
    v = svc.validate_generation(db, gen)
    return {"ok": not v and not gen.report.get("unscheduled"), "violations": [x.as_dict() for x in v],
            "unscheduled": gen.report.get("unscheduled", [])}


@router.get("/{gen_id}/export")
def export(gen_id: int, format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
           view: str = Query("batch", pattern="^(batch|faculty|room|department)$"),
           entity_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    gen = svc.get_generation(db, gen_id)
    if user.role != "admin" and gen.status != "published":
        raise HTTPException(403, "Only published timetables can be exported by faculty")
    data = svc.serialize_generation(db, gen)
    if not data["sessions"]:
        raise HTTPException(409, "This timetable has no scheduled sessions to export.")
    if format == "pdf":
        body, mime = render_pdf(data, view, entity_id), "application/pdf"
    else:
        body, mime = render_xlsx(data, view, entity_id), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=body, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="timetable-{gen_id}-{view}.{format}"'})
