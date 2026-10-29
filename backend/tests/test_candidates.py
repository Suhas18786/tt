"""Session splitting, candidate generation and infeasibility diagnostics (pure Python)."""
from app.scheduler.candidates import (build_sessions, candidate_placements, eligible_rooms, explain_unscheduled,
                                      static_diagnostics, time_options)

from .helpers import ctx_from_seed, tiny_ctx
from .test_validator import asg


def test_weekly_hours_split_into_sessions():
    ctx = ctx_from_seed(["CSE-S3-A"])
    sessions, issues = build_sessions(ctx)
    by = {}
    for s in sessions:
        by.setdefault(s.assignment.subject_code, []).append(s.duration)
    assert by["CS301"] == [1, 1, 1, 1]
    assert by["CS305"] == [2, 2]  # 4 lab hours -> two 2-period blocks
    assert sum(s.duration for s in sessions) == 20
    assert issues == []


def test_hours_not_multiple_of_duration_gives_warning_and_remainder_block():
    a = asg(1, 1, 1, hours=3, dur=2, consec=True)
    sessions, issues = build_sessions(tiny_ctx(assignments=[a]))
    assert [s.duration for s in sessions] == [2, 1]
    assert issues and issues[0]["code"] == "hours_not_multiple"


def test_lab_blocks_never_cross_lunch_or_day_end():
    ctx = ctx_from_seed(["CSE-S3-A"])
    sessions, _ = build_sessions(ctx)
    lab = next(s for s in sessions if s.assignment.subject_code == "CS305")
    starts = {p for _d, p in time_options(ctx, lab)}
    assert starts == {0, 1, 2, 5, 6}   # 3 would span lunch (3,4); 7 would run past the last period


def test_candidates_respect_room_type_capacity_and_equipment():
    ctx = ctx_from_seed(["ECE-S3-A"])
    lab = next(a for a in ctx.assignments if a.subject_code == "EC304")
    rooms = {r.label for r in eligible_rooms(ctx, lab)}
    assert rooms == {"EC Block-EL-1", "EC Block-EL-2"}


def test_candidates_respect_faculty_unavailability():
    ctx = ctx_from_seed(["ECE-S3-A"])
    sessions, _ = build_sessions(ctx)
    s = next(s for s in sessions if s.faculty_id == next(i for i, f in ctx.faculty.items() if f.name == "Dr. Neha Kapoor"))
    assert (4, 5) not in {(d, p) for d, p, _r in candidate_placements(ctx, s)}


def test_diagnostics_report_overloaded_faculty_and_missing_rooms():
    a1 = asg(1, 1, 1, hours=3)
    a2 = asg(2, 2, 1, hours=3)
    ctx = tiny_ctx(assignments=[a1, a2])
    ctx.faculty[1].max_per_week = 4
    sessions, _ = build_sessions(ctx)
    msgs = " ".join(i["message"] for i in static_diagnostics(ctx, sessions))
    assert "Alice" in msgs and "at most 4" in msgs

    big = asg(3, 1, 2, room_type="laboratory")
    ctx = tiny_ctx(assignments=[big])
    sessions, _ = build_sessions(ctx)
    diag = static_diagnostics(ctx, sessions)
    assert {i["code"] for i in diag} >= {"no_room_type", "no_eligible_room"}
    assert "laboratory" in explain_unscheduled(ctx, sessions[0], diag)


def test_batch_with_more_periods_than_exist_is_flagged():
    ctx = tiny_ctx(assignments=[asg(1, 1, 1, hours=6), asg(2, 1, 2, hours=6)])  # 12 periods vs 9 slots
    sessions, _ = build_sessions(ctx)
    assert any(i["code"] == "batch_capacity" for i in static_diagnostics(ctx, sessions))
