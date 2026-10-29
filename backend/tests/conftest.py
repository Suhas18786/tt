import os

# Must be set before the app is imported: tests run against an in-memory SQLite database.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("SOLVER_WORKERS", "4")
