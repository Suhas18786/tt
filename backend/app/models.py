"""SQLAlchemy models (normalised schema).

Mapping to the requirements:
  users/roles            -> User
  departments            -> Department
  academic years         -> AcademicYear
  semesters              -> Semester
  faculty                -> Faculty
  subjects               -> Subject
  faculty qualifications -> FacultyQualification
  teaching assignments   -> TeachingAssignment  (batch + subject + faculty)
  batches / sections     -> Batch
  classrooms             -> Classroom (+ RoomBlockedSlot for room availability)
  working days / slots   -> TimetableConfig (working_days, periods, blocked_slots)
  faculty availability   -> FacultyAvailability
  scheduling constraints -> TimetableConfig (weights, limits)
  timetable generations  -> Generation
  scheduled sessions     -> ScheduledSession
  publication history    -> PublicationHistory
"""
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey,
                        Index, Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ROLES = ("admin", "faculty")
ROOM_TYPES = ("lecture_room", "computer_lab", "laboratory")
SUBJECT_TYPES = ("lecture", "tutorial", "lab")
GEN_STATUSES = ("preview", "draft", "published", "archived", "infeasible")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="faculty")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("role in ('admin','faculty')", name="ck_user_role"),)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)


class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)  # e.g. 2026-27
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Semester(Base):
    __tablename__ = "semesters"
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)  # 1..8
    name: Mapped[str] = mapped_column(String(60))
    __table_args__ = (
        UniqueConstraint("academic_year_id", "number", name="uq_semester_year_number"),
        CheckConstraint("number between 1 and 12", name="ck_semester_number"),
    )


class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_code: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    max_hours_per_day: Mapped[int] = mapped_column(Integer, default=5)
    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=18)
    __table_args__ = (
        CheckConstraint("max_hours_per_day between 1 and 12", name="ck_fac_day"),
        CheckConstraint("max_hours_per_week between 1 and 60", name="ck_fac_week"),
    )


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    semester_number: Mapped[int] = mapped_column(Integer)
    subject_type: Mapped[str] = mapped_column(String(20), default="lecture")
    weekly_hours: Mapped[int] = mapped_column(Integer)           # teaching periods per week
    session_duration: Mapped[int] = mapped_column(Integer, default=1)  # periods per session block
    room_type: Mapped[str] = mapped_column(String(30), default="lecture_room")
    consecutive_required: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1 easy .. 3 hard
    required_equipment: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (
        CheckConstraint("weekly_hours between 1 and 30", name="ck_sub_hours"),
        CheckConstraint("session_duration between 1 and 6", name="ck_sub_duration"),
        CheckConstraint("difficulty between 1 and 3", name="ck_sub_diff"),
        CheckConstraint("subject_type in ('lecture','tutorial','lab')", name="ck_sub_type"),
        CheckConstraint("room_type in ('lecture_room','computer_lab','laboratory')", name="ck_sub_room"),
    )


class FacultyQualification(Base):
    __tablename__ = "faculty_qualifications"
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)


class FacultyAvailability(Base):
    """Only non-default slots are stored. Default = available, not preferred."""
    __tablename__ = "faculty_availability"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    period: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # unavailable | preferred
    __table_args__ = (
        UniqueConstraint("faculty_id", "day", "period", name="uq_fac_avail"),
        CheckConstraint("status in ('unavailable','preferred')", name="ck_avail_status"),
        CheckConstraint("day between 0 and 6", name="ck_avail_day"),
    )


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(10), default="A")
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), index=True)
    strength: Mapped[int] = mapped_column(Integer, default=60)
    __table_args__ = (CheckConstraint("strength between 1 and 1000", name="ck_batch_strength"),)


class Classroom(Base):
    __tablename__ = "classrooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(String(30))
    building: Mapped[str] = mapped_column(String(100))
    room_type: Mapped[str] = mapped_column(String(30), default="lecture_room")
    capacity: Mapped[int] = mapped_column(Integer)
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (
        UniqueConstraint("building", "room_number", name="uq_room"),
        CheckConstraint("capacity between 1 and 2000", name="ck_room_cap"),
        CheckConstraint("room_type in ('lecture_room','computer_lab','laboratory')", name="ck_room_type"),
    )


class RoomBlockedSlot(Base):
    """Room availability: slots in which the room is NOT available."""
    __tablename__ = "room_blocked_slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    period: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("classroom_id", "day", "period", name="uq_room_block"),)


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), index=True)
    __table_args__ = (UniqueConstraint("batch_id", "subject_id", name="uq_assignment"),)


class TimetableConfig(Base):
    """Working days, period grid, blocked slots and soft-constraint weights."""
    __tablename__ = "timetable_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="default")
    working_days: Mapped[list] = mapped_column(JSON)      # [0,1,2,3,4]  (0 = Monday)
    periods: Mapped[list] = mapped_column(JSON)           # [{index,start,end,kind}]
    blocked_slots: Mapped[list] = mapped_column(JSON, default=list)  # [[day, period], ...]
    weights: Mapped[dict] = mapped_column(JSON)
    max_consecutive: Mapped[int] = mapped_column(Integer, default=3)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_daily_hours_override: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Generation(Base):
    __tablename__ = "timetable_generations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="preview", index=True)
    semester_id: Mapped[int | None] = mapped_column(ForeignKey("semesters.id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    batch_ids: Mapped[list] = mapped_column(JSON)
    config: Mapped[dict] = mapped_column(JSON)       # snapshot used for solving
    solver_status: Mapped[str] = mapped_column(String(30), default="")
    objective: Mapped[float | None] = mapped_column(Float, nullable=True)
    solve_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sessions: Mapped[list["ScheduledSession"]] = relationship(
        back_populates="generation", cascade="all, delete-orphan", passive_deletes=True)


class ScheduledSession(Base):
    __tablename__ = "scheduled_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    generation_id: Mapped[int] = mapped_column(ForeignKey("timetable_generations.id", ondelete="CASCADE"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id", ondelete="CASCADE"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"))
    room_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"))
    day: Mapped[int] = mapped_column(Integer)
    start_period: Mapped[int] = mapped_column(Integer)
    duration: Mapped[int] = mapped_column(Integer, default=1)
    session_no: Mapped[int] = mapped_column(Integer, default=0)
    generation: Mapped[Generation] = relationship(back_populates="sessions")
    __table_args__ = (
        Index("ix_sess_gen_fac", "generation_id", "faculty_id", "day"),
        Index("ix_sess_gen_room", "generation_id", "room_id", "day"),
        Index("ix_sess_gen_batch", "generation_id", "batch_id", "day"),
        CheckConstraint("duration >= 1", name="ck_sess_duration"),
    )


class PublicationHistory(Base):
    __tablename__ = "publication_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_generations.id", ondelete="SET NULL"), nullable=True, index=True)
    generation_name: Mapped[str] = mapped_column(String(200), default="")
    action: Mapped[str] = mapped_column(String(30))  # generated|saved_draft|published|archived|edited
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConflictReport(Base):
    __tablename__ = "conflict_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), index=True)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_generations.id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | resolved
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
