"""Pydantic request/response models (server-side validation)."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

RoomType = Literal["lecture_room", "computer_lab", "laboratory"]
SubjectType = Literal["lecture", "tutorial", "lab"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: str


class DepartmentIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=200)


class DepartmentOut(DepartmentIn, ORM):
    id: int


class AcademicYearIn(BaseModel):
    name: str = Field(pattern=r"^\d{4}-\d{2,4}$", description="e.g. 2026-27")
    is_current: bool = False


class AcademicYearOut(AcademicYearIn, ORM):
    id: int


class SemesterIn(BaseModel):
    academic_year_id: int
    number: int = Field(ge=1, le=12)
    name: str = Field(min_length=1, max_length=60)


class SemesterOut(SemesterIn, ORM):
    id: int


class BatchIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    section: str = Field(default="A", max_length=10)
    department_id: int
    semester_id: int
    strength: int = Field(ge=1, le=1000)


class BatchOut(BatchIn, ORM):
    id: int


class ClassroomIn(BaseModel):
    room_number: str = Field(min_length=1, max_length=30)
    building: str = Field(min_length=1, max_length=100)
    room_type: RoomType = "lecture_room"
    capacity: int = Field(ge=1, le=2000)
    equipment: list[str] = []


class ClassroomOut(ClassroomIn, ORM):
    id: int


class SubjectIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    department_id: int
    semester_number: int = Field(ge=1, le=12)
    subject_type: SubjectType = "lecture"
    weekly_hours: int = Field(ge=1, le=30)
    session_duration: int = Field(default=1, ge=1, le=6)
    room_type: RoomType = "lecture_room"
    consecutive_required: bool = False
    difficulty: int = Field(default=1, ge=1, le=3)
    required_equipment: list[str] = []

    @model_validator(mode="after")
    def _check(self):
        if self.session_duration > self.weekly_hours:
            raise ValueError("session_duration cannot exceed weekly_hours")
        if self.consecutive_required and self.session_duration < 2:
            raise ValueError("consecutive_required needs a session_duration of at least 2 periods")
        return self


class SubjectOut(SubjectIn, ORM):
    id: int


class FacultyIn(BaseModel):
    faculty_code: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    department_id: int
    max_hours_per_day: int = Field(default=5, ge=1, le=12)
    max_hours_per_week: int = Field(default=18, ge=1, le=60)
    qualified_subject_ids: list[int] = []
    initial_password: str | None = Field(default=None, min_length=8, max_length=128,
                                         description="Creates a login for the faculty member")

    @model_validator(mode="after")
    def _check(self):
        if self.max_hours_per_day > self.max_hours_per_week:
            raise ValueError("max_hours_per_day cannot exceed max_hours_per_week")
        return self


class AssignmentIn(BaseModel):
    batch_id: int
    subject_id: int
    faculty_id: int


class AssignmentOut(AssignmentIn, ORM):
    id: int


class AvailabilitySlot(BaseModel):
    day: int = Field(ge=0, le=6)
    period: int = Field(ge=0, le=30)
    status: Literal["unavailable", "preferred"]


class AvailabilityIn(BaseModel):
    slots: list[AvailabilitySlot]


class PeriodIn(BaseModel):
    index: int = Field(ge=0, le=30)
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    kind: Literal["class", "break", "lunch"] = "class"


class ConfigIn(BaseModel):
    working_days: list[int] | None = None
    periods: list[PeriodIn] | None = None
    blocked_slots: list[list[int]] | None = None
    weights: dict[str, int] | None = None
    max_consecutive: int | None = Field(default=None, ge=1, le=10)
    time_limit_seconds: int | None = Field(default=None, ge=1, le=600)
    max_daily_hours_override: int | None = Field(default=None, ge=1, le=12)

    @field_validator("working_days")
    @classmethod
    def _days(cls, v):
        if v is not None:
            if not v or any(d < 0 or d > 6 for d in v) or len(set(v)) != len(v):
                raise ValueError("working_days must be unique numbers 0-6")
        return v

    @field_validator("periods")
    @classmethod
    def _periods(cls, v):
        if v is not None:
            idx = [p.index for p in v]
            if sorted(idx) != list(range(len(idx))):
                raise ValueError("period indexes must be 0..n-1 without gaps")
            if not any(p.kind == "class" for p in v):
                raise ValueError("at least one class period is required")
            for p in v:
                if p.start >= p.end:
                    raise ValueError(f"period {p.index + 1}: start must be before end")
        return v

    @field_validator("weights")
    @classmethod
    def _weights(cls, v):
        from .scheduler.context import DEFAULT_WEIGHTS
        if v is not None:
            for k, w in v.items():
                if k not in DEFAULT_WEIGHTS:
                    raise ValueError(f"unknown weight '{k}'")
                if w < 0 or w > 20:
                    raise ValueError("weights must be between 0 and 20")
        return v


class GenerateIn(ConfigIn):
    name: str = Field(default="Timetable", min_length=1, max_length=200)
    semester_id: int | None = None
    department_id: int | None = None
    batch_ids: list[int] | None = None
    assignment_ids: list[int] | None = None
    replace_generation_id: int | None = None


class MoveIn(BaseModel):
    session_id: int
    day: int = Field(ge=0, le=6)
    start_period: int = Field(ge=0, le=30)
    room_id: int | None = None
    dry_run: bool = False


class ConflictReportIn(BaseModel):
    message: str = Field(min_length=5, max_length=2000)
    generation_id: int | None = None


class ConflictResolveIn(BaseModel):
    admin_note: str = Field(default="", max_length=2000)


class FacultyCodeCheck(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def _c(cls, v):
        if not re.match(r"^[\w\-./]+$", v):
            raise ValueError("invalid code")
        return v
