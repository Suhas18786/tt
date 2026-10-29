"""Seed the database with realistic sample data.   python -m app.seed [--reset]"""
import sys

from sqlalchemy.orm import Session

from . import models as m
from . import seed_data as sd
from .database import Base, SessionLocal, engine
from .scheduler.loader import default_config
from .security import hash_password


def seed(db: Session, with_users: bool = True) -> dict:
    if db.query(m.Department).count():
        return {"skipped": True}
    depts = {}
    for code, name in sd.DEPARTMENTS:
        d = m.Department(code=code, name=name)
        db.add(d)
        depts[code] = d
    year = m.AcademicYear(name=sd.ACADEMIC_YEAR, is_current=True)
    db.add(year)
    db.flush()
    sems = {}
    for num, name in sd.SEMESTERS:
        s = m.Semester(academic_year_id=year.id, number=num, name=name)
        db.add(s)
        sems[num] = s
    db.flush()

    subjects = {}
    for code, name, dept, sem, typ, hours, dur, rtype, consec, diff, equip in sd.SUBJECTS:
        s = m.Subject(code=code, name=name, department_id=depts[dept].id, semester_number=sem, subject_type=typ,
                      weekly_hours=hours, session_duration=dur, room_type=rtype, consecutive_required=consec,
                      difficulty=diff, required_equipment=equip)
        db.add(s)
        subjects[code] = s
    db.flush()

    if with_users:
        email, name, pw = sd.ADMIN
        db.add(m.User(email=email, full_name=name, role="admin", password_hash=hash_password(pw)))

    faculty = {}
    pw_hash = hash_password(sd.FACULTY_PASSWORD) if with_users else None
    for code, name, dept, per_day, per_week in sd.FACULTY:
        user_id = None
        if with_users:
            u = m.User(email=sd.faculty_email(name), full_name=name, role="faculty", password_hash=pw_hash)
            db.add(u)
            db.flush()
            user_id = u.id
        f = m.Faculty(faculty_code=code, full_name=name, email=sd.faculty_email(name), department_id=depts[dept].id,
                      user_id=user_id, max_hours_per_day=per_day, max_hours_per_week=per_week)
        db.add(f)
        faculty[code] = f
    db.flush()

    batches = {}
    for code, name, dept, sem, section, strength in sd.BATCHES:
        b = m.Batch(code=code, name=name, section=section, department_id=depts[dept].id,
                    semester_id=sems[sem].id, strength=strength)
        db.add(b)
        batches[code] = b
    for building, number, rtype, cap, equip in sd.ROOMS:
        db.add(m.Classroom(building=building, room_number=number, room_type=rtype, capacity=cap, equipment=equip))
    db.flush()

    quals = {(f, s) for _b, s, f in sd.ASSIGNMENTS} | set(sd.EXTRA_QUALIFICATIONS)
    for fcode, scode in sorted(quals):
        db.add(m.FacultyQualification(faculty_id=faculty[fcode].id, subject_id=subjects[scode].id))
    for bcode, scode, fcode in sd.ASSIGNMENTS:
        db.add(m.TeachingAssignment(batch_id=batches[bcode].id, subject_id=subjects[scode].id, faculty_id=faculty[fcode].id))
    for fcode, slots in sd.UNAVAILABLE.items():
        for d, p in slots:
            db.add(m.FacultyAvailability(faculty_id=faculty[fcode].id, day=d, period=p, status="unavailable"))
    for fcode, slots in sd.PREFERRED.items():
        for d, p in slots:
            db.add(m.FacultyAvailability(faculty_id=faculty[fcode].id, day=d, period=p, status="preferred"))

    cfg = default_config()
    db.add(m.TimetableConfig(name="default", working_days=cfg["working_days"], periods=cfg["periods"],
                             blocked_slots=cfg["blocked_slots"], weights=cfg["weights"],
                             max_consecutive=cfg["max_consecutive"], time_limit_seconds=cfg["time_limit_seconds"]))
    db.commit()
    return {"skipped": False, "faculty": len(faculty), "subjects": len(subjects), "batches": len(batches)}


if __name__ == "__main__":
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print(seed(session))
