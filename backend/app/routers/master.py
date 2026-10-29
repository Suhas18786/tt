"""Master data: departments, years, semesters, batches, classrooms, subjects, faculty, assignments, config."""
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..crud import make_crud_router
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import (AcademicYear, Batch, Classroom, Department, Faculty, FacultyAvailability,
                      FacultyQualification, RoomBlockedSlot, Semester, Subject, TeachingAssignment,
                      TimetableConfig, User)
from ..schemas import (AcademicYearIn, AcademicYearOut, AssignmentIn, AssignmentOut, AvailabilityIn,
                       BatchIn, BatchOut, ClassroomIn, ClassroomOut, ConfigIn, DepartmentIn,
                       DepartmentOut, FacultyIn, SemesterIn, SemesterOut, SubjectIn, SubjectOut)
from ..scheduler.context import DEFAULT_WEIGHTS
from ..scheduler.loader import get_saved_config
from ..security import hash_password

router = APIRouter()


def _exists(db, model, id_, label):
    if db.get(model, id_) is None:
        raise HTTPException(422, f"{label} {id_} does not exist")


# --- simple entities -----------------------------------------------------------------
router.include_router(make_crud_router(
    prefix="/departments", tag="departments", Model=Department, In=DepartmentIn, Out=DepartmentOut,
    search=["code", "name"], in_use_message="Department still has faculty, subjects or batches."))

router.include_router(make_crud_router(
    prefix="/academic-years", tag="academic years", Model=AcademicYear, In=AcademicYearIn, Out=AcademicYearOut,
    search=["name"], in_use_message="Academic year still has semesters."))


def _sem_validate(db, data, obj):
    _exists(db, AcademicYear, data.academic_year_id, "Academic year")


router.include_router(make_crud_router(
    prefix="/semesters", tag="semesters", Model=Semester, In=SemesterIn, Out=SemesterOut,
    search=["name"], filters=["academic_year_id"], validate=_sem_validate,
    in_use_message="Semester still has student batches."))


def _batch_validate(db, data, obj):
    _exists(db, Department, data.department_id, "Department")
    _exists(db, Semester, data.semester_id, "Semester")


router.include_router(make_crud_router(
    prefix="/batches", tag="batches", Model=Batch, In=BatchIn, Out=BatchOut, search=["code", "name"],
    filters=["department_id", "semester_id"], validate=_batch_validate,
    in_use_message="Batch is used in teaching assignments or timetables."))

router.include_router(make_crud_router(
    prefix="/classrooms", tag="classrooms", Model=Classroom, In=ClassroomIn, Out=ClassroomOut,
    search=["room_number", "building"], filters=["room_type", "building"],
    in_use_message="Room is used in a timetable."))


def _subject_validate(db, data, obj):
    _exists(db, Department, data.department_id, "Department")


router.include_router(make_crud_router(
    prefix="/subjects", tag="subjects", Model=Subject, In=SubjectIn, Out=SubjectOut,
    search=["code", "name"], filters=["department_id", "semester_number", "subject_type", "room_type"],
    validate=_subject_validate, in_use_message="Subject is assigned to batches or used in timetables."))


# --- faculty ---------------------------------------------------------------------------
def _faculty_validate(db: Session, data: FacultyIn, obj):
    _exists(db, Department, data.department_id, "Department")
    found = {r[0] for r in db.query(Subject.id).filter(Subject.id.in_(data.qualified_subject_ids or [0])).all()}
    missing = set(data.qualified_subject_ids) - found
    if missing:
        raise HTTPException(422, f"Unknown subject id(s): {sorted(missing)}")
    if obj is not None and obj.id:
        assigned = {r[0] for r in db.query(TeachingAssignment.subject_id).filter(TeachingAssignment.faculty_id == obj.id)}
        dropped = assigned - set(data.qualified_subject_ids)
        if dropped:
            codes = [s.code for s in db.query(Subject).filter(Subject.id.in_(dropped))]
            raise HTTPException(422, f"Cannot remove qualification for currently assigned subject(s): {', '.join(codes)}")
        load = db.query(func.coalesce(func.sum(Subject.weekly_hours), 0)).join(
            TeachingAssignment, TeachingAssignment.subject_id == Subject.id).filter(
            TeachingAssignment.faculty_id == obj.id).scalar()
        if load > data.max_hours_per_week:
            raise HTTPException(422, f"Faculty already has {load} assigned weekly hours; limit cannot be {data.max_hours_per_week}.")
    email = data.email.lower()
    clash = db.query(User).filter(User.email == email)
    if obj is not None and obj.user_id:
        clash = clash.filter(User.id != obj.user_id)
    if clash.first():
        raise HTTPException(409, "A user account with this email already exists")


def _faculty_after(db: Session, obj: Faculty, data: FacultyIn, creating: bool):
    obj.email = data.email.lower()
    db.query(FacultyQualification).filter(FacultyQualification.faculty_id == obj.id).delete()
    for sid in set(data.qualified_subject_ids):
        db.add(FacultyQualification(faculty_id=obj.id, subject_id=sid))
    if obj.user_id:
        u = db.get(User, obj.user_id)
        u.email, u.full_name = obj.email, obj.full_name
        if data.initial_password:
            u.password_hash = hash_password(data.initial_password)
    elif data.initial_password:
        u = User(email=obj.email, full_name=obj.full_name, role="faculty",
                 password_hash=hash_password(data.initial_password))
        db.add(u)
        db.flush()
        obj.user_id = u.id


