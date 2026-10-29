"""Realistic sample data (pure Python so it can also be used in tests)."""

DEPARTMENTS = [("CSE", "Computer Science & Engineering"), ("ECE", "Electronics & Communication Engineering"),
               ("MECH", "Mechanical Engineering"), ("MATH", "Mathematics & Sciences")]

ACADEMIC_YEAR = "2026-27"
SEMESTERS = [(1, "Semester 1"), (3, "Semester 3"), (5, "Semester 5"), (7, "Semester 7")]

# code, name, dept, max/day, max/week
FACULTY = [
    ("F-CSE-01", "Dr. Anita Rao", "CSE", 4, 18),
    ("F-CSE-02", "Prof. Arjun Das", "CSE", 4, 16),
    ("F-CSE-03", "Prof. Kavya Nair", "CSE", 4, 16),
    ("F-CSE-04", "Prof. Rahul Verma", "CSE", 5, 18),
    ("F-CSE-05", "Dr. Vikram Shah", "CSE", 4, 18),
    ("F-CSE-06", "Dr. Meera Iyer", "CSE", 5, 18),
    ("F-CSE-07", "Dr. Sunil Kumar", "CSE", 4, 16),
    ("F-ECE-01", "Dr. Neha Kapoor", "ECE", 5, 18),
    ("F-ECE-02", "Prof. Ravi Teja", "ECE", 5, 18),
    ("F-ECE-03", "Dr. Farhan Ali", "ECE", 4, 16),
    ("F-MEC-01", "Dr. Suresh Patel", "MECH", 4, 16),
    ("F-MEC-02", "Prof. Lakshmi Narayan", "MECH", 5, 18),
    ("F-MAT-01", "Dr. Priya Menon", "MATH", 4, 16),
    ("F-MAT-02", "Dr. Deepak Joshi", "MATH", 4, 16),
]

# code, name, dept, semester, type, weekly hours, duration, room type, consecutive, difficulty, equipment
SUBJECTS = [
    ("CS301", "Data Structures", "CSE", 3, "lecture", 4, 1, "lecture_room", False, 2, []),
    ("CS302", "Discrete Mathematics", "CSE", 3, "lecture", 3, 1, "lecture_room", False, 3, []),
    ("CS303", "Digital Logic Design", "CSE", 3, "lecture", 3, 1, "lecture_room", False, 2, []),
    ("CS304", "Object Oriented Programming", "CSE", 3, "lecture", 3, 1, "lecture_room", False, 1, []),
    ("CS305", "Data Structures Lab", "CSE", 3, "lab", 4, 2, "computer_lab", True, 1, ["computers"]),
    ("MA301", "Probability & Statistics", "MATH", 3, "lecture", 3, 1, "lecture_room", False, 3, []),
    ("CS501", "Operating Systems", "CSE", 5, "lecture", 4, 1, "lecture_room", False, 3, []),
    ("CS502", "Database Management Systems", "CSE", 5, "lecture", 4, 1, "lecture_room", False, 2, []),
    ("CS503", "Computer Networks", "CSE", 5, "lecture", 3, 1, "lecture_room", False, 2, []),
    ("CS504", "Software Engineering", "CSE", 5, "lecture", 3, 1, "lecture_room", False, 1, []),
    ("CS505", "DBMS Lab", "CSE", 5, "lab", 4, 2, "computer_lab", True, 1, ["computers"]),
    ("CS506", "Machine Learning", "CSE", 5, "lecture", 3, 1, "lecture_room", False, 3, []),
    ("EC301", "Signals & Systems", "ECE", 3, "lecture", 4, 1, "lecture_room", False, 3, []),
    ("EC302", "Analog Circuits", "ECE", 3, "lecture", 4, 1, "lecture_room", False, 2, []),
    ("EC303", "Network Theory", "ECE", 3, "lecture", 3, 1, "lecture_room", False, 2, []),
    ("MA302", "Engineering Mathematics III", "MATH", 3, "lecture", 3, 1, "lecture_room", False, 3, []),
    ("EC304", "Analog Circuits Lab", "ECE", 3, "lab", 4, 2, "laboratory", True, 1, ["oscilloscope"]),
    ("EC501", "Digital Signal Processing", "ECE", 5, "lecture", 4, 1, "lecture_room", False, 3, []),
    ("EC502", "Microprocessors", "ECE", 5, "lecture", 4, 1, "lecture_room", False, 2, []),
    ("EC503", "Electromagnetic Waves", "ECE", 5, "lecture", 3, 1, "lecture_room", False, 3, []),
    ("EC504", "Communication Systems", "ECE", 5, "lecture", 3, 1, "lecture_room", False, 2, []),
    ("EC505", "DSP Lab", "ECE", 5, "lab", 4, 2, "computer_lab", True, 1, ["computers"]),
    ("ME301", "Thermodynamics", "MECH", 3, "lecture", 4, 1, "lecture_room", False, 3, []),
    ("ME302", "Fluid Mechanics", "MECH", 3, "lecture", 4, 1, "lecture_room", False, 2, []),
    ("ME303", "Strength of Materials", "MECH", 3, "lecture", 3, 1, "lecture_room", False, 2, []),
    ("ME304", "Workshop Practice Lab", "MECH", 3, "lab", 4, 2, "laboratory", True, 1, ["lathe"]),
]

