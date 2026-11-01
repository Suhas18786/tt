from app.services.csv_parse import PLAN_TEMPLATE, ROOMS_TEMPLATE, parse_rooms, parse_teaching_plan

HEAD = "batch_code,department_code,subject_code,subject_name,weekly_hours,faculty_name,subject_type\n"


def test_templates_parse_cleanly():
    recs, errs = parse_teaching_plan(PLAN_TEMPLATE)
    assert errs == [] and len(recs) == 1 and recs[0]["faculty_code"] == "F-ASHA"
    assert parse_rooms(ROOMS_TEMPLATE)[1] == []


def test_lab_defaults_to_consecutive_block_in_lab_room():
    recs, errs = parse_teaching_plan(HEAD + "B1,CSE,L1,Net Lab,2,Dr A,lab\n")
    assert errs == [] and recs[0]["session_duration"] == 2
    assert recs[0]["consecutive_required"] and recs[0]["room_type"] == "laboratory"


def test_bad_rows_are_reported_with_line_numbers():
    text = HEAD + "B1,CSE,X1,T,99,Dr A,lecture\nB1,CSE,X2,T,2,Dr A,weird\n,CSE,X3,T,2,Dr A,lecture\n"
    recs, errs = parse_teaching_plan(text)
    assert recs == []
    assert any(e.startswith("Line 2") and "weekly_hours" in e for e in errs)
    assert any(e.startswith("Line 3") and "subject_type" in e for e in errs)
    assert any(e.startswith("Line 4") and "batch_code" in e for e in errs)


def test_duplicate_batch_subject_and_missing_columns():
    recs, errs = parse_teaching_plan(HEAD + "B1,CSE,X1,T,2,Dr A,lecture\nB1,CSE,X1,T,2,Dr A,lecture\n")
    assert len(recs) == 1 and any("already has subject" in e for e in errs)
    assert "Missing column" in parse_teaching_plan("a,b\n1,2")[1][0]
    assert parse_teaching_plan("")[1] == ["The file is empty."]


def test_rooms_validation():
    recs, errs = parse_rooms("building,room_number,capacity\nA,1,0\nA,2,50\nA,2,50\n")
    assert len(recs) == 1 and len(errs) == 2
