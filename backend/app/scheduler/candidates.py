"""Candidate generation + static feasibility diagnostics (pure Python)."""
from __future__ import annotations

from collections import defaultdict

from .context import ProblemContext, SessionReq


def build_sessions(ctx: ProblemContext):
    """Split every assignment's weekly hours into session blocks.

    weekly_hours=4, duration=2 -> two 2-period sessions.
    weekly_hours=3, duration=2 -> one 2-period and one 1-period session (+ warning).
    Returns (sessions, issues).
    """
    sessions, issues = [], []
    key = 0
    for a in ctx.assignments:
        full, rem = divmod(a.weekly_hours, a.session_duration)
        blocks = [a.session_duration] * full + ([rem] if rem else [])
        if rem:
            issues.append({
                "severity": "warning", "code": "hours_not_multiple",
                "message": (f"{a.subject_code}: weekly hours ({a.weekly_hours}) is not a multiple of the session "
                            f"duration ({a.session_duration}); the last session is {rem} period(s) long."),
            })
        for n, dur in enumerate(blocks):
            sessions.append(SessionReq(key=key, assignment=a, number=n, duration=dur))
            key += 1
    return sessions, issues


def eligible_rooms(ctx: ProblemContext, a) -> list:
    batch = ctx.batches[a.batch_id]
    return [r for r in ctx.rooms.values()
            if r.room_type == a.room_type and r.capacity >= batch.strength and a.equipment <= r.equipment]


def time_options(ctx: ProblemContext, s: SessionReq) -> list:
    """All (day, start) where the faculty can teach a block of s.duration periods."""
    fac = ctx.faculty[s.faculty_id]
    out = []
    for d in ctx.working_days:
        for p0 in ctx.class_periods:
            periods = range(p0, p0 + s.duration)
            if all(ctx.slot_is_class(d, p) and (d, p) not in fac.unavailable
                   and (fac.id, d, p) not in ctx.external_faculty_busy for p in periods):
                out.append((d, p0))
    return out


def candidate_placements(ctx: ProblemContext, s: SessionReq) -> list:
    """All (day, start, room_id) placements that satisfy the *unary* hard constraints."""
    rooms = eligible_rooms(ctx, s.assignment)
    out = []
    for d, p0 in time_options(ctx, s):
        for r in rooms:
            if all((d, p) not in r.blocked and (r.id, d, p) not in ctx.external_room_busy
                   for p in range(p0, p0 + s.duration)):
                out.append((d, p0, r.id))
    return out


def static_diagnostics(ctx: ProblemContext, sessions) -> list:
    """Cheap necessary-condition checks that explain most infeasibilities."""
    issues = []
    n_class = len(ctx.class_periods)
    week_slots = len(ctx.working_days) * n_class

    fac_load, batch_load, room_type_load = defaultdict(int), defaultdict(int), defaultdict(int)
    for s in sessions:
        fac_load[s.faculty_id] += s.duration
        batch_load[s.batch_id] += s.duration
        room_type_load[s.assignment.room_type] += s.duration

    for fid, load in fac_load.items():
        f = ctx.faculty[fid]
        week_cap = f.max_per_week - ctx.external_week_load(fid)
        if load > week_cap:
            issues.append({"severity": "error", "code": "faculty_weekly_limit", "faculty_id": fid,
                           "message": f"{f.name} is assigned {load} periods/week but can teach at most {week_cap}."})
        avail = 0
        day_cap_total = 0
        for d in ctx.working_days:
            free = [p for p in ctx.class_periods if ctx.slot_is_class(d, p) and (d, p) not in f.unavailable
                    and (fid, d, p) not in ctx.external_faculty_busy]
            avail += len(free)
            day_cap_total += min(len(free), max(0, ctx.faculty_daily_cap(fid) - ctx.external_load(fid, d)))
        if load > day_cap_total:
            issues.append({"severity": "error", "code": "faculty_capacity", "faculty_id": fid,
                           "message": (f"{f.name} needs {load} periods/week but availability and the daily limit "
                                       f"({ctx.faculty_daily_cap(fid)}/day) only allow {day_cap_total}.")})
        elif load > 0.9 * day_cap_total:
            issues.append({"severity": "warning", "code": "faculty_tight", "faculty_id": fid,
                           "message": f"{f.name} is at {load}/{day_cap_total} of available capacity - very tight."})

    for bid, load in batch_load.items():
        if load > week_slots:
            issues.append({"severity": "error", "code": "batch_capacity", "batch_id": bid,
                           "message": f"Batch {ctx.batches[bid].code} needs {load} periods/week but only {week_slots} exist."})

    rooms_by_type = defaultdict(list)
    for r in ctx.rooms.values():
        rooms_by_type[r.room_type].append(r)
    for rtype, load in room_type_load.items():
        cap = sum(week_slots - len(r.blocked) for r in rooms_by_type.get(rtype, []))
        if not rooms_by_type.get(rtype):
            issues.append({"severity": "error", "code": "no_room_type", "room_type": rtype,
                           "message": f"No classroom of type '{rtype}' exists but {load} periods/week need one."})
        elif load > cap:
            issues.append({"severity": "error", "code": "room_capacity", "room_type": rtype,
                           "message": f"'{rtype}' rooms offer {cap} periods/week but {load} are required."})

    for s in sessions:
        a = s.assignment
        if s.number > 0:
            continue
        rooms = eligible_rooms(ctx, a)
        if not rooms:
            b = ctx.batches[a.batch_id]
            extra = f" with equipment {sorted(a.equipment)}" if a.equipment else ""
            issues.append({"severity": "error", "code": "no_eligible_room", "assignment_id": a.id,
                           "message": (f"{a.subject_code} ({b.code}): no '{a.room_type}' room with capacity >= "
                                       f"{b.strength}{extra}.")})
        if not time_options(ctx, s):
            issues.append({"severity": "error", "code": "no_time_option", "assignment_id": a.id,
                           "message": (f"{a.subject_code} ({ctx.batches[a.batch_id].code}): "
                                       f"{ctx.faculty[a.faculty_id].name} has no slot where a {s.duration}-period "
                                       f"block fits (availability, breaks or blocked periods).")})
    return issues


def explain_unscheduled(ctx: ProblemContext, s: SessionReq, issues: list) -> str:
    """Human-readable reason why a session could not be placed."""
    a = s.assignment
    f = ctx.faculty[a.faculty_id]
    b = ctx.batches[a.batch_id]
    if not eligible_rooms(ctx, a):
        return f"No '{a.room_type}' room with capacity >= {b.strength} and the required equipment exists."
    if not time_options(ctx, s):
        return f"{f.name} has no free {s.duration}-period block (availability, breaks, blocked periods)."
    if not candidate_placements(ctx, s):
        return "Eligible rooms are blocked or already used by other saved timetables in every slot the faculty can teach."
    related = [i["message"] for i in issues if i.get("severity") == "error" and (
        i.get("faculty_id") == f.id or i.get("batch_id") == b.id
        or i.get("room_type") == a.room_type or i.get("assignment_id") == a.id)]
    if related:
        return "Over-constrained: " + " ".join(related[:2])
    return ("No conflict-free combination of faculty, batch and room slots remains. Relax faculty availability, "
            "raise the daily limit, or add rooms/periods.")
