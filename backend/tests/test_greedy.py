"""The greedy fallback/hint scheduler must itself produce conflict-free timetables (pure Python)."""
import time

from app.scheduler.candidates import build_sessions
from app.scheduler.context import Placement
from app.scheduler.greedy import greedy_schedule
from app.scheduler.validator import validate_placements

from .helpers import ctx_from_seed


def _placements(sessions, choice):
    out = []
    for s in sessions:
        c = choice[s.key]
        if c:
            d, p, r = c
            out.append(Placement(id=s.key, assignment_id=s.assignment.id, batch_id=s.batch_id, faculty_id=s.faculty_id,
                                 room_id=r, day=d, start=p, duration=s.duration))
    return out


def test_greedy_schedules_all_seed_data_without_violations():
    ctx = ctx_from_seed()
    sessions, _ = build_sessions(ctx)
    t0 = time.time()
    choice = greedy_schedule(ctx, sessions, seconds=10)
    pl = _placements(sessions, choice)
    unplaced = [s for s in sessions if not choice[s.key]]
    assert not unplaced, f"{len(unplaced)} unplaced in {time.time() - t0:.1f}s"
    assert validate_placements(ctx, pl, require_complete=True) == []


def test_greedy_partial_result_is_still_conflict_free_when_impossible():
    ctx = ctx_from_seed(["CSE-S3-A"])
    for f in ctx.faculty.values():
        f.max_per_week = 3                      # far too little teaching capacity
    sessions, _ = build_sessions(ctx)
    choice = greedy_schedule(ctx, sessions, seconds=1)
    pl = _placements(sessions, choice)
    assert 0 < len(pl) < len(sessions)
    assert validate_placements(ctx, pl, require_complete=False) == []
