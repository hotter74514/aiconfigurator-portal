FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534 AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN python -m pip install --no-cache-dir uv==0.11.21
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra aiconfigurator

FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORTAL_RUN_ROOT=/var/lib/portal/runs
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
RUN useradd --create-home --uid 10001 portal \
    && mkdir -p /var/lib/portal/runs \
    && chown -R portal:portal /var/lib/portal
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live')"
CMD ["uvicorn", "portal.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