def _faculty_serialize(db: Session, objs):
    ids = [o.id for o in objs] or [0]
    quals = defaultdict(list)
    for q in db.query(FacultyQualification).filter(FacultyQualification.faculty_id.in_(ids)):
        quals[q.faculty_id].append(q.subject_id)
    assigned = defaultdict(list)
    rows = (db.query(TeachingAssignment, Subject).join(Subject, Subject.id == TeachingAssignment.subject_id)
            .filter(TeachingAssignment.faculty_id.in_(ids)).all())
    for ta, sub in rows:
        assigned[ta.faculty_id].append({"assignment_id": ta.id, "batch_id": ta.batch_id, "subject_id": sub.id,
                                        "subject_code": sub.code, "hours": sub.weekly_hours})
    return [{
        "id": o.id, "faculty_code": o.faculty_code, "full_name": o.full_name, "email": o.email,
        "department_id": o.department_id, "max_hours_per_day": o.max_hours_per_day,
        "max_hours_per_week": o.max_hours_per_week, "qualified_subject_ids": sorted(quals[o.id]),
        "assigned": assigned[o.id], "assigned_hours": sum(a["hours"] for a in assigned[o.id]),
        "has_login": o.user_id is not None,
    } for o in objs]


def _faculty_before_delete(db: Session, obj: Faculty):
    uid = obj.user_id
    db.query(FacultyQualification).filter(FacultyQualification.faculty_id == obj.id).delete()
    db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id == obj.id).delete()
    if uid:
        obj.user_id = None
        db.flush()
        u = db.get(User, uid)
        if u:
            db.delete(u)


router.include_router(make_crud_router(
    prefix="/faculty", tag="faculty", Model=Faculty, In=FacultyIn, Out=None,
    search=["faculty_code", "full_name", "email"], filters=["department_id"],
    exclude={"qualified_subject_ids", "initial_password"},
    validate=_faculty_validate, after_save=_faculty_after, before_delete=_faculty_before_delete,
    serialize_many=_faculty_serialize, in_use_message="Faculty member has teaching assignments or timetable sessions."))


# --- faculty availability ------------------------------------------------------------------
def _can_edit_faculty(user: User, fac: Faculty):
    if user.role != "admin" and fac.user_id != user.id:
        raise HTTPException(403, "You can only edit your own availability")


@router.get("/faculty/{faculty_id}/availability", tags=["faculty"])
def get_availability(faculty_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fac = db.get(Faculty, faculty_id)
    if fac is None:
        raise HTTPException(404, "Faculty not found")
    _can_edit_faculty(user, fac)
    rows = db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id == faculty_id).all()
    return {"faculty_id": faculty_id, "slots": [{"day": r.day, "period": r.period, "status": r.status} for r in rows]}


