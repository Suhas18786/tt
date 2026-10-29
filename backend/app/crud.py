"""Generic paginated CRUD router factory."""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Integer, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user, require_admin


def make_crud_router(*, prefix: str, tag: str, Model, In, Out, search: "list[str] | None" = None,
                     filters: list[str] | None = None, exclude: set[str] | None = None,
                     validate: Callable | None = None, after_save: Callable | None = None,
                     before_delete: Callable | None = None, serialize_many: Callable | None = None,
                     readable_by_all: bool = True, in_use_message: str = "This record is in use and cannot be deleted."):
    router = APIRouter(prefix=prefix, tags=[tag])
    exclude = exclude or set()
    search = search or []
    filters = filters or []
    read_dep = get_current_user if readable_by_all else require_admin

    def ser(db, objs):
        if serialize_many:
            return serialize_many(db, objs)
        return [Out.model_validate(o).model_dump(mode="json") for o in objs]

    @router.get("")
    def list_items(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=500),
                   q: str | None = None, db: Session = Depends(get_db), _=Depends(read_dep)):
        query = db.query(Model)
        for f in filters:
            val = request.query_params.get(f)
            if val not in (None, ""):
                col = getattr(Model, f)
                try:
                    query = query.filter(col == (int(val) if isinstance(col.type, Integer) else val))
                except ValueError:
                    raise HTTPException(422, f"Invalid value for filter '{f}'")
        if q:
            query = query.filter(or_(*[getattr(Model, c).ilike(f"%{q}%") for c in search]))
        total = query.count()
        objs = query.order_by(Model.id).offset((page - 1) * page_size).limit(page_size).all()
        return {"items": ser(db, objs), "total": total, "page": page, "page_size": page_size}

    @router.get("/{item_id}")
    def get_item(item_id: int, db: Session = Depends(get_db), _=Depends(read_dep)):
        obj = db.get(Model, item_id)
        if obj is None:
            raise HTTPException(404, "Not found")
        return ser(db, [obj])[0]

    def save(db: Session, obj, data, creating: bool):
        if validate:
            validate(db, data, obj)
        for k, v in data.model_dump(exclude=exclude).items():
            setattr(obj, k, v)
        try:
            db.add(obj)
            db.flush()
            if after_save:
                after_save(db, obj, data, creating)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(409, "A record with the same unique value already exists or a referenced record is missing.") from e
        except HTTPException:
            db.rollback()
            raise
        db.refresh(obj)
        return ser(db, [obj])[0]

    @router.post("", status_code=201)
    def create_item(data: In, db: Session = Depends(get_db), _=Depends(require_admin)):  # type: ignore[valid-type]
        return save(db, Model(), data, True)

    @router.put("/{item_id}")
    def update_item(item_id: int, data: In, db: Session = Depends(get_db), _=Depends(require_admin)):  # type: ignore[valid-type]
        obj = db.get(Model, item_id)
        if obj is None:
            raise HTTPException(404, "Not found")
        return save(db, obj, data, False)

    @router.delete("/{item_id}", status_code=204)
    def delete_item(item_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
        obj = db.get(Model, item_id)
        if obj is None:
            raise HTTPException(404, "Not found")
        try:
            if before_delete:
                before_delete(db, obj)
            db.delete(obj)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(409, in_use_message) from e

    return router
