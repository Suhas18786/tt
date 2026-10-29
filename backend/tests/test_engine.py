"""CP-SAT scheduling engine. Skipped automatically if ortools is not installed."""
from collections import Counter, defaultdict

import pytest

pytest.importorskip("ortools")

from app.scheduler.engine import solve  # noqa: E402
from app.scheduler.validator import validate_placements  # noqa: E402

from .helpers import ctx_from_seed, tiny_ctx  # noqa: E402
from .test_validator import asg  # noqa: E402


@pytest.fixture(scope="module")
def full():
    ctx = ctx_from_seed(time_limit=30)
    return ctx, solve(ctx)


def occupancy(ctx, placements, who):
    c = Counter()
    for p in placements:
        for q in p.periods():
            c[(getattr(p, who), p.day, q)] += 1
    return c


def test_seed_data_yields_a_complete_timetable(full):
    ctx, res = full
    assert res.status == "complete", res.issues
    assert not res.unscheduled
    assert validate_placements(ctx, res.placements) == []


def test_no_double_booking_of_faculty_batches_or_rooms(full):
    ctx, res = full
    for who in ("faculty_id", "batch_id", "room_id"):
        assert max(occupancy(ctx, res.placements, who).values()) == 1, who


def test_weekly_teaching_hours_are_exact(full):
    ctx, res = full
    got = defaultdict(int)
    for p in res.placements:
        got[p.assignment_id] += p.duration
    for a in ctx.assignments:
        assert got[a.id] == a.weekly_hours, a.subject_code


def test_faculty_availability_and_daily_limits_are_respected(full):
    ctx, res = full
    per_day = Counter()
    for p in res.placements:
        for q in p.periods():
            assert (p.day, q) not in ctx.faculty[p.faculty_id].unavailable
        per_day[(p.faculty_id, p.day)] += p.duration
    for (f, _d), n in per_day.items():
        assert n <= ctx.faculty[f].max_per_day


def test_lab_sessions_are_consecutive_blocks_not_spanning_lunch(full):
    ctx, res = full
    labs = [p for p in res.placements if ctx.assignment_by_id()[p.assignment_id].consecutive_required]
    assert labs
    for p in labs:
        assert p.duration == 2
        kinds = [ctx.period_by_index()[q].kind for q in p.periods()]
        assert kinds == ["class", "class"]


def test_rooms_match_type_and_capacity(full):
    ctx, res = full
    for p in res.placements:
        a, r, b = ctx.assignment_by_id()[p.assignment_id], ctx.rooms[p.room_id], ctx.batches[p.batch_id]
        assert r.room_type == a.room_type and r.capacity >= b.strength and a.equipment <= r.equipment


def test_tiny_instance_is_solved_and_spreads_subject_over_days():
    ctx = tiny_ctx(assignments=[asg(1, 1, 1, hours=3), asg(2, 1, 2, hours=2)])
    res = solve(ctx)
    assert res.status == "complete"
    days = [p.day for p in res.placements if p.assignment_id == 1]
    assert len(set(days)) == 3          # soft constraint: one session per day when possible


def test_impossible_weekly_limit_yields_infeasibility_report_not_invalid_timetable():
    a = asg(1, 1, 1, hours=3)
    ctx = tiny_ctx(assignments=[a, asg(2, 2, 1, hours=3)])
    ctx.faculty[1].max_per_week = 4          # needs 6
    res = solve(ctx)
    assert res.status == "partial"
    assert len(res.unscheduled) == 2
    assert all(u["reason"] for u in res.unscheduled)
    assert any("Alice" in i["message"] for i in res.issues)
    assert validate_placements(ctx, res.placements, require_complete=False) == []
    assert validate_placements(ctx, res.placements, require_complete=True)  # incomplete -> never publishable


def test_missing_room_type_is_reported_with_reason():
    ctx = tiny_ctx(assignments=[asg(1, 1, 1, room_type="laboratory"), asg(2, 1, 2)])
    res = solve(ctx)
    assert res.status == "partial"
    assert [u["subject_code"] for u in res.unscheduled] == ["S1"]
    assert "laboratory" in res.unscheduled[0]["reason"]
    assert len(res.placements) == 1          # the feasible class is still placed


def test_unavailable_slots_can_make_a_problem_infeasible():
    ctx = tiny_ctx(assignments=[asg(1, 1, 1, hours=3)])
    ctx.faculty[1].unavailable = {(d, p) for d in (0, 1, 2) for p in (0, 1, 2)} - {(0, 0)}
    res = solve(ctx)
    assert res.status == "partial" and len(res.unscheduled) == 2


def test_departments_schedule_independently_without_clashing_on_shared_faculty_or_rooms():
    cse = ctx_from_seed(["CSE-S3-A", "CSE-S3-B"], time_limit=20)
    r1 = solve(cse)
    assert r1.status == "complete"
    busy_f = {(p.faculty_id, p.day, q) for p in r1.placements for q in p.periods()}
    busy_r = {(p.room_id, p.day, q) for p in r1.placements for q in p.periods()}
    other = ctx_from_seed(["ECE-S3-A", "MECH-S3-A"], time_limit=20,
                          external_faculty_busy=busy_f, external_room_busy=busy_r)
    r2 = solve(other)
    assert r2.status == "complete", r2.issues
    mine_f = {(p.faculty_id, p.day, q) for p in r2.placements for q in p.periods()}
    mine_r = {(p.room_id, p.day, q) for p in r2.placements for q in p.periods()}
    assert not (mine_f & busy_f) and not (mine_r & busy_r)   # e.g. shared Math faculty Dr. Joshi


def test_preferred_slots_are_honoured_when_weighted():
    ctx = ctx_from_seed(["CSE-S3-A"], time_limit=20)
    ctx.weights = {k: 0 for k in ctx.weights}
    ctx.weights["preferred"] = 10
    res = solve(ctx)
    rao = next(i for i, f in ctx.faculty.items() if f.name == "Dr. Anita Rao")
    assert res.status == "complete"
    for p in res.placements:
        if p.faculty_id == rao:
            assert all((p.day, q) in ctx.faculty[rao].preferred for q in p.periods())
