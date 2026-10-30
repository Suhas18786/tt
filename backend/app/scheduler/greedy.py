"""Fast constructive scheduler (pure Python, no OR-Tools).

Used in two ways by the engine:
  * as a starting point (hint) for CP-SAT, so the solver always begins from a valid timetable;
  * as a fallback when CP-SAT returns nothing within the time limit (e.g. on a very small server).

It respects every hard constraint the validator checks: faculty/batch/room never double-booked, the unary
constraints already baked into candidate_placements (availability, breaks, blocked periods, room type and
capacity), and faculty daily/weekly workload limits. Most-constrained sessions are placed first; if some
sessions do not fit, it restarts with a perturbed order until the time budget is used up and keeps the best.
"""
from __future__ import annotations

import random
import time
from collections import defaultdict

from .candidates import candidate_placements
from .context import ProblemContext


def greedy_schedule(ctx: ProblemContext, sessions: list, seconds: float = 8.0, seed: int = 7) -> dict:
    """Returns {session.key: (day, start, room_id) or None}."""
    cands = {s.key: candidate_placements(ctx, s) for s in sessions}
    rng = random.Random(seed)
    deadline = time.time() + seconds
    best, best_n, attempt = {}, -1, 0

    while True:
        noise = 0.0 if attempt == 0 else 0.6
        order = sorted(sessions, key=lambda s: (len(cands[s.key]) * (1 + noise * rng.random()), -s.duration))
        fac_busy, batch_busy, room_busy = set(), set(), set()
        fac_day, fac_week = defaultdict(int), defaultdict(int)
        a_day = defaultdict(int)
        room_load = defaultdict(int)
        result = {}
        for s in order:
            f, b, a = s.faculty_id, s.batch_id, s.assignment
            fac = ctx.faculty[f]
            week_cap = fac.max_per_week - ctx.external_week_load(f)
            chosen, chosen_score = None, None
            for (d, p0, r) in cands[s.key]:
                span = range(p0, p0 + s.duration)
                if any((f, d, q) in fac_busy or (b, d, q) in batch_busy or (r, d, q) in room_busy for q in span):
                    continue
                if fac_day[(f, d)] + s.duration > ctx.faculty_daily_cap(f) - ctx.external_load(f, d):
                    continue
                if fac_week[f] + s.duration > week_cap:
                    continue
                miss = sum(1 for q in span if fac.preferred and (d, q) not in fac.preferred)
                score = (6 * a_day[(a.id, d)] + 2 * fac_day[(f, d)] + miss * 2 + room_load[r] * 0.1
                         + p0 * 0.05 + rng.random() * (0.2 if attempt else 0.0))
                if chosen_score is None or score < chosen_score:
                    chosen, chosen_score = (d, p0, r), score
            if chosen is None:
                result[s.key] = None
                continue
            d, p0, r = chosen
            for q in range(p0, p0 + s.duration):
                fac_busy.add((f, d, q)); batch_busy.add((b, d, q)); room_busy.add((r, d, q))
            fac_day[(f, d)] += s.duration
            fac_week[f] += s.duration
            a_day[(a.id, d)] += 1
            room_load[r] += s.duration
            result[s.key] = chosen
        placed = sum(1 for v in result.values() if v is not None)
        if placed > best_n:
            best, best_n = result, placed
        attempt += 1
        if placed == len(sessions) or time.time() >= deadline:
            return best
