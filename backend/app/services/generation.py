"""Generation orchestration: run solver, persist, serialise, validate, move, publish."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (Batch, Classroom, Department, Faculty, Generation, PublicationHistory, ScheduledSession,
                      Semester, Subject, TeachingAssignment)
from ..scheduler import engine
from ..scheduler.candidates import build_sessions
from ..scheduler.context import Placement, ProblemContext
from ..scheduler.loader import build_context, get_saved_config, merge_config
from ..scheduler.validator import validate_placements


def log_history(db: Session, gen: Generation, action: str, user_id, note: str = ""):
    db.add(PublicationHistory(generation_id=gen.id, generation_name=gen.name, action=action,
                              user_id=user_id, note=note))


# ------------------------------------------------------------------------------ generate
def resolve_scope(db: Session, req: dict) -> list:
    q = db.query(Batch)
    if req.get("batch_ids"):
        q = q.filter(Batch.id.in_(req["batch_ids"]))
    if req.get("semester_id"):
        q = q.filter(Batch.semester_id == req["semester_id"])
    if req.get("department_id"):
        q = q.filter(Batch.department_id == req["department_id"])
    ids = [b.id for b in q.order_by(Batch.id).all()]
    if not ids:
        raise HTTPException(422, "No student batches match the selected scope.")
    return ids


def run_generation(db: Session, user_id: int, req: dict) -> Generation:
    batch_ids = resolve_scope(db, req)
    base = get_saved_config(db)
    overrides = {k: req.get(k) for k in ("working_days", "periods", "blocked_slots", "weights", "max_consecutive",
                                          "time_limit_seconds", "max_daily_hours_override")}
    if overrides.get("periods"):
        overrides["periods"] = [dict(p) for p in overrides["periods"]]
    config = merge_config(base, overrides)
    assignment_ids = req.get("assignment_ids") or None
    ctx = build_context(db, batch_ids, config, assignment_ids)
    if not ctx.assignments:
        raise HTTPException(422, "The selected batches have no subject/faculty assignments to schedule.")

    sessions, _ = build_sessions(ctx)
    result = engine.solve(ctx)

    if result.status == "no_solution":
        status = "infeasible"
    else:
        status = "preview" if result.status == "complete" else "infeasible"

    stored_cfg = dict(config)
    stored_cfg["assignment_ids"] = [a.id for a in ctx.assignments]
    gen = Generation(
        name=req.get("name") or "Timetable", status=status, semester_id=req.get("semester_id"),
        department_id=req.get("department_id"), batch_ids=batch_ids, config=stored_cfg,
        solver_status=result.solver_status, objective=result.objective, solve_seconds=round(result.seconds, 3),
        report={"complete": result.status == "complete", "issues": result.issues,
                "unscheduled": result.unscheduled, "stats": result.stats,
                "expected_sessions": len(sessions)},
        created_by=user_id)
    try:
        db.add(gen)
        db.flush()
        for pl in result.placements:
            a = next(x for x in ctx.assignments if x.id == pl.assignment_id)
            db.add(ScheduledSession(generation_id=gen.id, assignment_id=a.id, batch_id=a.batch_id,
                                    subject_id=a.subject_id, faculty_id=a.faculty_id, room_id=pl.room_id,
                                    day=pl.day, start_period=pl.start, duration=pl.duration, session_no=pl.id))
        rid = req.get("replace_generation_id")
        if rid:
            old = db.get(Generation, rid)
            if old and old.status in ("preview", "infeasible", "draft"):
                db.delete(old)
        log_history(db, gen, "generated", user_id, f"{result.status}; {len(result.placements)} sessions placed")
        db.commit()  # all-or-nothing: generation + sessions + history
    except Exception:
        db.rollback()
        raise
    return gen


# ------------------------------------------------------------------------------ helpers
def generation_context(db: Session, gen: Generation) -> ProblemContext:
    return build_context(db, gen.batch_ids, gen.config, gen.config.get("assignment_ids"), exclude_generation_id=gen.id)


def placements_of(sessions) -> list:
    return [Placement(id=s.id, assignment_id=s.assignment_id, batch_id=s.batch_id, faculty_id=s.faculty_id,
                      room_id=s.room_id, day=s.day, start=s.start_period, duration=s.duration) for s in sessions]


def load_sessions(db: Session, gen_id: int) -> list:
    return db.query(ScheduledSession).filter(ScheduledSession.generation_id == gen_id).order_by(ScheduledSession.id).all()


def validate_generation(db: Session, gen: Generation) -> list:
    ctx = generation_context(db, gen)
    complete = not gen.report.get("unscheduled") and gen.status != "infeasible"
    return validate_placements(ctx, placements_of(load_sessions(db, gen.id)), require_complete=complete)


def serialize_sessions(db: Session, sessions: list) -> list:
    if not sessions:
        return []
    subs = {s.id: s for s in db.query(Subject).filter(Subject.id.in_({x.subject_id for x in sessions}))}
    facs = {f.id: f for f in db.query(Faculty).filter(Faculty.id.in_({x.faculty_id for x in sessions}))}
    rooms = {r.id: r for r in db.query(Classroom).filter(Classroom.id.in_({x.room_id for x in sessions}))}
    bats = {b.id: b for b in db.query(Batch).filter(Batch.id.in_({x.batch_id for x in sessions}))}
    depts = {d.id: d.code for d in db.query(Department)}
    out = []
    for s in sessions:
        sub, fac, room, b = subs[s.subject_id], facs[s.faculty_id], rooms[s.room_id], bats[s.batch_id]
        out.append({
            "id": s.id, "assignment_id": s.assignment_id, "batch_id": b.id, "batch_code": b.code,
            "department_id": b.department_id, "department_code": depts.get(b.department_id, ""),
            "semester_id": b.semester_id,
            "subject_id": sub.id, "subject_code": sub.code, "subject_name": sub.name, "subject_type": sub.subject_type,
            "faculty_id": fac.id, "faculty_name": fac.full_name, "room_id": room.id,
            "room_label": f"{room.building}-{room.room_number}", "room_type": room.room_type,
            "day": s.day, "start_period": s.start_period, "duration": s.duration,
        })
    return out


def workload_rows(db: Session, sessions: list) -> list:
    by_fac = defaultdict(int)
    for s in sessions:
        by_fac[s["faculty_id"]] += s["duration"]
    facs = {f.id: f for f in db.query(Faculty).filter(Faculty.id.in_(list(by_fac) or [0]))}
    return sorted(({"faculty_id": f, "faculty_name": facs[f].full_name, "hours": h,
                    "max_hours_per_week": facs[f].max_hours_per_week} for f, h in by_fac.items()),
                  key=lambda r: -r["hours"])


def serialize_generation(db: Session, gen: Generation, detail: bool = True) -> dict:
    out = {
        "id": gen.id, "name": gen.name, "status": gen.status, "semester_id": gen.semester_id,
        "department_id": gen.department_id, "batch_ids": gen.batch_ids, "solver_status": gen.solver_status,
        "objective": gen.objective, "solve_seconds": gen.solve_seconds,
        "created_at": gen.created_at.isoformat() if gen.created_at else None,
        "published_at": gen.published_at.isoformat() if gen.published_at else None,
        "unscheduled_count": len(gen.report.get("unscheduled", [])),
        "expected_sessions": gen.report.get("expected_sessions", 0),
    }
    if detail:
        sessions = serialize_sessions(db, load_sessions(db, gen.id))
        violations = validate_generation(db, gen)
        out.update({
            "config": {"working_days": gen.config["working_days"], "periods": gen.config["periods"],
                       "blocked_slots": gen.config.get("blocked_slots", [])},
            "report": gen.report, "sessions": sessions, "workload": workload_rows(db, sessions),
            "validation": {"ok": not violations and not gen.report.get("unscheduled"),
                           "violations": [v.as_dict() for v in violations],
                           "unscheduled": len(gen.report.get("unscheduled", []))},
        })
    return out


def get_generation(db: Session, gen_id: int, lock: bool = False) -> Generation:
    q = db.query(Generation).filter(Generation.id == gen_id)
    if lock:
        q = q.with_for_update()
    gen = q.first()
    if gen is None:
        raise HTTPException(404, "Timetable not found")
    return gen


# ------------------------------------------------------------------------------ manual edit
def move_session(db: Session, user_id: int, gen: Generation, session_id: int, day: int, start: int,
                 room_id: int | None, dry_run: bool) -> dict:
    if gen.status not in ("preview", "draft", "infeasible"):
        raise HTTPException(409, "Published or archived timetables are read-only. Unpublish/regenerate first.")
    sessions = load_sessions(db, gen.id)
    target = next((s for s in sessions if s.id == session_id), None)
    if target is None:
        raise HTTPException(404, "Session not found in this timetable")
    ctx = generation_context(db, gen)
    new_room = room_id or target.room_id
    placements = []
    for pl in placements_of(sessions):
        if pl.id == session_id:
            pl = Placement(id=pl.id, assignment_id=pl.assignment_id, batch_id=pl.batch_id, faculty_id=pl.faculty_id,
                           room_id=new_room, day=day, start=start, duration=pl.duration)
        placements.append(pl)
    complete = not gen.report.get("unscheduled")
    violations = validate_placements(ctx, placements, require_complete=complete)
    if violations:
        raise HTTPException(422, detail={"message": "The move violates scheduling constraints.",
                                         "violations": [v.as_dict() for v in violations]})
    if not dry_run:
        old = (target.day, target.start_period, target.room_id)
        target.day, target.start_period, target.room_id = day, start, new_room
        log_history(db, gen, "edited", user_id, f"session {session_id}: {old} -> {(day, start, new_room)}")
        db.commit()
    return {"ok": True, "dry_run": dry_run}


# ------------------------------------------------------------------------------ publish
def publish(db: Session, user_id: int, gen_id: int) -> Generation:
    gen = get_generation(db, gen_id, lock=True)
    if gen.status not in ("preview", "draft"):
        raise HTTPException(409, f"A timetable with status '{gen.status}' cannot be published.")
    if gen.report.get("unscheduled") or not gen.report.get("complete", False):
        raise HTTPException(422, "All required classes must be scheduled before publishing.")
    violations = validate_generation(db, gen)
    if violations:
        raise HTTPException(422, detail={"message": "Timetable has hard-constraint violations.",
                                         "violations": [v.as_dict() for v in violations]})
    mine = set(gen.batch_ids)
    others = db.query(Generation).filter(Generation.status == "published", Generation.id != gen.id).with_for_update().all()
    for o in others:
        if mine & set(o.batch_ids):
            o.status = "archived"
            log_history(db, o, "archived", user_id, f"superseded by '{gen.name}'")
    gen.status = "published"
    gen.published_at = datetime.now(timezone.utc)
    log_history(db, gen, "published", user_id)
    db.commit()
    return gen
