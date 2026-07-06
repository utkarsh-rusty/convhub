# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ---------------------------------------------------------------------------
# Dependencies — isolated stage so app code changes don't bust the pip cache.
# asyncpg ships prebuilt wheels; no system build deps required.
# ---------------------------------------------------------------------------
FROM base AS builder

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Production — non-root user, no reload, minimal image.
# ---------------------------------------------------------------------------
FROM base AS production

COPY --from=builder /install /usr/local
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .

RUN addgroup --system --gid 1000 app \
    && adduser --system --uid 1000 --gid 1000 --no-create-home app \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------------------
# Development — same image layers as production, but runs Uvicorn with reload.
# Mount source in compose; see docker-compose.yml `dev` profile.
# ---------------------------------------------------------------------------
FROM production AS development

USER root

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
