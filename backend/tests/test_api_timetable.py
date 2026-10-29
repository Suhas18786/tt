"""End-to-end generation, manual edit, publish and export through the API (needs ortools)."""
import pytest

pytest.importorskip("ortools")
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from app import seed_data as sd  # noqa: E402


@pytest.fixture(scope="module")
def client():
    from app.database import Base, SessionLocal, engine
    from app.main import app
    from app.seed import seed
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    with TestClient(app) as c:
        yield c


def hdr(client, email, pw):
    return {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": email, "password": pw}).json()["access_token"]}


@pytest.fixture(scope="module")
def admin(client):
    return hdr(client, sd.ADMIN[0], sd.ADMIN[2])


@pytest.fixture(scope="module")
def generated(client, admin):
    r = client.post("/api/timetables/generate", headers=admin, json={"name": "Odd Sem 2026", "time_limit_seconds": 30})
    assert r.status_code == 201, r.text
    return r.json()


def test_generate_saves_complete_conflict_free_timetable(client, admin, generated):
    assert generated["status"] == "preview"
    assert generated["validation"]["ok"] and not generated["validation"]["violations"]
    assert generated["report"]["unscheduled"] == [] and len(generated["sessions"]) == generated["expected_sessions"]
    again = client.get(f"/api/timetables/{generated['id']}", headers=admin).json()   # saved & retrievable
    assert len(again["sessions"]) == len(generated["sessions"])


def test_manual_move_is_validated(client, admin, generated):
    gid = generated["id"]
    sess = generated["sessions"]
    a = next(s for s in sess if s["duration"] == 1)
    other = next(s for s in sess if s["faculty_id"] == a["faculty_id"] and s["id"] != a["id"] and s["duration"] == 1
                 and (s["day"], s["start_period"]) != (a["day"], a["start_period"]))
    bad = client.post(f"/api/timetables/{gid}/move", headers=admin, json={
        "session_id": a["id"], "day": other["day"], "start_period": other["start_period"]})
    assert bad.status_code == 422
    codes = {v["code"] for v in bad.json()["detail"]["violations"]}
    assert "faculty_conflict" in codes
    lunch = client.post(f"/api/timetables/{gid}/move", headers=admin, json={"session_id": a["id"], "day": 0, "start_period": 4})
    assert lunch.status_code == 422 and any(v["code"] == "break_period" for v in lunch.json()["detail"]["violations"])

    moved = None
    for d in range(5):
        for p in (0, 1, 2, 3, 5, 6, 7):
            r = client.post(f"/api/timetables/{gid}/move", headers=admin, json={
                "session_id": a["id"], "day": d, "start_period": p, "dry_run": True})
            if r.status_code == 200 and (d, p) != (a["day"], a["start_period"]):
                moved = (d, p)
                break
        if moved:
            break
    assert moved, "expected at least one valid alternative slot"
    ok = client.post(f"/api/timetables/{gid}/move", headers=admin, json={"session_id": a["id"], "day": moved[0], "start_period": moved[1]})
    assert ok.status_code == 200
    after = client.get(f"/api/timetables/{gid}", headers=admin).json()
    s = next(x for x in after["sessions"] if x["id"] == a["id"])
    assert (s["day"], s["start_period"]) == moved and after["validation"]["ok"]


def test_publish_export_and_faculty_view(client, admin, generated):
    gid = generated["id"]
    assert client.post(f"/api/timetables/{gid}/save-draft", headers=admin).json()["status"] == "draft"
    assert client.post(f"/api/timetables/{gid}/publish", headers=admin).json()["status"] == "published"
    s = generated["sessions"][0]
    assert client.post(f"/api/timetables/{gid}/move", headers=admin, json={"session_id": s["id"], "day": 0, "start_period": 0}).status_code == 409
    assert client.delete(f"/api/timetables/{gid}", headers=admin).status_code == 409

    xl = client.get(f"/api/timetables/{gid}/export?format=xlsx&view=faculty", headers=admin)
    assert xl.status_code == 200 and xl.content[:2] == b"PK"
    pdf = client.get(f"/api/timetables/{gid}/export?format=pdf&view=batch", headers=admin)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    fh = hdr(client, sd.faculty_email("Dr. Anita Rao"), sd.FACULTY_PASSWORD)
    mine = client.get("/api/me/timetable", headers=fh).json()
    assert mine["sessions"] and all(x["faculty_name"] == "Dr. Anita Rao" for x in mine["sessions"])
    assert client.get("/api/me/workload", headers=fh).json()["total_hours"] == 7
    assert client.get(f"/api/timetables/{gid}", headers=fh).status_code == 200

    dash = client.get("/api/dashboard", headers=admin).json()
    assert dash["generation"]["status"] == "published" and dash["sessions"]["unscheduled"] == 0
    assert dash["conflicts"] == [] and dash["room_utilization"]
    assert client.get("/api/reports/workload", headers=admin).json()["rows"]
    assert client.get("/api/reports/room", headers=admin).json()["groups"]


def test_republishing_same_batches_archives_previous(client, admin):
    r = client.post("/api/timetables/generate", headers=admin, json={"name": "Second", "time_limit_seconds": 30})
    new = r.json()
    assert client.post(f"/api/timetables/{new['id']}/publish", headers=admin).status_code == 200
    published = client.get("/api/timetables?status=published", headers=admin).json()
    assert [g["id"] for g in published] == [new["id"]]
    assert any(h["action"] == "archived" for h in client.get("/api/timetables/history", headers=admin).json())


def test_infeasible_request_returns_report_and_cannot_be_published(client, admin):
    r = client.post("/api/timetables/generate", headers=admin, json={
        "name": "Impossible", "batch_ids": [1], "max_daily_hours_override": 1, "time_limit_seconds": 15})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "infeasible"
    assert body["report"]["unscheduled"] and all(u["reason"] for u in body["report"]["unscheduled"])
    assert body["validation"]["violations"] == []        # partial timetable itself has no hard violations
    pub = client.post(f"/api/timetables/{body['id']}/publish", headers=admin)
    assert pub.status_code in (409, 422)


def test_different_departments_have_independent_timetables(client, admin):
    lookups = client.get("/api/lookups", headers=admin).json()
    dept = {d["code"]: d["id"] for d in lookups["departments"]}
    cse = client.post("/api/timetables/generate", headers=admin, json={"name": "CSE only", "department_id": dept["CSE"], "time_limit_seconds": 30}).json()
    assert cse["status"] == "preview" and all(s["department_id"] == dept["CSE"] for s in cse["sessions"])
    ece = client.post("/api/timetables/generate", headers=admin, json={"name": "ECE only", "department_id": dept["ECE"], "time_limit_seconds": 30}).json()
    assert ece["status"] == "preview" and all(s["department_id"] == dept["ECE"] for s in ece["sessions"])
