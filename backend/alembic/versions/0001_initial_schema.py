"""Initial schema: all tables, constraints, FKs and indexes.

The baseline revision creates the schema from the SQLAlchemy models (tables, foreign keys,
unique/check constraints and indexes are all declared in app/models.py). Every later schema
change must be a normal revision:  alembic revision --autogenerate -m "describe change"

Revision ID: 0001
Revises:
"""
from alembic import op

from app import models  # noqa: F401
from app.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
