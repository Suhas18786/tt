"""Applies parsed CSV records to the database. Existing records (matched by code) are reused, never overwritten."""
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from .. import models as m
from .csv_parse import parse_rooms, parse_teaching_plan


class ImportFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors


def _current_year(db: Session) -> m.AcademicYear:
    y = db.query(m.AcademicYear).filter_by(is_current=True).first() or db.query(m.AcademicYear).first()
    if y:
        return y
    start = date.today().year
    y = m.AcademicYear(name=f"{start}-{str(start + 1)[-2:]}", is_current=True)
    db.add(y)
    db.flush()
    return y


def import_teaching_plan(db: Session, text: str, dry_run: bool = False) -> dict:
    records, errors = parse_teaching_plan(text)
    if errors:
        raise ImportFailed(errors)
    year = _current_year(db)
    made = defaultdict(int)
    reused = defaultdict(int)
    depts, sems, batches, subjects, faculty = {}, {}, {}, {}, {}
    hours = defaultdict(int)
    faculty_limit = {}

    def get_dept(code):
        if code not in depts:
            d = db.query(m.Department).filter_by(code=code).first()
            if d:
                reused["departments"] += 1
            else:
                name = code if not db.query(m.Department).filter_by(name=code).first() else f"{code} department"
                d = m.Department(code=code, name=name)
                db.add(d)
                db.flush()
                made["departments"] += 1
            depts[code] = d
        return depts[code]

    def get_sem(num):
        if num not in sems:
            s = db.query(m.Semester).filter_by(academic_year_id=year.id, number=num).first()
            if not s:
                s = m.Semester(academic_year_id=year.id, number=num, name=f"Semester {num}")
                db.add(s)
                db.flush()
                made["semesters"] += 1
            sems[num] = s
        return sems[num]

    for r in records:
        ln = r["line"]
        dept = get_dept(r["department_code"])
        b = batches.get(r["batch_code"]) or db.query(m.Batch).filter_by(code=r["batch_code"]).first()
        if b:
            reused["batches"] += 1 if r["batch_code"] not in batches else 0
        else:
            b = m.Batch(code=r["batch_code"], name=r["batch_name"], section="A", department_id=dept.id,
                        semester_id=get_sem(r["semester"]).id, strength=r["strength"])
            db.add(b)
            db.flush()
            made["batches"] += 1
        batches[r["batch_code"]] = b

        s = subjects.get(r["subject_code"]) or db.query(m.Subject).filter_by(code=r["subject_code"]).first()
        if s:
            reused["subjects"] += 1 if r["subject_code"] not in subjects else 0
        else:
            s = m.Subject(code=r["subject_code"], name=r["subject_name"], department_id=dept.id,
                          semester_number=r["semester"], subject_type=r["subject_type"], weekly_hours=r["weekly_hours"],
                          session_duration=r["session_duration"], room_type=r["room_type"],
                          consecutive_required=r["consecutive_required"], difficulty=r["difficulty"],
                          required_equipment=[])
            db.add(s)
            db.flush()
            made["subjects"] += 1
        subjects[r["subject_code"]] = s

        f = faculty.get(r["faculty_code"]) or db.query(m.Faculty).filter_by(faculty_code=r["faculty_code"]).first()
        if f:
            reused["faculty"] += 1 if r["faculty_code"] not in faculty else 0
        else:
            clash = db.query(m.Faculty).filter_by(email=r["faculty_email"]).first()
            if clash:
                raise ImportFailed([f"Line {ln}: email {r['faculty_email']} already belongs to faculty {clash.faculty_code}; "
                                    f"use that faculty_code or a different email."])
            f = m.Faculty(faculty_code=r["faculty_code"], full_name=r["faculty_name"], email=r["faculty_email"],
                          department_id=dept.id, max_hours_per_day=r["max_hours_per_day"],
                          max_hours_per_week=r["max_hours_per_week"])
            db.add(f)
            db.flush()
            made["faculty"] += 1
        faculty[r["faculty_code"]] = f
        faculty_limit[f.id] = (f.faculty_code, f.max_hours_per_week)

        if not db.get(m.FacultyQualification, (f.id, s.id)):
            db.add(m.FacultyQualification(faculty_id=f.id, subject_id=s.id))
            db.flush()
        if db.query(m.TeachingAssignment).filter_by(batch_id=b.id, subject_id=s.id).first():
            reused["assignments"] += 1
        else:
            db.add(m.TeachingAssignment(batch_id=b.id, subject_id=s.id, faculty_id=f.id))
            db.flush()
            made["assignments"] += 1
            hours[f.id] += s.weekly_hours

    warnings = []
    for fid, h in hours.items():
        code, limit = faculty_limit[fid]
        if h > limit:
            warnings.append(f"Faculty {code} is assigned {h} hours a week but their limit is {limit}; "
                            f"the generator will report some sessions as unscheduled.")
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return {"dry_run": dry_run, "rows": len(records), "created": dict(made), "already_existed": dict(reused),
            "warnings": warnings}


def import_rooms(db: Session, text: str, dry_run: bool = False) -> dict:
    records, errors = parse_rooms(text)
    if errors:
        raise ImportFailed(errors)
    created = existed = 0
    for r in records:
        if db.query(m.Classroom).filter_by(building=r["building"], room_number=r["room_number"]).first():
            existed += 1
            continue
        db.add(m.Classroom(building=r["building"], room_number=r["room_number"], room_type=r["room_type"],
                           capacity=r["capacity"], equipment=[]))
        created += 1
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return {"dry_run": dry_run, "rows": len(records), "created": {"classrooms": created},
            "already_existed": {"classrooms": existed}, "warnings": []}
