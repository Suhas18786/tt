"""Loads the B.Tech-2024 5th-semester course list (11 programmes) as a ready-to-run dataset.

The source is an exam timetable, so it has no faculty, rooms or weekly hours. These are filled with
simple assumptions: one batch per programme, one faculty per distinct course code, 3 lecture periods
per week per course, and a pool of lecture rooms. Safe to call more than once.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

from sqlalchemy.orm import Session

from .. import models as m

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "btech2024_sem5_courses.csv"
WEEKLY_HOURS = 3
ROOMS = [("Main Block", f"LH-{n}", 70) for n in range(101, 113)]


def read_rows(path: Path = CSV_PATH) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(fh)]


def _slug(code: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", code.lower())


def load_btech_sample(db: Session, rows: list[dict] | None = None) -> dict:
    rows = rows if rows is not None else read_rows()
    if db.query(m.Batch).filter(m.Batch.code.like("%-S5")).filter(m.Batch.name.like("B.Tech 2024%")).count():
        return {"skipped": True, "message": "The B.Tech 2024 sample is already loaded."}

    year = db.query(m.AcademicYear).filter_by(is_current=True).first() or db.query(m.AcademicYear).first()
    if not year:
        year = m.AcademicYear(name="2024-25", is_current=True)
        db.add(year)
        db.flush()
    sem = db.query(m.Semester).filter_by(academic_year_id=year.id, number=5).first()
    if not sem:
        sem = m.Semester(academic_year_id=year.id, number=5, name="Semester 5")
        db.add(sem)
        db.flush()

    # distinct (programme, course) pairs; the first title wins when a code is repeated in a programme
    by_prog: dict[str, dict[str, str]] = defaultdict(dict)
    for r in rows:
        by_prog[r["programme"]].setdefault(r["course_code"], r["course_title"])
    programmes = list(by_prog)
    courses_of: dict[str, list[str]] = defaultdict(list)   # course code -> programmes using it
    titles: dict[str, str] = {}
    first_prog: dict[str, str] = {}
    for p in programmes:
        for code, title in by_prog[p].items():
            courses_of[code].append(p)
            titles.setdefault(code, title)
            first_prog.setdefault(code, p)

    depts = {}
    for p in programmes:
        d = db.query(m.Department).filter_by(code=f"BT-{p}"[:20]).first()
        if not d:
            d = m.Department(code=f"BT-{p}"[:20], name=f"B.Tech {p} (2024 batch)")
            db.add(d)
        depts[p] = d
    db.flush()

    subjects, faculty = {}, {}
    for code, title in titles.items():
        s = db.query(m.Subject).filter_by(code=code).first()
        if not s:
            s = m.Subject(code=code, name=title[:200], department_id=depts[first_prog[code]].id, semester_number=5,
                          subject_type="lecture", weekly_hours=WEEKLY_HOURS, session_duration=1,
                          room_type="lecture_room", consecutive_required=False, difficulty=2, required_equipment=[])
            db.add(s)
        subjects[code] = s
        n = len(courses_of[code])
        email = f"{_slug(code)}@btech.example.edu"
        f = db.query(m.Faculty).filter_by(faculty_code=f"F-{code}"[:30]).first()
        if not f:
            f = m.Faculty(faculty_code=f"F-{code}"[:30], full_name=f"Faculty for {code}", email=email,
                          department_id=depts[first_prog[code]].id,
                          max_hours_per_day=5 if n == 1 else 6, max_hours_per_week=min(60, max(18, WEEKLY_HOURS * n)))
            db.add(f)
        faculty[code] = f
    db.flush()

    for building, number, cap in ROOMS:
        if not db.query(m.Classroom).filter_by(building=building, room_number=number).first():
            db.add(m.Classroom(building=building, room_number=number, room_type="lecture_room",
                               capacity=cap, equipment=[]))
    for code in titles:
        db.add(m.FacultyQualification(faculty_id=faculty[code].id, subject_id=subjects[code].id))
    db.flush()

    n_assign = 0
    for p in programmes:
        b = m.Batch(code=f"{p}-S5"[:30], name=f"B.Tech 2024 {p} Sem 5", section="A",
                    department_id=depts[p].id, semester_id=sem.id, strength=60)
        db.add(b)
        db.flush()
        for code in by_prog[p]:
            db.add(m.TeachingAssignment(batch_id=b.id, subject_id=subjects[code].id, faculty_id=faculty[code].id))
            n_assign += 1
    db.commit()
    return {"skipped": False, "message": "Loaded the B.Tech 2024 semester 5 sample.", "batches": len(programmes),
            "subjects": len(subjects), "faculty": len(faculty), "rooms": len(ROOMS), "assignments": n_assign,
            "sessions": n_assign * WEEKLY_HOURS}
