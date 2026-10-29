# University Automatic Timetable Generator

A database-backed web application that generates conflict-free university timetables with a real constraint solver
(**Google OR-Tools CP-SAT**), lets administrators review / drag-and-drop edit / publish them, and gives faculty their own
portal.

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Tailwind CSS (Vite) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Scheduler | OR-Tools CP-SAT |
| Auth | JWT bearer tokens, bcrypt password hashes, roles `admin` / `faculty` |
| Export | PDF (ReportLab) and Excel (openpyxl) |

## Quick start (Docker)

```bash
cp .env.example .env            # then edit: SECRET_KEY, POSTGRES_PASSWORD (and DATABASE_URL to match)
docker compose up --build
```

* App: <http://localhost:8080>   ·   API docs (Swagger): <http://localhost:8000/docs>
* With `SEED_ON_START=true` the first start loads sample data (4 departments, 14 faculty, 26 subjects, 6 batches, 12 rooms).
  Sample logins: `admin@university.edu` / `Admin@123`; faculty use `Faculty@123` (emails are shown on the Faculty page).
  **Change these before any real deployment**, and set `SEED_ON_START=false` for a clean install.

## Local development

```bash
# database
docker run -d --name tt-db -e POSTGRES_USER=timetable -e POSTGRES_PASSWORD=timetable -e POSTGRES_DB=timetable -p 5432:5432 postgres:16-alpine

# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://timetable:timetable@localhost:5432/timetable SECRET_KEY=dev-secret ENVIRONMENT=development
alembic upgrade head
python -m app.seed               # sample data (idempotent)
uvicorn app.main:app --reload    # http://localhost:8000/docs

# frontend (new terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

## Tests

```bash
cd backend && pytest -q
```

Tests run against in-memory SQLite and cover: no faculty / batch / room double-booking, weekly-hour coverage,
faculty unavailability, consecutive lab blocks, daily-load limits, room type & capacity, infeasibility reports,
manual-edit validation (accepted and rejected moves), publish guards, save/retrieve, PDF/Excel export, and independent
departments. The solver output is checked by an **independent validator** (`scheduler/validator.py`), the same code used to
validate manual drag-and-drop edits.

## Architecture

```
React SPA ──REST/JSON──▶ FastAPI ──▶ SQLAlchemy ──▶ PostgreSQL
                            └──▶ scheduler (loader → candidates → CP-SAT engine → validator)
```

```
backend/app
  main.py            app, error handlers (validation → 422, integrity → 409, unhandled → logged 500 with ref id)
  models.py          all tables, FKs, unique/check constraints, indexes
  schemas.py         server-side validation (Pydantic)
  security.py deps.py   bcrypt hashing, JWT, role guards
  crud.py            generic paginated/searchable/filterable CRUD router factory
  routers/           auth, master (CRUD + availability + config), timetables, reports, faculty_portal
  scheduler/         context (dataclasses, default weights) · loader (DB → problem) · candidates (eligible slots/rooms,
                     pre-solve diagnostics) · engine (CP-SAT model) · validator (hard-constraint checker)
  services/          generation (run/save/move/publish transactions) · exports (PDF/Excel)
  seed.py seed_data.py   realistic sample data
