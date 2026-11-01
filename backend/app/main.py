import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from .config import settings
from .routers import auth, faculty_portal, master, reports, sample_data, timetables, importer as importer_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("timetable")

app = FastAPI(title="University Automatic Timetable Generator", version="1.0.0",
              description="Constraint-based (OR-Tools CP-SAT) timetable generation API. Interactive docs at /docs.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, master.router, timetables.router, reports.router, faculty_portal.router, sample_data.router, importer_router.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        loc = ".".join(str(x) for x in e["loc"] if x not in ("body", "query", "path"))
        msgs.append(f"{loc}: {e['msg']}" if loc else e["msg"])
    return JSONResponse(status_code=422, content={"detail": {"message": "; ".join(msgs), "errors": msgs}})


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, exc: IntegrityError):
    log.warning("integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(status_code=409, content={"detail": "The change conflicts with existing data (duplicate or in use)."})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    rid = uuid.uuid4().hex[:8]
    log.exception("unhandled error [%s] on %s %s", rid, request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Internal server error (ref {rid})"})


# --- single-container deployment: serve the built React app from the same origin -----------------
STATIC_DIR = os.getenv("STATIC_DIR", "/srv/static")
if os.path.isfile(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = os.path.realpath(os.path.join(STATIC_DIR, full_path))
        if full_path and candidate.startswith(os.path.realpath(STATIC_DIR) + os.sep) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
