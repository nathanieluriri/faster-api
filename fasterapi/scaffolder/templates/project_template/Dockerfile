FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    WEB_CONCURRENCY=2

WORKDIR /app

# curl is only used by the docker-compose healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

# Cloud Run, Render and Fly inject PORT; WEB_CONCURRENCY should roughly match the vCPU count.
CMD exec gunicorn main:app -k uvicorn.workers.UvicornWorker \
    --workers "$WEB_CONCURRENCY" --bind "0.0.0.0:$PORT" \
    --timeout 120 --graceful-timeout 30
