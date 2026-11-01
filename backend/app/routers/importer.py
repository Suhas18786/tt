from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..services import csv_parse
from ..services.importer import ImportFailed, import_rooms, import_teaching_plan

router = APIRouter(tags=["import"])


class ImportIn(BaseModel):
    csv: str = Field(min_length=1, max_length=2_000_000)
    dry_run: bool = False


def _run(fn, db: Session, body: ImportIn):
    try:
        return fn(db, body.csv, body.dry_run)
    except ImportFailed as e:
        db.rollback()
        raise HTTPException(422, {"message": "The file has problems, so nothing was imported.",
                                  "violations": [{"code": "csv", "message": m} for m in e.errors[:50]]})


@router.post("/admin/import/teaching-plan")
def teaching_plan(body: ImportIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    return _run(import_teaching_plan, db, body)


@router.post("/admin/import/rooms")
def rooms(body: ImportIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    return _run(import_rooms, db, body)


@router.get("/admin/import/templates")
def templates(_=Depends(require_admin)):
    return {"teaching_plan": csv_parse.PLAN_TEMPLATE, "rooms": csv_parse.ROOMS_TEMPLATE}
