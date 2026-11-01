"""CSV parsing and validation for bulk import (pure Python, no database)."""
import csv
import io
import re

ROOM_TYPES = ("lecture_room", "computer_lab", "laboratory")
SUBJECT_TYPES = ("lecture", "tutorial", "lab")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ROWS = 2000

PLAN_REQUIRED = ["batch_code", "department_code", "subject_code", "subject_name", "weekly_hours", "faculty_name"]
PLAN_OPTIONAL = ["batch_name", "strength", "semester", "subject_type", "room_type", "session_duration", "difficulty",
                 "faculty_code", "faculty_email", "max_hours_per_week", "max_hours_per_day"]
ROOM_REQUIRED = ["building", "room_number", "capacity"]
ROOM_OPTIONAL = ["room_type"]

PLAN_TEMPLATE = (",".join(PLAN_REQUIRED + PLAN_OPTIONAL) + "\n"
                 "CSE-S5,CSE,CS501,Operating Systems,3,Dr. Asha Rao,CSE Semester 5 A,60,5,lecture,lecture_room,1,2,"
                 "F-ASHA,asha.rao@university.edu,18,5\n")
ROOMS_TEMPLATE = ",".join(ROOM_REQUIRED + ROOM_OPTIONAL) + "\nMain Block,LH-101,70,lecture_room\n"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def read_csv(text: str, required: list[str], optional: list[str]):
    """-> (rows, errors). Each row is a dict with normalised keys plus '_line'. Errors are human-readable strings."""
    errors: list[str] = []
    text = text.lstrip("﻿")
    if not text.strip():
        return [], ["The file is empty."]
    reader = csv.DictReader(io.StringIO(text))
    headers = [(h or "").strip().lower().replace(" ", "_") for h in (reader.fieldnames or [])]
    reader.fieldnames = headers
    missing = [c for c in required if c not in headers]
    if missing:
        return [], [f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(required + optional)}."]
    rows = []
    for i, raw in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            errors.append(f"Too many rows; the limit is {MAX_ROWS}.")
            break
        row = {k: (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        row["_line"] = i
        rows.append(row)
    if not rows and not errors:
        errors.append("The file has a header but no data rows.")
    return rows, errors


def _int(row, key, default, lo, hi, errors):
    raw = row.get(key, "")
    if raw == "":
        return default
    try:
        v = int(float(raw))
    except ValueError:
        errors.append(f"Line {row['_line']}: {key} must be a number (got '{raw}').")
        return default
    if not lo <= v <= hi:
        errors.append(f"Line {row['_line']}: {key} must be between {lo} and {hi} (got {v}).")
    return v


def parse_teaching_plan(text: str):
    """-> (records, errors). A record = one batch x subject x faculty assignment with its supporting data."""
    rows, errors = read_csv(text, PLAN_REQUIRED, PLAN_OPTIONAL)
    if errors and not rows:
        return [], errors
    records, seen = [], set()
    for r in rows:
        ln = r["_line"]
        for col in PLAN_REQUIRED:
            if not r.get(col):
                errors.append(f"Line {ln}: {col} is empty.")
        if any(not r.get(c) for c in PLAN_REQUIRED):
            continue
        stype = (r.get("subject_type") or "lecture").lower()
        if stype not in SUBJECT_TYPES:
            errors.append(f"Line {ln}: subject_type must be one of {', '.join(SUBJECT_TYPES)} (got '{stype}').")
            continue
        default_room = "laboratory" if stype == "lab" else "lecture_room"
        rtype = (r.get("room_type") or default_room).lower()
        if rtype not in ROOM_TYPES:
            errors.append(f"Line {ln}: room_type must be one of {', '.join(ROOM_TYPES)} (got '{rtype}').")
            continue
        before = len(errors)
        weekly = _int(r, "weekly_hours", 0, 1, 30, errors)
        duration = _int(r, "session_duration", 2 if stype == "lab" else 1, 1, 6, errors)
        strength = _int(r, "strength", 60, 1, 1000, errors)
        semester = _int(r, "semester", 1, 1, 12, errors)
        difficulty = _int(r, "difficulty", 2, 1, 3, errors)
        per_week = _int(r, "max_hours_per_week", 18, 1, 60, errors)
        per_day = _int(r, "max_hours_per_day", 5, 1, 12, errors)
        email = r.get("faculty_email", "")
        if email and not EMAIL_RE.match(email):
            errors.append(f"Line {ln}: faculty_email '{email}' is not a valid email address.")
        if len(errors) > before:
            continue
        key = (r["batch_code"], r["subject_code"])
        if key in seen:
            errors.append(f"Line {ln}: batch {r['batch_code']} already has subject {r['subject_code']} earlier in this file.")
            continue
        seen.add(key)
        fcode = r.get("faculty_code") or f"F-{_slug(r['faculty_name']).upper()}"[:30]
        records.append({
            "line": ln, "batch_code": r["batch_code"][:30], "batch_name": (r.get("batch_name") or r["batch_code"])[:200],
            "strength": strength, "semester": semester, "department_code": r["department_code"][:20],
            "subject_code": r["subject_code"][:30], "subject_name": r["subject_name"][:200], "subject_type": stype,
            "weekly_hours": weekly, "session_duration": duration, "room_type": rtype, "difficulty": difficulty,
            "consecutive_required": stype == "lab" or duration > 1,
            "faculty_code": fcode, "faculty_name": r["faculty_name"][:200],
            "faculty_email": email or f"{_slug(fcode)}@imported.example.edu",
            "max_hours_per_week": per_week, "max_hours_per_day": per_day,
        })
    return records, errors


def parse_rooms(text: str):
    rows, errors = read_csv(text, ROOM_REQUIRED, ROOM_OPTIONAL)
    if errors and not rows:
        return [], errors
    records, seen = [], set()
    for r in rows:
        ln = r["_line"]
        if not (r.get("building") and r.get("room_number")):
            errors.append(f"Line {ln}: building and room_number are required.")
            continue
        rtype = (r.get("room_type") or "lecture_room").lower()
        if rtype not in ROOM_TYPES:
            errors.append(f"Line {ln}: room_type must be one of {', '.join(ROOM_TYPES)} (got '{rtype}').")
            continue
        before = len(errors)
        cap = _int(r, "capacity", 0, 1, 2000, errors)
        if len(errors) > before:
            continue
        key = (r["building"], r["room_number"])
        if key in seen:
            errors.append(f"Line {ln}: room {r['building']} {r['room_number']} appears twice in this file.")
            continue
        seen.add(key)
        records.append({"line": ln, "building": r["building"][:100], "room_number": r["room_number"][:30],
                        "room_type": rtype, "capacity": cap})
    return records, errors
