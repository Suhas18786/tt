"""Plain-Python problem description shared by the solver and the validator.

This module deliberately has no database / ortools imports so it can be unit-tested
anywhere. The loader (loader.py) fills it from the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DEFAULT_WEIGHTS = {
    "faculty_spread": 3,    # even workload across the week
    "faculty_gaps": 2,      # idle periods between a faculty member's classes
    "student_gaps": 3,      # idle periods inside a batch's day
    "consecutive": 2,       # more than `max_consecutive` teaching periods in a row
    "subject_spread": 4,    # repeated sessions of one subject on the same day
    "preferred": 3,         # faculty preferred periods
    "room_balance": 1,      # even room utilisation
    "difficulty": 1,        # avoid piling hard subjects on one day
}

DEFAULT_PERIODS = [
    {"index": 0, "start": "09:00", "end": "10:00", "kind": "class"},
    {"index": 1, "start": "10:00", "end": "11:00", "kind": "class"},
    {"index": 2, "start": "11:00", "end": "12:00", "kind": "class"},
    {"index": 3, "start": "12:00", "end": "13:00", "kind": "class"},
    {"index": 4, "start": "13:00", "end": "14:00", "kind": "lunch"},
    {"index": 5, "start": "14:00", "end": "15:00", "kind": "class"},
    {"index": 6, "start": "15:00", "end": "16:00", "kind": "class"},
    {"index": 7, "start": "16:00", "end": "17:00", "kind": "class"},
]


@dataclass
class Period:
    index: int
    start: str
    end: str
    kind: str = "class"  # class | break | lunch


@dataclass
class FacultyCtx:
    id: int
    name: str
    max_per_day: int
    max_per_week: int
    unavailable: set = field(default_factory=set)  # {(day, period)}
    preferred: set = field(default_factory=set)


@dataclass
class BatchCtx:
    id: int
    code: str
    strength: int
    department_id: int | None = None


@dataclass
class RoomCtx:
    id: int
    label: str
    room_type: str
    capacity: int
    equipment: frozenset = frozenset()
    blocked: set = field(default_factory=set)  # {(day, period)}


@dataclass
class AssignmentCtx:
    id: int
    batch_id: int
    subject_id: int
    subject_code: str
    subject_name: str
    faculty_id: int
    weekly_hours: int
    session_duration: int      # *effective* block length (1 unless consecutive_required)
    room_type: str
    equipment: frozenset = frozenset()
    difficulty: int = 1
    subject_type: str = "lecture"
    consecutive_required: bool = False


@dataclass
class Placement:
    """A session placed in the timetable. `id` is any hashable (DB id, or temp key)."""
    id: object
    assignment_id: int
    batch_id: int
    faculty_id: int
    room_id: int
    day: int
    start: int
    duration: int

    def periods(self):
        return range(self.start, self.start + self.duration)


@dataclass
class SessionReq:
    key: int            # running index
    assignment: AssignmentCtx
    number: int         # 0-based number within the assignment
    duration: int

    @property
    def batch_id(self):
        return self.assignment.batch_id

    @property
    def faculty_id(self):
        return self.assignment.faculty_id

    def label(self) -> str:
        return f"{self.assignment.subject_code} #{self.number + 1}"


@dataclass
class ProblemContext:
    working_days: list
    periods: list
    blocked: set                       # {(day, period)} blocked for everybody
    faculty: dict
    batches: dict
    rooms: dict
    assignments: list
    external_faculty_busy: set = field(default_factory=set)   # {(fid, day, period)} (other published timetables)
    external_room_busy: set = field(default_factory=set)      # {(rid, day, period)}
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    max_consecutive: int = 3
    time_limit: int = 30
    max_daily_override: int | None = None

    # ---- helpers -------------------------------------------------------
    @property
    def class_periods(self) -> list:
        return [p.index for p in self.periods if p.kind == "class"]

    def period_by_index(self) -> dict:
        return {p.index: p for p in self.periods}

    def slot_is_class(self, day: int, period: int) -> bool:
        pm = self.period_by_index().get(period)
        return (day in self.working_days and pm is not None and pm.kind == "class"
                and (day, period) not in self.blocked)

    def faculty_daily_cap(self, fid: int) -> int:
        cap = self.faculty[fid].max_per_day
        if self.max_daily_override:
            cap = min(cap, self.max_daily_override)
        return cap

    def external_load(self, fid: int, day: int) -> int:
        return sum(1 for (f, d, _p) in self.external_faculty_busy if f == fid and d == day)

    def external_week_load(self, fid: int) -> int:
        return sum(1 for (f, _d, _p) in self.external_faculty_busy if f == fid)

    def assignment_by_id(self) -> dict:
        return {a.id: a for a in self.assignments}

    def slot_label(self, day: int, period: int) -> str:
        pm = self.period_by_index().get(period)
        t = f" ({pm.start}-{pm.end})" if pm else ""
        return f"{DAY_NAMES[day]} period {period + 1}{t}"
