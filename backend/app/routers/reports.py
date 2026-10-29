from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Batch, Classroom, ConflictReport, Faculty, Generation, Subject
from ..services import generation as svc
from ..services.exports import group_sessions

router = APIRouter(tags=["reports"])


def pick_generation(db: Session, gen_id: int | None) -> Generation | None:
    if gen_id:
        return svc.get_generation(db, gen_id)
    for status in ("published", "draft", "preview", "infeasible"):
        g = db.query(Generation).filter(Generation.status == status).order_by(Generation.id.desc()).first()
        if g:
            return g
    return None


@router.get("/dashboard")
def dashboard(generation_id: int | None = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    room_types = dict(db.query(Classroom.room_type, func.count()).group_by(Classroom.room_type).all())
    out = {
        "counts": {
            "faculty": db.query(Faculty).count(), "subjects": db.query(Subject).count(),
            "batches": db.query(Batch).count(),
            "classrooms": room_types.get("lecture_room", 0),
            "laboratories": room_types.get("computer_lab", 0) + room_types.get("laboratory", 0),
        },
        "open_conflict_reports": db.query(ConflictReport).filter(ConflictReport.status == "open").count(),
        "generation": None, "sessions": {"scheduled": 0, "unscheduled": 0, "expected": 0},
        "workload": [], "room_utilization": [], "conflicts": [], "issues": [],
        "status_counts": dict(db.query(Generation.status, func.count()).group_by(Generation.status).all()),
    }
    gen = pick_generation(db, generation_id)
    if gen is None:
        return out
    data = svc.serialize_generation(db, gen)
    out["generation"] = {k: data[k] for k in ("id", "name", "status", "solver_status", "solve_seconds", "created_at", "published_at")}
    sched = len(data["sessions"])
    unsched = data["report"].get("unscheduled", [])
    out["sessions"] = {"scheduled": sched, "unscheduled": len(unsched), "expected": data["report"].get("expected_sessions", sched)}
    out["workload"] = data["workload"]
    out["conflicts"] = data["validation"]["violations"]
    out["issues"] = [i for i in data["report"].get("issues", []) if i.get("severity") in ("error", "warning")]
    cfg = data["config"]
    slots = len(cfg["working_days"]) * sum(1 for p in cfg["periods"] if p.get("kind", "class") == "class")
    used = defaultdict(int)
    labels = {}
    for s in data["sessions"]:
        used[s["room_id"]] += s["duration"]
        labels[s["room_id"]] = s["room_label"]
    out["room_utilization"] = sorted(({"room_id": r, "room": labels[r], "used": u, "capacity": slots,
                                       "percent": round(100 * u / slots, 1) if slots else 0} for r, u in used.items()),
                                     key=lambda x: -x["percent"])
    return out


@router.get("/reports/{kind}")
def report(kind: str, generation_id: int | None = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    gen = pick_generation(db, generation_id)
    if gen is None:
        raise HTTPException(404, "No timetable has been generated yet.")
    data = svc.serialize_generation(db, gen)
    base = {"kind": kind, "generation": {"id": gen.id, "name": gen.name, "status": gen.status, "config": data["config"]}}
    if kind in ("faculty", "batch", "room", "department"):
        groups = group_sessions(data["sessions"], kind)
        base["groups"] = [{"id": gid, "title": title, "sessions": sess} for gid, title, sess in groups]
        return base
    if kind == "workload":
        per_day = defaultdict(lambda: defaultdict(int))
        for s in data["sessions"]:
            per_day[s["faculty_id"]][s["day"]] += s["duration"]
        base["rows"] = [{**w, "per_day": dict(per_day[w["faculty_id"]])} for w in data["workload"]]
        return base
    if kind == "unscheduled":
        base["unscheduled"] = data["report"].get("unscheduled", [])
        base["violations"] = data["validation"]["violations"]
        base["issues"] = data["report"].get("issues", [])
        return base
    raise HTTPException(404, "Unknown report type")