backend/alembic       migrations      backend/tests   pytest suite
frontend/src          pages/ components/ (CrudPage, TimetableGrid, TimetableWorkspace, AvailabilityGrid) api.ts auth.tsx
```

### Database (normalised)

`users`, `departments`, `academic_years`, `semesters`, `faculty`, `subjects`, `faculty_qualifications`,
`faculty_availability` (unavailable / preferred slots), `batches`, `classrooms`, `room_blocked_slots`,
`teaching_assignments` (batch × subject × faculty), `timetable_configs` (working days, periods, breaks, blocked slots,
weights), `timetable_generations`, `scheduled_sessions`, `publication_history`, `conflict_reports`.
Foreign keys use `RESTRICT`/`CASCADE` as appropriate; deleting an in-use record returns a clear 409 message.

### Scheduling model

* A **session** is one block of `session_duration` periods for a teaching assignment. Weekly hours ÷ session duration gives
  the number of sessions. If `consecutive_required` is off, a subject is split into single-period sessions.
* For each session the engine builds Boolean variables `x[session, day, start, room]` only for **eligible** candidates:
  working day, class periods only (no break/lunch/blocked slot inside the block), faculty available for every covered period,
  room of the right type, with enough capacity and equipment, and free in every covered period, and not already used by
  *another published timetable* (so departments can be generated independently while sharing faculty and rooms).
* **Hard constraints**: at most one session per faculty, batch and room in any period; faculty daily/weekly hour limits;
  blocks contiguous and never spanning a break; every session placed.
* **Soft constraints** (weights 0–10, set on the generator page): spread faculty load, avoid faculty gaps, minimise batch idle
  periods, limit consecutive periods, spread repeated sessions of a subject over different days, honour preferred periods,
  balance room use, avoid stacking difficult subjects on one day.
* **Infeasibility**: before solving, diagnostics detect obvious causes (no room big enough, faculty with too few free
  periods, overloaded faculty…). If no complete schedule exists the engine returns the best *conflict-free partial* timetable
  with status `infeasible`, a list of unscheduled sessions and the reasons. Such a timetable can never be published.
* **Manual edits** (`POST /api/timetables/{id}/move`) re-run the validator on the whole timetable; invalid moves get a 422 listing
  each violated rule. Undo/redo in the UI replays inverse moves through the same endpoint.
* **Transactions**: generation + sessions + history are saved atomically; publishing locks the rows, re-validates, and archives the
  previously published timetable for the same batches, so partially saved or conflicting published timetables cannot occur.

## API overview

Interactive documentation: `/docs` (Swagger UI) and `/redoc`. All routes are under `/api`.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `GET /auth/me`, `POST /auth/change-password` |
| Master data (admin write, authenticated read; `?page&page_size&q&<filters>`) | `/departments`, `/academic-years`, `/semesters`, `/batches`, `/classrooms`, `/subjects`, `/faculty`, `/assignments`, `GET /lookups` |
| Availability | `GET/PUT /faculty/{id}/availability` (admin or the faculty member), `GET/PUT /classrooms/{id}/blocked` |
| Configuration | `GET/PUT /config` |
| Timetables | `POST /timetables/generate`, `GET /timetables`, `GET/DELETE /timetables/{id}`, `POST …/save-draft`, `…/publish`, `…/unpublish`, `…/move` (supports `dry_run`), `GET …/validate`, `GET …/export?format=pdf\|xlsx&view=batch\|faculty\|room\|department&entity_id=`, `GET /timetables/history` |
| Reports | `GET /dashboard`, `GET /reports/{faculty\|batch\|room\|department\|workload\|unscheduled}` |
| Faculty portal | `GET /me/timetable`, `GET /me/workload`, `POST/GET /conflict-reports`, `POST /conflict-reports/{id}/resolve` (admin) |

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key. Required when `ENVIRONMENT=production`. `openssl rand -hex 32` |
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg2://…`) |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |
| `SOLVER_WORKERS` | CP-SAT search threads |
| `WEB_WORKERS` | uvicorn processes — a running solve occupies one worker, so use ≥ 2 |
| `SEED_ON_START` | Load sample data on first start |

## Deployment notes

* Put the stack behind HTTPS (e.g. a reverse proxy / load balancer terminating TLS); the bundled nginx serves the SPA and proxies `/api`.
* Use a managed or backed-up PostgreSQL volume; run `alembic upgrade head` on every release (the backend container does this on start).
* Generation runs synchronously inside the request and is bounded by *Solver time limit* (default 30 s); the nginx proxy timeout is 300 s.
  For very large institutions raise `SOLVER_WORKERS`/the time limit or move generation to a job queue.
* Rotate the seeded passwords immediately, and keep `SEED_ON_START=false` in production.

## One-click hosting on Render (public link)

`render.yaml` defines a single Docker web service (API **and** web app on the same URL) plus a PostgreSQL database.

1. Push this folder to a GitHub repository.
2. On <https://render.com>: **New → Blueprint**, pick the repository, and apply. Render builds the root `Dockerfile`,
   creates the database, generates `SECRET_KEY`, runs migrations and loads the sample data.
3. Open the `*.onrender.com` URL Render shows. Sign in with `admin@university.edu` / `Admin@123`, then change the password
   and set `SEED_ON_START=false` once you have your own data.

Free-tier services sleep when idle and have limited CPU, so large timetables solve slowly; use a paid instance for real use.
