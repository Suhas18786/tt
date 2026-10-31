from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..services.btech_sample import load_btech_sample

router = APIRouter(tags=["sample-data"])


@router.post("/admin/load-btech-sample")
def load_btech(db: Session = Depends(get_db), _=Depends(require_admin)):
    return load_btech_sample(db)