# code, name, dept, semester number, strength
BATCHES = [
    ("CSE-S3-A", "CSE Sem 3 - Section A", "CSE", 3, "A", 60),
    ("CSE-S3-B", "CSE Sem 3 - Section B", "CSE", 3, "B", 58),
    ("CSE-S5-A", "CSE Sem 5 - Section A", "CSE", 5, "A", 55),
    ("ECE-S3-A", "ECE Sem 3 - Section A", "ECE", 3, "A", 50),
    ("ECE-S5-A", "ECE Sem 5 - Section A", "ECE", 5, "A", 48),
    ("MECH-S3-A", "MECH Sem 3 - Section A", "MECH", 3, "A", 45),
]

# building, number, type, capacity, equipment
ROOMS = [
    ("Main Block", "LH-101", "lecture_room", 70, ["projector"]),
    ("Main Block", "LH-102", "lecture_room", 70, ["projector"]),
    ("Main Block", "LH-103", "lecture_room", 60, ["projector"]),
    ("Main Block", "LH-201", "lecture_room", 60, ["projector"]),
    ("Main Block", "LH-202", "lecture_room", 50, []),
    ("Main Block", "LH-203", "lecture_room", 50, []),
    ("CS Block", "CL-1", "computer_lab", 65, ["computers", "projector"]),
    ("CS Block", "CL-2", "computer_lab", 65, ["computers", "projector"]),
    ("CS Block", "CL-3", "computer_lab", 62, ["computers"]),
    ("EC Block", "EL-1", "laboratory", 60, ["oscilloscope", "signal generator"]),
    ("EC Block", "EL-2", "laboratory", 60, ["oscilloscope"]),
    ("Workshop", "ML-1", "laboratory", 50, ["lathe", "milling machine"]),
]

# batch, subject, faculty
ASSIGNMENTS = [
    ("CSE-S3-A", "CS301", "F-CSE-01"), ("CSE-S3-A", "CS302", "F-MAT-01"), ("CSE-S3-A", "CS303", "F-CSE-02"),
    ("CSE-S3-A", "CS304", "F-CSE-01"), ("CSE-S3-A", "CS305", "F-CSE-03"), ("CSE-S3-A", "MA301", "F-MAT-01"),
    ("CSE-S3-B", "CS301", "F-CSE-04"), ("CSE-S3-B", "CS302", "F-MAT-01"), ("CSE-S3-B", "CS303", "F-CSE-02"),
    ("CSE-S3-B", "CS304", "F-CSE-03"), ("CSE-S3-B", "CS305", "F-CSE-04"), ("CSE-S3-B", "MA301", "F-MAT-02"),
    ("CSE-S5-A", "CS501", "F-CSE-05"), ("CSE-S5-A", "CS502", "F-CSE-06"), ("CSE-S5-A", "CS503", "F-CSE-05"),
    ("CSE-S5-A", "CS504", "F-CSE-07"), ("CSE-S5-A", "CS505", "F-CSE-06"), ("CSE-S5-A", "CS506", "F-CSE-07"),
    ("ECE-S3-A", "EC301", "F-ECE-01"), ("ECE-S3-A", "EC302", "F-ECE-02"), ("ECE-S3-A", "EC303", "F-ECE-01"),
    ("ECE-S3-A", "MA302", "F-MAT-02"), ("ECE-S3-A", "EC304", "F-ECE-02"),
    ("ECE-S5-A", "EC501", "F-ECE-01"), ("ECE-S5-A", "EC502", "F-ECE-03"), ("ECE-S5-A", "EC503", "F-ECE-02"),
    ("ECE-S5-A", "EC504", "F-ECE-03"), ("ECE-S5-A", "EC505", "F-ECE-01"),
    ("MECH-S3-A", "ME301", "F-MEC-01"), ("MECH-S3-A", "ME302", "F-MEC-02"), ("MECH-S3-A", "ME303", "F-MEC-01"),
    ("MECH-S3-A", "MA302", "F-MAT-02"), ("MECH-S3-A", "ME304", "F-MEC-02"),
]

# extra qualifications beyond the assigned subjects
EXTRA_QUALIFICATIONS = [("F-CSE-04", "CS303"), ("F-CSE-02", "CS302"), ("F-CSE-05", "CS502"), ("F-MAT-01", "MA302")]

# (day, period) the faculty member cannot teach; day 0 = Monday
UNAVAILABLE = {
    "F-ECE-01": [(4, 5), (4, 6), (4, 7)],
    "F-MAT-01": [(0, 0), (0, 1)],
    "F-MAT-02": [(2, p) for p in (0, 1, 2, 3, 5, 6, 7)],
    "F-CSE-05": [(1, 5), (1, 6), (1, 7)],
}
PREFERRED = {
    "F-CSE-01": [(d, p) for d in range(5) for p in (0, 1, 2, 3)],
    "F-CSE-02": [(d, p) for d in (1, 3) for p in (0, 1, 2, 3)],
    "F-CSE-06": [(d, p) for d in range(5) for p in (5, 6, 7)],
}

ADMIN = ("admin@university.edu", "System Administrator", "Admin@123")
FACULTY_PASSWORD = "Faculty@123"


def faculty_email(name: str) -> str:
    parts = [p for p in name.replace(".", "").split() if p not in ("Dr", "Prof")]
    return ".".join(p.lower() for p in parts) + "@university.edu"
