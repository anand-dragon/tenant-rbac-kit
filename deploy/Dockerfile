FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

RUN groupadd --system app && useradd --system --gid app --no-create-home app

ENV UV_CACHE_DIR=/app/.uv-cache

WORKDIR /app

COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ src/
COPY casbin/ casbin/
COPY alembic/ alembic/
RUN uv sync --no-dev && chown -R app:app /app

USER app

EXPOSE 8000
# Worker count comes from WEB_CONCURRENCY (uvicorn reads it natively).
CMD ["uv", "run", "uvicorn", "tenant_rbac_kit.main:app", "--host", "0.0.0.0", "--port", "8000"]
