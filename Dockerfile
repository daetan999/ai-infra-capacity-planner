FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/capacity_planner.db \
    SEED_DEMO_DATA=true

WORKDIR /app

RUN addgroup --system planner && adduser --system --ingroup planner planner

COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY data ./data
COPY templates ./templates
COPY static ./static

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir . && \
    mkdir -p /app/data && \
    chown -R planner:planner /app

USER planner

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
