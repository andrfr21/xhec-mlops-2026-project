# Better Dockerfile (issue #31) - design

Date: 2026-10-23. Made with the Superpowers brainstorming skill.

## Problem

`Dockerfile.app` installs uv with pip in the final image, runs everything as root and has no healthcheck. Issue #31.

## Constraints

- Keep the single container of the course: API + Prefect server + weekly training deployment, started by `bin/run_services.sh`.
- Keep the ports (8001 API, 4201 Prefect), the Prefect environment variables and the CI docker job (build, `/predict`, Prefect health) green.
- The training deployment writes `model.pkl` and `interval.json` in `src/web_service/local_objects/` at runtime, and the Prefect server writes its database in `PREFECT_HOME`: both must be writable without root.

## Approaches considered

1. **Multi-stage with the official uv pattern (chosen).** A build stage installs the dependencies with uv; the final image only gets the virtualenv, the code and the data.
2. Single stage, uv copied from its image instead of `pip install uv`. Simpler, but uv stays in the image.
3. Two containers with docker compose (API, Prefect). Better Docker practice, but it changes the single-container design of the course, so it is out of scope.

## Design

**Build stage** (`python:3.11-slim AS builder`):
- uv binary copied from `ghcr.io/astral-sh/uv:0.12.21` (same version as the one used to make `uv.lock`, so `--locked` does not see a format change).
- `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`.
- `uv sync --locked --no-dev --no-install-project`, with `uv.lock` and `pyproject.toml` bind-mounted and a cache mount for the uv cache.

**Final stage** (`python:3.11-slim`, same base so the virtualenv's python path is valid):
- `useradd --create-home app`; the Prefect database goes to `/home/app/.prefect` (default `PREFECT_HOME`).
- Copy `/app/.venv` from the build stage, then `src`, `bin` and `data`.
- `chown app` on `src/web_service/local_objects` only, so the rest of the code stays read-only for the running user.
- `USER app`.
- `HEALTHCHECK` on the API only (decision: the API is the service; if Prefect is down the API still predicts with the last model, and the CI checks Prefect separately): `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/')"`, every 30 s, timeout 5 s, start period 30 s, 3 retries. Python is used because the slim image has no curl.
- Same `ENV`, `EXPOSE` and `CMD` as before.

## Verification

- Build, then compare the image size with the current one (808 MB).
- `docker exec ... whoami` returns `app`; no `pip`/`uv` in the final image.
- `docker inspect` health status becomes `healthy`.
- A training run started in the container (`prefect deployment run`) completes and rewrites the model as the `app` user.
- `docker stop` still takes a few seconds.
- CI docker job green.

## Out of scope

Persisting the model and the Prefect database outside the container (volumes), and splitting the services. Both are listed as remaining concerns in `.planning/codebase/CONCERNS.md`.
