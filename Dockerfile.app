# Design: docs/superpowers/specs/2026-10-23-dockerfile-design.md

# --- build stage: install the dependencies with uv ---
FROM python:3.11-slim AS builder

# same uv version as the one used to make uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv
# no UV_COMPILE_BYTECODE: measured +250 MB for a startup ~10 s faster, not worth it here
ENV UV_LINK_MODE=copy

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# --- final image: only the virtualenv, the code and the data, no pip/uv, not root ---
FROM python:3.11-slim

RUN useradd --create-home app
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY bin ./bin
# needed by the weekly training deployment
COPY data ./data
# the training deployment writes the new model here
RUN chown -R app:app src/web_service/local_objects
USER app

ENV PATH="/app/.venv/bin:$PATH"
# the processes in the container use the prefect server of the container,
# the UI (port 4201 mapped on 4200 of the host) calls the API through the host port
ENV PREFECT_API_URL=http://127.0.0.1:4201/api
ENV PREFECT_UI_API_URL=http://localhost:4200/api

# 8001: API, 4201: prefect UI
EXPOSE 8001 4201

# only the API: if prefect is down, the API still predicts with the last model
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/')"

CMD ["bash", "bin/run_services.sh"]
