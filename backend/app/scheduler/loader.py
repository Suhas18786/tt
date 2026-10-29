"""Database -> ProblemContext."""
from __future__ import annotations

import copy

from sqlalchemy.orm import Session

from ..models import (Batch, Classroom, Faculty, FacultyAvailability, Generation, RoomBlockedSlot,
                      ScheduledSession, Subject, TeachingAssignment, TimetableConfig)
from .context import (DEFAULT_PERIODS, DEFAULT_WEIGHTS, AssignmentCtx, BatchCtx, FacultyCtx,
                      Period, ProblemContext, RoomCtx)


def default_config() -> dict:
    return {
        "working_days": [0, 1, 2, 3, 4],
        "periods": copy.deepcopy(DEFAULT_PERIODS),
        "blocked_slots": [],
        "weights": dict(DEFAULT_WEIGHTS),
        "max_consecutive": 3,
        "time_limit_seconds": 30,
        "max_daily_hours_override": None,
    }


def get_saved_config(db: Session) -> dict:
    row = db.query(TimetableConfig).order_by(TimetableConfig.id).first()
    cfg = default_config()
    if row:
        cfg.update({
            "working_days": row.working_days, "periods": row.periods, "blocked_slots": row.blocked_slots or [],
            "weights": {**DEFAULT_WEIGHTS, **(row.weights or {})}, "max_consecutive": row.max_consecutive,
            "time_limit_seconds": row.time_limit_seconds, "max_daily_hours_override": row.max_daily_hours_override,
        })
    return cfg


def merge_config(base: dict, overrides: dict | None) -> dict:
    cfg = copy.deepcopy(base)
    for k, v in (overrides or {}).items():
        if v is None:
            continue
        if k == "weights":
            cfg["weights"] = {**cfg["weights"], **v}
        else:
            cfg[k] = v
    return cfg


def build_context(db: Session, batch_ids: list, config: dict, assignment_ids: list | None = None,
                  exclude_generation_id: int | None = None) -> ProblemContext:
    q = (db.query(TeachingAssignment, Subject)
         .join(Subject, Subject.id == TeachingAssignment.subject_id)
         .filter(TeachingAssignment.batch_id.in_(batch_ids)))
    if assignment_ids:
        q = q.filter(TeachingAssignment.id.in_(assignment_ids))
    rows = q.order_by(TeachingAssignment.id).all()

    assignments = []
    for ta, sub in rows:
        assignments.append(AssignmentCtx(
            id=ta.id, batch_id=ta.batch_id, subject_id=sub.id, subject_code=sub.code, subject_name=sub.name,
            faculty_id=ta.faculty_id, weekly_hours=sub.weekly_hours,
            session_duration=sub.session_duration if sub.consecutive_required else 1,
            room_type=sub.room_type, equipment=frozenset(sub.required_equipment or []),
            difficulty=sub.difficulty, subject_type=sub.subject_type,
            consecutive_required=sub.consecutive_required))

    fac_ids = {a.faculty_id for a in assignments}
    faculty = {}
    for f in db.query(Faculty).filter(Faculty.id.in_(fac_ids)).all() if fac_ids else []:
        faculty[f.id] = FacultyCtx(id=f.id, name=f.full_name, max_per_day=f.max_hours_per_day,
                                   max_per_week=f.max_hours_per_week)
    if fac_ids:
        for av in db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id.in_(fac_ids)).all():
            tgt = faculty[av.faculty_id]
            (tgt.unavailable if av.status == "unavailable" else tgt.preferred).add((av.day, av.period))

    batches = {b.id: BatchCtx(id=b.id, code=b.code, strength=b.strength, department_id=b.department_id)
               for b in db.query(Batch).filter(Batch.id.in_(batch_ids)).all()}

    rooms = {c.id: RoomCtx(id=c.id, label=f"{c.building}-{c.room_number}", room_type=c.room_type,
                           capacity=c.capacity, equipment=frozenset(c.equipment or []))
             for c in db.query(Classroom).all()}
    for rb in db.query(RoomBlockedSlot).all():
        if rb.classroom_id in rooms:
            rooms[rb.classroom_id].blocked.add((rb.day, rb.period))

    # Faculty/rooms already committed in *other* published timetables are fixed obstacles.
    ext_fac, ext_room = set(), set()
    batch_set = set(batch_ids)
    pubs = db.query(Generation).filter(Generation.status == "published").all()
    for g in pubs:
        if g.id == exclude_generation_id or batch_set & set(g.batch_ids or []):
            continue
        for s in db.query(ScheduledSession).filter(ScheduledSession.generation_id == g.id).all():
            for p in range(s.start_period, s.start_period + s.duration):
                ext_fac.add((s.faculty_id, s.day, p))
                ext_room.add((s.room_id, s.day, p))

    # An assignment may reference faculty that no longer exists -> cannot happen (FK), but be safe.
    return ProblemContext(
        working_days=sorted(config["working_days"]),
        periods=[Period(p["index"], p["start"], p["end"], p.get("kind", "class")) for p in config["periods"]],
        blocked={(d, p) for d, p in config.get("blocked_slots", [])},
        faculty=faculty, batches=batches, rooms=rooms, assignments=assignments,
        external_faculty_busy=ext_fac, external_room_busy=ext_room,
        weights={**DEFAULT_WEIGHTS, **config.get("weights", {})},
        max_consecutive=int(config.get("max_consecutive", 3)),
        time_limit=int(config.get("time_limit_seconds", 30)),
        max_daily_override=config.get("max_daily_hours_override"),
    )
