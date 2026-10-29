FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 netcat-openbsd && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x start.sh && useradd -m app && chown -R app /srv
USER app
EXPOSE 8000
CMD ["./start.sh"]
