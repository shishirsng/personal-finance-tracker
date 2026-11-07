# Stage 1: Build dependencies in isolated wheels environment
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -e . && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r <(pip install pip-tools && pip-compile pyproject.toml -o -) || \
    pip wheel --no-cache-dir --wheel-dir /build/wheels "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" "sqlalchemy>=2.0.36" "asyncpg>=0.30.0" "alembic>=1.14.0" "pydantic>=2.9.2" "pydantic-settings>=2.6.1" "pwdlib[argon2]>=0.2.1" "pyjwt>=2.9.0" "redis>=5.2.0" "arq>=0.26.1" "structlog>=24.4.0" "prometheus-fastapi-instrumentator>=7.0.0" "python-multipart>=0.0.12"

# Stage 2: Final non-root lightweight image
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN useradd -m -u 10001 -s /bin/bash appuser

# Install wheels from builder
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Copy application files
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
