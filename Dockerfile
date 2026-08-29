# ── Stage 1: Build / Test stage (mirrors maven build-app stage in original) ──
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime (mirrors eclipse-temurin:21-jre stage) ──
FROM python:3.11-slim AS runtime
WORKDIR /app

# Create non-root user (same as original Dockerfile: appuser 1000)
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
COPY requirements.txt ./

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
# Gunicorn mirrors `java -jar ...` entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]
