"""Hard-constraint validator (pure Python - needs no database or solver)."""
from app.scheduler.context import AssignmentCtx, Placement
from app.scheduler.validator import validate_placements

from .helpers import tiny_ctx


def asg(id_, batch, fac, hours=1, room_type="lecture_room", equip=frozenset(), dur=1, consec=False):
    return AssignmentCtx(id=id_, batch_id=batch, subject_id=id_, subject_code=f"S{id_}", subject_name=f"Subject {id_}",
                         faculty_id=fac, weekly_hours=hours, session_duration=dur, room_type=room_type,
                         equipment=equip, consecutive_required=consec)


def pl(id_, a, room, day, start, dur=1):
    return Placement(id=id_, assignment_id=a.id, batch_id=a.batch_id, faculty_id=a.faculty_id, room_id=room,
                     day=day, start=start, duration=dur)


def codes(vs):
    return {v.code for v in vs}


def test_valid_schedule_has_no_violations():
    a1, a2 = asg(1, 1, 1), asg(2, 2, 2)
    ctx = tiny_ctx(assignments=[a1, a2])
    assert validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a2, 2, 0, 0)]) == []


def test_faculty_cannot_teach_two_classes_simultaneously():
    a1, a2 = asg(1, 1, 1), asg(2, 2, 1)
    ctx = tiny_ctx(assignments=[a1, a2])
    assert "faculty_conflict" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a2, 2, 0, 0)]))


def test_batch_cannot_have_two_classes_simultaneously():
    a1, a2 = asg(1, 1, 1), asg(2, 1, 2)
    ctx = tiny_ctx(assignments=[a1, a2])
    assert "batch_conflict" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a2, 2, 0, 0)]))


def test_room_cannot_be_double_booked_even_partially_overlapping_blocks():
    a1, a2 = asg(1, 1, 1, hours=2, dur=2, consec=True), asg(2, 2, 2)
    ctx = tiny_ctx(assignments=[a1, a2])
    vs = validate_placements(ctx, [pl(1, a1, 1, 0, 0, 2), pl(2, a2, 1, 0, 1)])
    assert "room_conflict" in codes(vs)


def test_required_weekly_hours_must_be_met():
    a1 = asg(1, 1, 1, hours=3)
    ctx = tiny_ctx(assignments=[a1])
    vs = validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 1, 0)])
    assert "weekly_hours" in codes(vs)
    assert "weekly_hours" not in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 1, 0)], require_complete=False))
    assert validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 1, 0), pl(3, a1, 1, 2, 0)]) == []


def test_unavailable_faculty_slot_is_rejected():
    a1 = asg(1, 1, 1)
    ctx = tiny_ctx(assignments=[a1])
    ctx.faculty[1].unavailable.add((1, 2))
    assert "faculty_unavailable" in codes(validate_placements(ctx, [pl(1, a1, 1, 1, 2)]))


def test_breaks_blocked_periods_and_non_working_days():
    from app.scheduler.context import Period
    a1 = asg(1, 1, 1)
    ctx = tiny_ctx(assignments=[a1])
    ctx.periods[1] = Period(1, "10:00", "11:00", "lunch")
    assert "break_period" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 1)]))
    ctx.blocked.add((0, 2))
    assert "blocked_period" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 2)]))
    assert "outside_working_days" in codes(validate_placements(ctx, [pl(1, a1, 1, 5, 0)]))
    assert "outside_hours" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 9)]))


def test_block_cannot_span_a_break():
    from app.scheduler.context import Period
    a1 = asg(1, 1, 1, hours=2, dur=2, consec=True)
    ctx = tiny_ctx(assignments=[a1])
    ctx.periods[1] = Period(1, "10:00", "11:00", "break")
    assert "break_period" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0, 2)]))


def test_room_type_capacity_and_equipment():
    lab = asg(1, 1, 1, room_type="computer_lab", equip=frozenset({"computers"}))
    ctx = tiny_ctx(assignments=[lab])
    assert "room_type" in codes(validate_placements(ctx, [pl(1, lab, 1, 0, 0)]))
    assert validate_placements(ctx, [pl(1, lab, 3, 0, 0)]) == []
    ctx.rooms[3].equipment = frozenset()
    assert "room_equipment" in codes(validate_placements(ctx, [pl(1, lab, 3, 0, 0)]))
    a = asg(2, 1, 1)
    ctx2 = tiny_ctx(assignments=[a])
    ctx2.batches[1].strength = 100
    assert "room_capacity" in codes(validate_placements(ctx2, [pl(1, a, 1, 0, 0)]))


def test_faculty_daily_and_weekly_limits():
    a1 = asg(1, 1, 1, hours=3)
    ctx = tiny_ctx(assignments=[a1])
    ctx.faculty[1].max_per_day = 2
    vs = validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 0, 1), pl(3, a1, 1, 0, 2)])
    assert "faculty_daily_limit" in codes(vs)
    ctx.faculty[1].max_per_day, ctx.faculty[1].max_per_week = 3, 2
    vs = validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 1, 0), pl(3, a1, 1, 2, 0)])
    assert "faculty_weekly_limit" in codes(vs)
    ctx.max_daily_override = 1
    ctx.faculty[1].max_per_week = 10
    assert "faculty_daily_limit" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0), pl(2, a1, 1, 0, 1), pl(3, a1, 1, 1, 0)]))


def test_conflicts_with_other_published_timetables():
    a1 = asg(1, 1, 1)
    ctx = tiny_ctx(assignments=[a1], external_faculty_busy={(1, 0, 0)}, external_room_busy={(2, 1, 1)})
    assert "faculty_external_conflict" in codes(validate_placements(ctx, [pl(1, a1, 1, 0, 0)]))
    assert "room_external_conflict" in codes(validate_placements(ctx, [pl(1, a1, 2, 1, 1)]))
