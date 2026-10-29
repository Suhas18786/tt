# One image serving API + web app (used by Render / any single-container host).
FROM node:22-alpine AS web
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STATIC_DIR=/srv/static
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /app/dist /srv/static
RUN chmod +x start.sh && useradd -m app && chown -R app /srv
USER app
EXPOSE 8000
CMD ["./start.sh"]
