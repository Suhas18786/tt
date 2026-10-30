"""Hard-constraint validator (pure Python).

Used for: (1) verifying every solver result, (2) validating manual edits / drag-and-drop,
(3) the publish gate, (4) dashboard conflict detection, (5) tests.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .context import Placement, ProblemContext


@dataclass
class Violation:
    code: str
    message: str
    session_ids: list = field(default_factory=list)

    def as_dict(self):
        return {"code": self.code, "message": self.message, "session_ids": list(self.session_ids)}


def validate_placements(ctx: ProblemContext, placements: list, require_complete: bool = True) -> list:
    v: list[Violation] = []
    amap = ctx.assignment_by_id()
    pmap = ctx.period_by_index()

    fac_slots, batch_slots, room_slots = defaultdict(list), defaultdict(list), defaultdict(list)
    fac_day = defaultdict(int)
    fac_week = defaultdict(int)
    covered = defaultdict(int)

    for pl in placements:
        a = amap.get(pl.assignment_id)
        fac = ctx.faculty.get(pl.faculty_id)
        room = ctx.rooms.get(pl.room_id)
        batch = ctx.batches.get(pl.batch_id)
        if a is None or fac is None or room is None or batch is None:
            v.append(Violation("unknown_entity", "Session references an unknown assignment, faculty, room or batch.", [pl.id]))
            continue
        if a.faculty_id != pl.faculty_id or a.batch_id != pl.batch_id:
            v.append(Violation("assignment_mismatch", f"{a.subject_code}: faculty/batch differ from the teaching assignment.", [pl.id]))
        covered[a.id] += pl.duration

        if pl.day not in ctx.working_days:
            v.append(Violation("outside_working_days", f"{a.subject_code}: day {pl.day} is not a working day.", [pl.id]))
            continue
        # contiguous class periods inside working hours
        for p in pl.periods():
            pm = pmap.get(p)
            if pm is None:
                v.append(Violation("outside_hours", f"{a.subject_code}: period {p + 1} is outside working hours.", [pl.id]))
            elif pm.kind != "class":
                v.append(Violation("break_period", f"{a.subject_code}: {ctx.slot_label(pl.day, p)} is a {pm.kind} period.", [pl.id]))
            elif (pl.day, p) in ctx.blocked:
                v.append(Violation("blocked_period", f"{a.subject_code}: {ctx.slot_label(pl.day, p)} is blocked.", [pl.id]))
            if (pl.day, p) in fac.unavailable:
                v.append(Violation("faculty_unavailable", f"{fac.name} is unavailable {ctx.slot_label(pl.day, p)}.", [pl.id]))
            if (pl.faculty_id, pl.day, p) in ctx.external_faculty_busy:
                v.append(Violation("faculty_external_conflict", f"{fac.name} already teaches {ctx.slot_label(pl.day, p)} in another saved timetable.", [pl.id]))
            if (pl.day, p) in room.blocked:
                v.append(Violation("room_unavailable", f"Room {room.label} is unavailable {ctx.slot_label(pl.day, p)}.", [pl.id]))
            if (pl.room_id, pl.day, p) in ctx.external_room_busy:
                v.append(Violation("room_external_conflict", f"Room {room.label} is already used {ctx.slot_label(pl.day, p)} in another saved timetable.", [pl.id]))
            fac_slots[(pl.faculty_id, pl.day, p)].append(pl.id)
            batch_slots[(pl.batch_id, pl.day, p)].append(pl.id)
            room_slots[(pl.room_id, pl.day, p)].append(pl.id)
            fac_day[(pl.faculty_id, pl.day)] += 1
            fac_week[pl.faculty_id] += 1

        if room.room_type != a.room_type:
            v.append(Violation("room_type", f"{a.subject_code} needs a {a.room_type} but {room.label} is a {room.room_type}.", [pl.id]))
        if room.capacity < batch.strength:
            v.append(Violation("room_capacity", f"Room {room.label} seats {room.capacity} but batch {batch.code} has {batch.strength} students.", [pl.id]))
        if not a.equipment <= room.equipment:
            miss = sorted(a.equipment - room.equipment)
            v.append(Violation("room_equipment", f"Room {room.label} lacks required equipment: {', '.join(miss)}.", [pl.id]))

    for (kind, slots, who) in (("faculty", fac_slots, lambda k: ctx.faculty[k[0]].name),
                               ("batch", batch_slots, lambda k: f"Batch {ctx.batches[k[0]].code}"),
                               ("room", room_slots, lambda k: f"Room {ctx.rooms[k[0]].label}")):
        for key, ids in slots.items():
            if len(set(ids)) > 1:
                v.append(Violation(f"{kind}_conflict", f"{who(key)} has {len(set(ids))} classes at {ctx.slot_label(key[1], key[2])}.", sorted(set(ids), key=str)))

    for (fid, d), n in fac_day.items():
        cap = ctx.faculty_daily_cap(fid)
        total = n + ctx.external_load(fid, d)
        if total > cap:
            v.append(Violation("faculty_daily_limit", f"{ctx.faculty[fid].name} teaches {total} periods on {ctx.slot_label(d, 0).split(' period')[0]} (limit {cap}).",
                               [pl.id for pl in placements if pl.faculty_id == fid and pl.day == d]))
    for fid, n in fac_week.items():
        total = n + ctx.external_week_load(fid)
        if total > ctx.faculty[fid].max_per_week:
            v.append(Violation("faculty_weekly_limit", f"{ctx.faculty[fid].name} teaches {total} periods/week (limit {ctx.faculty[fid].max_per_week}).",
                               [pl.id for pl in placements if pl.faculty_id == fid]))

    if require_complete:
        for a in ctx.assignments:
            got = covered.get(a.id, 0)
            if got != a.weekly_hours:
                v.append(Violation("weekly_hours", f"{a.subject_code} ({ctx.batches[a.batch_id].code}) has {got} of {a.weekly_hours} required weekly periods.", []))
    else:
        for a in ctx.assignments:
            if covered.get(a.id, 0) > a.weekly_hours:
                v.append(Violation("weekly_hours", f"{a.subject_code} has more periods than required.", []))
    return v
