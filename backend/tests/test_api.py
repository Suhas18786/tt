"""REST API tests (SQLite in memory). Skipped if FastAPI / SQLAlchemy are not installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("bcrypt")

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


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    return login(client, sd.ADMIN[0], sd.ADMIN[2])


@pytest.fixture(scope="module")
def faculty_user(client):
    return login(client, sd.faculty_email("Dr. Anita Rao"), sd.FACULTY_PASSWORD)


def test_login_rejects_bad_credentials(client):
    assert client.post("/api/auth/login", json={"email": sd.ADMIN[0], "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ghost@x.com", "password": "nope"}).status_code == 401


def test_endpoints_require_authentication_and_roles(client, admin, faculty_user):
    assert client.get("/api/faculty").status_code == 401
    assert client.get("/api/auth/me", headers=admin).json()["role"] == "admin"
    r = client.post("/api/departments", json={"code": "X", "name": "Nope Dept"}, headers=faculty_user)
    assert r.status_code == 403
    assert client.post("/api/timetables/generate", json={}, headers=faculty_user).status_code == 403
    assert client.get("/api/dashboard", headers=faculty_user).status_code == 403


def test_crud_search_pagination_and_validation(client, admin):
    r = client.get("/api/faculty?page=1&page_size=5", headers=admin).json()
    assert r["total"] == len(sd.FACULTY) and len(r["items"]) == 5
    assert client.get("/api/faculty?q=kapoor", headers=admin).json()["total"] == 1
    dept = client.get("/api/departments?q=ECE", headers=admin).json()["items"][0]["id"]
    assert client.get(f"/api/faculty?department_id={dept}", headers=admin).json()["total"] == 3

    created = client.post("/api/classrooms", headers=admin,
                          json={"room_number": "T-1", "building": "Test", "room_type": "lecture_room", "capacity": 30})
    assert created.status_code == 201
    rid = created.json()["id"]
    assert client.post("/api/classrooms", headers=admin, json={"room_number": "T-1", "building": "Test", "capacity": 30}).status_code == 409
    assert client.put(f"/api/classrooms/{rid}", headers=admin, json={"room_number": "T-1", "building": "Test", "capacity": 45}).json()["capacity"] == 45
    assert client.post("/api/classrooms", headers=admin, json={"room_number": "T-2", "building": "Test", "capacity": 0}).status_code == 422
    assert client.delete(f"/api/classrooms/{rid}", headers=admin).status_code == 204
    assert client.get(f"/api/classrooms/{rid}", headers=admin).status_code == 404


def test_subject_validation_rules(client, admin):
    base = {"code": "ZZ1", "name": "Bad Subject", "department_id": 1, "semester_number": 3, "weekly_hours": 2}
    assert client.post("/api/subjects", headers=admin, json={**base, "session_duration": 3}).status_code == 422
    assert client.post("/api/subjects", headers=admin, json={**base, "consecutive_required": True}).status_code == 422
    ok = client.post("/api/subjects", headers=admin, json={**base, "session_duration": 2, "consecutive_required": True, "room_type": "computer_lab"})
    assert ok.status_code == 201
    assert client.delete(f"/api/subjects/{ok.json()['id']}", headers=admin).status_code == 204


def test_faculty_create_with_login_and_delete_protection(client, admin):
    body = {"faculty_code": "F-NEW-1", "full_name": "Dr. New Person", "email": "new.person@university.edu",
            "department_id": 1, "max_hours_per_day": 4, "max_hours_per_week": 12, "initial_password": "Welcome#123"}
    r = client.post("/api/faculty", headers=admin, json=body)
    assert r.status_code == 201 and r.json()["has_login"] is True
    login(client, "new.person@university.edu", "Welcome#123")
    assert client.post("/api/faculty", headers=admin, json={**body, "faculty_code": "F-NEW-2"}).status_code in (409, 422)
    assert client.post("/api/faculty", headers=admin, json={**body, "max_hours_per_day": 9, "max_hours_per_week": 4,
                                                            "faculty_code": "F-X", "email": "x@y.com"}).status_code == 422
    assert client.delete(f"/api/faculty/{r.json()['id']}", headers=admin).status_code == 204
    busy = client.get("/api/faculty?q=Kapoor", headers=admin).json()["items"][0]
    assert client.delete(f"/api/faculty/{busy['id']}", headers=admin).status_code == 409   # has assignments


def test_assignment_requires_qualification_and_respects_weekly_limit(client, admin):
    lookups = client.get("/api/lookups", headers=admin).json()
    fac = next(f for f in lookups["faculty"] if f["name"] == "Dr. Anita Rao")
    sub = next(s for s in lookups["subjects"] if s["code"] == "ME301")
    batch = next(b for b in lookups["batches"] if b["code"] == "CSE-S3-A")
    r = client.post("/api/assignments", headers=admin, json={"batch_id": batch["id"], "subject_id": sub["id"], "faculty_id": fac["id"]})
    assert r.status_code == 422 and "not qualified" in str(r.json())


def test_faculty_can_edit_only_their_own_availability(client, admin, faculty_user):
    me = client.get("/api/auth/me", headers=faculty_user).json()
    slots = {"slots": [{"day": 0, "period": 2, "status": "unavailable"}, {"day": 1, "period": 0, "status": "preferred"}]}
    assert client.put(f"/api/faculty/{me['faculty_id']}/availability", json=slots, headers=faculty_user).status_code == 200
    other = next(f for f in client.get("/api/lookups", headers=admin).json()["faculty"] if f["id"] != me["faculty_id"])
    assert client.put(f"/api/faculty/{other['id']}/availability", json=slots, headers=faculty_user).status_code == 403
    bad = {"slots": [{"day": 0, "period": 4, "status": "unavailable"}]}   # period 5 is lunch
    assert client.put(f"/api/faculty/{me['faculty_id']}/availability", json=bad, headers=faculty_user).status_code == 422
    # restore original seed availability for later tests
    orig = [{"day": d, "period": p, "status": "preferred"} for d, p in sd.PREFERRED["F-CSE-01"]]
    assert client.put(f"/api/faculty/{me['faculty_id']}/availability", json={"slots": orig}, headers=faculty_user).status_code == 200


def test_config_roundtrip_and_validation(client, admin):
    cfg = client.get("/api/config", headers=admin).json()
    assert cfg["working_days"] == [0, 1, 2, 3, 4] and "faculty_spread" in cfg["weights"]
    assert client.put("/api/config", headers=admin, json={"weights": {"nonsense": 1}}).status_code == 422
    assert client.put("/api/config", headers=admin, json={"working_days": [9]}).status_code == 422
    assert client.put("/api/config", headers=admin, json={"weights": {"student_gaps": 5}}).json()["weights"]["student_gaps"] == 5


def test_conflict_report_flow(client, admin, faculty_user):
    r = client.post("/api/conflict-reports", json={"message": "I teach two classes at once on Tuesday"}, headers=faculty_user)
    assert r.status_code == 201
    assert any(x["id"] == r.json()["id"] for x in client.get("/api/conflict-reports", headers=admin).json())
    assert client.post(f"/api/conflict-reports/{r.json()['id']}/resolve", json={"admin_note": "fixed"}, headers=admin).json()["status"] == "resolved"
    assert client.post("/api/conflict-reports", json={"message": "x"}, headers=admin).status_code in (404, 422)
