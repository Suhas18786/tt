from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_kwargs: dict = {}
if settings.database_url.startswith("sqlite"):  # used by the automated tests
    from sqlalchemy.pool import StaticPool
    _kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True, **_kwargs)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
