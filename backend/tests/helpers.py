"""Build in-memory problem contexts (no database needed)."""
from app import seed_data as sd
from app.scheduler.context import (DEFAULT_PERIODS, DEFAULT_WEIGHTS, AssignmentCtx, BatchCtx, FacultyCtx,
                                   Period, ProblemContext, RoomCtx)


def ctx_from_seed(batch_codes=None, time_limit=20, **overrides) -> ProblemContext:
    fac_ids = {f[0]: i + 1 for i, f in enumerate(sd.FACULTY)}
    sub = {s[0]: (i + 1, s) for i, s in enumerate(sd.SUBJECTS)}
    bat_ids = {b[0]: i + 1 for i, b in enumerate(sd.BATCHES)}
    dept_ids = {d[0]: i + 1 for i, d in enumerate(sd.DEPARTMENTS)}

    faculty = {}
    for code, name, _dept, per_day, per_week in sd.FACULTY:
        f = FacultyCtx(id=fac_ids[code], name=name, max_per_day=per_day, max_per_week=per_week)
        f.unavailable = set(sd.UNAVAILABLE.get(code, []))
        f.preferred = set(sd.PREFERRED.get(code, []))
        faculty[f.id] = f
    batches = {bat_ids[b[0]]: BatchCtx(id=bat_ids[b[0]], code=b[0], strength=b[5], department_id=dept_ids[b[2]])
               for b in sd.BATCHES if not batch_codes or b[0] in batch_codes}
    rooms = {i + 1: RoomCtx(id=i + 1, label=f"{r[0]}-{r[1]}", room_type=r[2], capacity=r[3], equipment=frozenset(r[4]))
             for i, r in enumerate(sd.ROOMS)}
    assignments = []
    for n, (bcode, scode, fcode) in enumerate(sd.ASSIGNMENTS, start=1):
        if batch_codes and bcode not in batch_codes:
            continue
        sid, s = sub[scode]
        _code, name, _d, _sem, typ, hours, dur, rtype, consec, diff, equip = s
        assignments.append(AssignmentCtx(
            id=n, batch_id=bat_ids[bcode], subject_id=sid, subject_code=scode, subject_name=name,
            faculty_id=fac_ids[fcode], weekly_hours=hours, session_duration=dur if consec else 1,
            room_type=rtype, equipment=frozenset(equip), difficulty=diff, subject_type=typ,
            consecutive_required=consec))
    ctx = ProblemContext(
        working_days=[0, 1, 2, 3, 4], periods=[Period(**p) for p in DEFAULT_PERIODS], blocked=set(),
        faculty=faculty, batches=batches, rooms=rooms, assignments=assignments,
        weights=dict(DEFAULT_WEIGHTS), time_limit=time_limit)
    for k, v in overrides.items():
        setattr(ctx, k, v)
    return ctx


def tiny_ctx(**kw) -> ProblemContext:
    """1 batch, 2 faculty, 2 rooms, 3 days x 3 class periods - easy to reason about."""
    periods = [Period(0, "09:00", "10:00"), Period(1, "10:00", "11:00"), Period(2, "11:00", "12:00")]
    ctx = ProblemContext(
        working_days=[0, 1, 2], periods=periods, blocked=set(),
        faculty={1: FacultyCtx(1, "Alice", 3, 10), 2: FacultyCtx(2, "Bob", 3, 10)},
        batches={1: BatchCtx(1, "B1", 30), 2: BatchCtx(2, "B2", 30)},
        rooms={1: RoomCtx(1, "R1", "lecture_room", 40), 2: RoomCtx(2, "R2", "lecture_room", 40),
               3: RoomCtx(3, "LAB", "computer_lab", 40, frozenset({"computers"}))},
        assignments=[], time_limit=10)
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx
