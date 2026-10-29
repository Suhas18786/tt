#!/bin/sh
set -e
echo "Waiting for database..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text
url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        with create_engine(url).connect() as c:
            c.execute(text("select 1"))
        break
    except Exception as e:
        time.sleep(1)
else:
    raise SystemExit("database not reachable")
PY
alembic upgrade head
if [ "$SEED_ON_START" = "true" ]; then python -m app.seed; fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_WORKERS:-2}"