@router.put("/faculty/{faculty_id}/availability", tags=["faculty"])
def put_availability(faculty_id: int, data: AvailabilityIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    fac = db.get(Faculty, faculty_id)
    if fac is None:
        raise HTTPException(404, "Faculty not found")
    _can_edit_faculty(user, fac)
    cfg = get_saved_config(db)
    valid_p = {p["index"] for p in cfg["periods"] if p.get("kind", "class") == "class"}
    seen = set()
    for s in data.slots:
        if (s.day, s.period) in seen:
            raise HTTPException(422, f"Duplicate slot day={s.day} period={s.period}")
        seen.add((s.day, s.period))
        if s.period not in valid_p:
            raise HTTPException(422, f"Period {s.period + 1} is not a class period")
        if s.day not in cfg["working_days"]:
            raise HTTPException(422, f"Day {s.day} is not a working day")
    db.query(FacultyAvailability).filter(FacultyAvailability.faculty_id == faculty_id).delete()
    for s in data.slots:
        db.add(FacultyAvailability(faculty_id=faculty_id, day=s.day, period=s.period, status=s.status))
    db.commit()
    return {"faculty_id": faculty_id, "slots": [s.model_dump() for s in data.slots]}


# --- classroom blocked slots ------------------------------------------------------------------
@router.get("/classrooms/{room_id}/blocked", tags=["classrooms"])
def get_room_blocked(room_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(RoomBlockedSlot).filter(RoomBlockedSlot.classroom_id == room_id).all()
    return {"slots": [[r.day, r.period] for r in rows]}


@router.put("/classrooms/{room_id}/blocked", tags=["classrooms"])
def put_room_blocked(room_id: int, body: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.get(Classroom, room_id) is None:
        raise HTTPException(404, "Room not found")
    slots = body.get("slots", [])
    try:
        pairs = {(int(d), int(p)) for d, p in slots}
    except (TypeError, ValueError):
        raise HTTPException(422, "slots must be [[day, period], ...]")
    db.query(RoomBlockedSlot).filter(RoomBlockedSlot.classroom_id == room_id).delete()
    for d, p in sorted(pairs):
        db.add(RoomBlockedSlot(classroom_id=room_id, day=d, period=p))
    db.commit()
    return {"slots": [list(x) for x in sorted(pairs)]}


# --- teaching assignments ------------------------------------------------------------------------
def _assignment_validate(db: Session, data: AssignmentIn, obj):
    _exists(db, Batch, data.batch_id, "Batch")
    sub = db.get(Subject, data.subject_id)
    fac = db.get(Faculty, data.faculty_id)
    if sub is None:
        raise HTTPException(422, f"Subject {data.subject_id} does not exist")
    if fac is None:
        raise HTTPException(422, f"Faculty {data.faculty_id} does not exist")
    if db.get(FacultyQualification, (fac.id, sub.id)) is None:
        raise HTTPException(422, f"{fac.full_name} is not qualified to teach {sub.code}. Add the qualification first.")
    q = db.query(func.coalesce(func.sum(Subject.weekly_hours), 0)).join(
        TeachingAssignment, TeachingAssignment.subject_id == Subject.id).filter(TeachingAssignment.faculty_id == fac.id)
    if obj is not None and obj.id:
        q = q.filter(TeachingAssignment.id != obj.id)
    load = q.scalar() + sub.weekly_hours
    if load > fac.max_hours_per_week:
        raise HTTPException(422, f"{fac.full_name} would have {load} weekly hours (limit {fac.max_hours_per_week}).")


router.include_router(make_crud_router(
    prefix="/assignments", tag="assignments", Model=TeachingAssignment, In=AssignmentIn, Out=AssignmentOut,
    search=[], filters=["batch_id", "subject_id", "faculty_id"], validate=_assignment_validate,
    in_use_message="Assignment is used in a timetable."))


# --- lookups for dropdowns -------------------------------------------------------------------------
@router.get("/lookups", tags=["lookups"])
def lookups(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {
        "departments": [{"id": d.id, "code": d.code, "name": d.name} for d in db.query(Department).order_by(Department.name)],
        "academic_years": [{"id": y.id, "name": y.name, "is_current": y.is_current} for y in db.query(AcademicYear).order_by(AcademicYear.name)],
        "semesters": [{"id": s.id, "academic_year_id": s.academic_year_id, "number": s.number, "name": s.name}
                      for s in db.query(Semester).order_by(Semester.academic_year_id, Semester.number)],
        "batches": [{"id": b.id, "code": b.code, "name": b.name, "department_id": b.department_id,
                     "semester_id": b.semester_id, "strength": b.strength} for b in db.query(Batch).order_by(Batch.code)],
        "faculty": [{"id": f.id, "name": f.full_name, "code": f.faculty_code, "department_id": f.department_id,
                     "max_hours_per_day": f.max_hours_per_day, "max_hours_per_week": f.max_hours_per_week}
                    for f in db.query(Faculty).order_by(Faculty.full_name)],
        "subjects": [{"id": s.id, "code": s.code, "name": s.name, "department_id": s.department_id,
                      "semester_number": s.semester_number, "weekly_hours": s.weekly_hours}
                     for s in db.query(Subject).order_by(Subject.code)],
        "rooms": [{"id": c.id, "label": f"{c.building}-{c.room_number}", "room_type": c.room_type, "capacity": c.capacity}
                  for c in db.query(Classroom).order_by(Classroom.building, Classroom.room_number)],
    }


# --- timetable configuration -------------------------------------------------------------------------
@router.get("/config", tags=["config"])
def get_config(db: Session = Depends(get_db), _=Depends(get_current_user)):
    cfg = get_saved_config(db)
    cfg["weight_keys"] = list(DEFAULT_WEIGHTS.keys())
    return cfg


@router.put("/config", tags=["config"])
def put_config(data: ConfigIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    cfg = get_saved_config(db)
    upd = data.model_dump(exclude_unset=True)
    if "periods" in upd and upd["periods"] is not None:
        upd["periods"] = [dict(p) for p in upd["periods"]]
    for k, v in upd.items():
        if k == "weights" and v is not None:
            cfg["weights"] = {**cfg["weights"], **v}
        elif v is not None or k == "max_daily_hours_override":
            cfg[k] = v
    nper = len(cfg["periods"])
    for d, p in cfg["blocked_slots"]:
        if d not in cfg["working_days"] or p < 0 or p >= nper:
            raise HTTPException(422, f"Blocked slot [{d},{p}] is outside the working days/periods")
    row = db.query(TimetableConfig).order_by(TimetableConfig.id).first() or TimetableConfig()
    row.name = "default"
    row.working_days, row.periods, row.blocked_slots = cfg["working_days"], cfg["periods"], cfg["blocked_slots"]
    row.weights, row.max_consecutive = cfg["weights"], cfg["max_consecutive"]
    row.time_limit_seconds, row.max_daily_hours_override = cfg["time_limit_seconds"], cfg["max_daily_hours_override"]
    db.add(row)
    db.commit()
    return get_saved_config(db)
