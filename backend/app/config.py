"""Application settings, read from environment variables (see .env.example)."""
import logging
import os

log = logging.getLogger("timetable")


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://timetable:timetable@localhost:5432/timetable",
        )
        # Hosts such as Render/Heroku hand out "postgres://..." URLs; SQLAlchemy needs the driver name.
        for old in ("postgres://", "postgresql://"):
            if self.database_url.startswith(old):
                self.database_url = "postgresql+psycopg2://" + self.database_url[len(old):]
        secret = os.getenv("SECRET_KEY", "")
        if not secret:
            if self.environment == "production":
                raise RuntimeError("SECRET_KEY must be set when ENVIRONMENT=production")
            log.warning("SECRET_KEY not set - using an insecure development key")
            secret = "dev-insecure-secret-change-me-0123456789"
        self.secret_key = secret
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o.strip()]
        self.solver_max_seconds = int(os.getenv("SOLVER_MAX_SECONDS", "60"))
        self.solver_workers = int(os.getenv("SOLVER_WORKERS", "8"))


settings = Settings()
