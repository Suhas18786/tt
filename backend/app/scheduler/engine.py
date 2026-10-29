"""Timetable solver built on Google OR-Tools CP-SAT.

Model
-----
For every required session s (a block of `duration` consecutive periods of one teaching
assignment) there is a Boolean x[s,d,p,r] for each *candidate* (day d, start period p,
room r) that already satisfies the unary hard constraints (working day, class periods only,
no break/blocked period, faculty availability, room type/capacity/equipment/availability,
no clash with other published timetables). placed[s] = sum_x x[s,...].

Hard constraints (never relaxed)
  * faculty / batch / room: at most one session covers any (entity, day, period)
  * faculty daily and weekly workload limits
  * consecutive blocks: a block is one run of adjacent class periods (no break inside)
Required coverage ("every session scheduled") is enforced through a dominating penalty
BIG per unplaced session. If the data are satisfiable every session is placed. If not, the
solver returns the best *partial* timetable together with an infeasibility report that
lists the unscheduled sessions and the reasons - the result is never marked complete.

Soft constraints (weights configurable, see context.DEFAULT_WEIGHTS)
  faculty_spread, faculty_gaps, student_gaps, consecutive, subject_spread, preferred,
  room_balance, difficulty.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .candidates import build_sessions, candidate_placements, explain_unscheduled, static_diagnostics
from .context import Placement, ProblemContext
from .validator import validate_placements

BIG = 10_000_000


@dataclass
class SolveResult:
    status: str                      # complete | partial | no_solution
    solver_status: str
    placements: list = field(default_factory=list)
    unscheduled: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    objective: float | None = None
    seconds: float = 0.0
    stats: dict = field(default_factory=dict)


def _lin(terms):
    """terms: list of (coef, var) -> linear expression."""
    return cp_model.LinearExpr.WeightedSum([v for _, v in terms], [c for c, _ in terms])


def solve(ctx: ProblemContext, workers: int | None = None) -> SolveResult:
    t0 = time.time()
    sessions, issues = build_sessions(ctx)
    issues = list(issues) + static_diagnostics(ctx, sessions)
    if not sessions:
        return SolveResult("complete", "NO_SESSIONS", [], [], issues, 0.0, 0.0, {"sessions": 0})

    W = ctx.weights
    n_periods = max(p.index for p in ctx.periods) + 1
    ordinal = {p: i for i, p in enumerate(ctx.class_periods)}
    n_ord = len(ordinal)

    model = cp_model.CpModel()
    opts = {}                       # si -> [(var, d, p, r)]
    fac_cov, batch_cov, room_cov = defaultdict(list), defaultdict(list), defaultdict(list)
    fac_day_terms = defaultdict(list)     # (f, d) -> [(dur, var)]
    fac_week_terms = defaultdict(list)    # f -> [(dur, var)]
    room_terms = defaultdict(list)        # r -> [(dur, var)]
    batch_day_diff = defaultdict(list)    # (b, d) -> [(difficulty*dur, var)]
    assign_day_vars = defaultdict(list)   # (assignment id, d) -> [var]
    soft = []                             # (coef, var)
    n_vars = 0

    for s in sessions:
        a = s.assignment
        fac = ctx.faculty[a.faculty_id]
        lst = []
        for (d, p0, r) in candidate_placements(ctx, s):
            v = model.NewBoolVar(f"x_{s.key}_{d}_{p0}_{r}")
            n_vars += 1
            lst.append((v, d, p0, r))
            for q in range(p0, p0 + s.duration):
                fac_cov[(a.faculty_id, d, q)].append(v)
                batch_cov[(a.batch_id, d, q)].append(v)
                room_cov[(r, d, q)].append(v)
            fac_day_terms[(a.faculty_id, d)].append((s.duration, v))
            fac_week_terms[a.faculty_id].append((s.duration, v))
            room_terms[r].append((s.duration, v))
            batch_day_diff[(a.batch_id, d)].append((a.difficulty * s.duration, v))
            assign_day_vars[(a.id, d)].append(v)
            if fac.preferred:
                miss = sum(1 for q in range(p0, p0 + s.duration) if (d, q) not in fac.preferred)
                if miss and W.get("preferred", 0):
                    soft.append((W["preferred"] * miss, v))
        opts[s.key] = lst

    placed = {}
    for s in sessions:
        pv = model.NewBoolVar(f"placed_{s.key}")
        placed[s.key] = pv
        lst = opts[s.key]
        if lst:
            model.Add(cp_model.LinearExpr.Sum([v for v, *_ in lst]) == pv)
        else:
            model.Add(pv == 0)

    # ---- hard: no double booking ------------------------------------------------
    for cov in (fac_cov, batch_cov, room_cov):
        for vs in cov.values():
            if len(vs) > 1:
                model.AddAtMostOne(vs)

    # ---- hard: faculty daily / weekly limits ------------------------------------
    for (f, d), terms in fac_day_terms.items():
        cap = max(0, ctx.faculty_daily_cap(f) - ctx.external_load(f, d))
        model.Add(_lin(terms) <= cap)
    for f, terms in fac_week_terms.items():
        model.Add(_lin(terms) <= max(0, ctx.faculty[f].max_per_week - ctx.external_week_load(f)))

    # ---- symmetry breaking: sessions of one assignment are ordered in time -------
    by_assignment = defaultdict(list)
    for s in sessions:
        by_assignment[s.assignment.id].append(s)
    for lst in by_assignment.values():
        lst.sort(key=lambda s: s.number)
        texprs = {}
        for s in lst:
            texprs[s.key] = _lin([(d * n_periods + p, v) for v, d, p, _r in opts[s.key]]) if opts[s.key] else 0
        for s1, s2 in zip(lst, lst[1:]):
            model.Add(placed[s1.key] >= placed[s2.key])
            if opts[s1.key] and opts[s2.key]:
                model.Add(texprs[s1.key] + 1 <= texprs[s2.key]).OnlyEnforceIf(placed[s2.key])

    # ---- occupancy booleans ------------------------------------------------------
    def occupancy(cov):
        occ = {}
        for key, vs in cov.items():
            if len(vs) == 1:
                occ[key] = vs[0]
            else:
                o = model.NewBoolVar("occ")
                model.Add(cp_model.LinearExpr.Sum(vs) == o)  # at-most-one holds, so sum is 0/1
                occ[key] = o
        return occ

    fac_occ = occupancy(fac_cov)
    batch_occ = occupancy(batch_cov)

    fac_total = defaultdict(int)
    batch_total = defaultdict(int)
    for s in sessions:
        fac_total[s.faculty_id] += s.duration
        batch_total[s.batch_id] += s.duration

    # ---- soft: idle gaps (faculty & batches) --------------------------------------
    def add_gaps(occ, totals, weight):
        if not weight or n_ord < 3:
            return
        groups = defaultdict(list)
        for (e, d, p), o in occ.items():
            if totals[e] >= 2 and p in ordinal:
                groups[(e, d)].append((ordinal[p], o))
        for items in groups.values():
            if len(items) < 3:
                continue
            os_ = [o for _, o in items]
            cnt = cp_model.LinearExpr.Sum(os_)
            used = model.NewBoolVar("used")
            model.Add(cnt >= 1).OnlyEnforceIf(used)
            model.Add(cnt == 0).OnlyEnforceIf(used.Not())
            first = model.NewIntVar(0, n_ord - 1, "first")
            last = model.NewIntVar(0, n_ord - 1, "last")
            for k, o in items:
                model.Add(first <= k).OnlyEnforceIf(o)
                model.Add(last >= k).OnlyEnforceIf(o)
            gap = model.NewIntVar(0, n_ord, "gap")
            model.Add(gap >= last - first + 1 - cnt).OnlyEnforceIf(used)
            soft.append((weight, gap))

    add_gaps(fac_occ, fac_total, W.get("faculty_gaps", 0))
    add_gaps(batch_occ, batch_total, W.get("student_gaps", 0))

    # ---- soft: too many consecutive teaching periods (faculty) --------------------
    k = ctx.max_consecutive
    if W.get("consecutive", 0) and k >= 1:
        for f, total in fac_total.items():
            if total <= k:
                continue
            for d in ctx.working_days:
                for p0 in ctx.class_periods:
                    window = list(range(p0, p0 + k + 1))
                    if not all(ctx.slot_is_class(d, q) for q in window):
                        continue
                    os_ = [fac_occ[(f, d, q)] for q in window if (f, d, q) in fac_occ]
                    if len(os_) <= k:
                        continue
                    viol = model.NewBoolVar("consec")
                    model.Add(cp_model.LinearExpr.Sum(os_) <= k + viol)
                    soft.append((W["consecutive"], viol))

    # ---- soft: even faculty workload over the week ---------------------------------
    if W.get("faculty_spread", 0):
        for f in fac_total:
            days = [d for d in ctx.working_days if (f, d) in fac_day_terms]
            if len(days) < 2:
                continue
            mx = model.NewIntVar(0, ctx.faculty_daily_cap(f), f"maxload_{f}")
            for d in days:
                model.Add(mx >= _lin(fac_day_terms[(f, d)]))
            soft.append((W["faculty_spread"], mx))

    # ---- soft: spread repeated sessions of a subject over different days -------------
    if W.get("subject_spread", 0):
        for a_id, lst in by_assignment.items():
            n = len(lst)
            if n < 2:
                continue
            for d in ctx.working_days:
                vs = assign_day_vars.get((a_id, d), [])
                if len(vs) < 2:
                    continue
                ex = model.NewIntVar(0, n, "spread")
                model.Add(ex >= cp_model.LinearExpr.Sum(vs) - 1)
                soft.append((W["subject_spread"], ex))

    # ---- soft: balanced room utilisation (per room type) ------------------------------
    if W.get("room_balance", 0):
        by_type = defaultdict(list)
        for r, terms in room_terms.items():
            by_type[ctx.rooms[r].room_type].append(r)
        for rtype, rs in by_type.items():
            if len(rs) < 2:
                continue
            mx = model.NewIntVar(0, len(ctx.working_days) * n_ord, f"roomload_{rtype}")
            for r in rs:
                model.Add(mx >= _lin(room_terms[r]))
            soft.append((W["room_balance"], mx))

    # ---- soft: avoid piling difficult subjects on one day ---------------------------------
    if W.get("difficulty", 0):
        for b in batch_total:
            if not any(a.difficulty > 1 for a in ctx.assignments if a.batch_id == b):
                continue
            days = [d for d in ctx.working_days if (b, d) in batch_day_diff]
            if len(days) < 2:
                continue
            h = model.NewIntVar(0, 3 * n_ord, f"heavy_{b}")
            for d in days:
                model.Add(h >= _lin(batch_day_diff[(b, d)]))
            soft.append((W["difficulty"], h))

    # ---- objective ---------------------------------------------------------------------
    obj_terms = [(-BIG, placed[s.key]) for s in sessions] + soft
    model.Minimize(_lin(obj_terms) + BIG * len(sessions))  # = BIG*unplaced + soft cost (>= 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(ctx.time_limit)
    n_workers = workers or int(os.getenv("SOLVER_WORKERS", "8"))
    try:
        solver.parameters.num_workers = n_workers
    except Exception:  # older ortools
        solver.parameters.num_search_workers = n_workers
    solver.parameters.random_seed = 7
    solver.parameters.relative_gap_limit = 0.02

    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    seconds = time.time() - t0
    stats = {"sessions": len(sessions), "variables": n_vars, "soft_terms": len(soft),
             "wall_time": round(seconds, 3)}

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        issues.append({"severity": "error", "code": "no_solution",
                       "message": ("The solver found no timetable within the time limit "
                                   f"({ctx.time_limit}s, status {status_name}). Increase the time limit or relax constraints.")})
        return SolveResult("no_solution", status_name, [], [], issues, None, seconds, stats)

    placements, unscheduled = [], []
    for s in sessions:
        chosen = next(((d, p, r) for v, d, p, r in opts[s.key] if solver.Value(v) == 1), None)
        if chosen is None:
            unscheduled.append({
                "assignment_id": s.assignment.id, "session": s.label(),
                "subject_code": s.assignment.subject_code, "subject_name": s.assignment.subject_name,
                "batch_id": s.batch_id, "faculty_id": s.faculty_id, "duration": s.duration,
                "reason": explain_unscheduled(ctx, s, issues),
            })
            continue
        d, p, r = chosen
        placements.append(Placement(id=s.key, assignment_id=s.assignment.id, batch_id=s.batch_id,
                                    faculty_id=s.faculty_id, room_id=r, day=d, start=p, duration=s.duration))

    # Safety net: independently re-validate everything the solver produced.
    bad = validate_placements(ctx, placements, require_complete=not unscheduled)
    if bad:
        raise RuntimeError("Solver produced an invalid timetable: " + "; ".join(x.message for x in bad[:5]))

    objective = solver.ObjectiveValue()
    stats["soft_cost"] = round(objective - BIG * len(unscheduled), 3)
    stats["best_bound"] = solver.BestObjectiveBound()
    if unscheduled:
        issues.append({"severity": "error", "code": "unscheduled",
                       "message": f"{len(unscheduled)} session(s) could not be scheduled; see the unscheduled list."})
    return SolveResult("partial" if unscheduled else "complete", status_name, placements, unscheduled,
                       issues, objective, seconds, stats)
