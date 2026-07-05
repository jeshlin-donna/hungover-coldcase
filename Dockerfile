FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.production.txt ./
RUN pip install --upgrade pip && pip install -r requirements.production.txt

COPY backend ./backend
COPY scripts ./scripts
COPY frontend/mock ./frontend/mock
COPY benchmark ./benchmark
COPY data/hero_case ./data/hero_case
COPY data/sample_evidence ./data/sample_evidence

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD curl --fail http://localhost:${PORT:-8000}/ready || exit 1

# Cloud Run injects $PORT at runtime (defaults to 8080); Render/other hosts
# that set a fixed PORT still work since we fall back to 8000 otherwise.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips=*"]
