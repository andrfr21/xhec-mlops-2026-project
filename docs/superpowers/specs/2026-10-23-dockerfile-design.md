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
- `UV_LINK_MODE=copy` (`UV_COMPILE_BYTECODE=1` was planned, then removed after measurement: see the last section).
- `uv sync --locked --no-dev --no-install-project`, with `uv.lock` and `pyproject.toml` bind-mounted and a cache mount for the uv cache.

**Final stage** (`python:3.11-slim`, same base so the virtualenv's python path is valid):
- `useradd --create-home app`; the Prefect database goes to `/home/app/.prefect` (default `PREFECT_HOME`).
- Copy `/app/.venv` from the build stage, then `src`, `bin` and `data`.
- `chown app` on `src/web_service/local_objects` only, so the rest of the code stays read-only for the running user.
- `USER app`.
- `HEALTHCHECK` on the API only (decision: the API is the service; if Prefect is down the API still predicts with the last model, and the CI checks Prefect separately): `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/')"`, every 30 s, timeout 5 s, start period 30 s, 3 retries. Python is used because the slim image has no curl.
- Same `ENV`, `EXPOSE` and `CMD` as before.

## Verification

- Build, then compare the image size with the current one (805 MB).
- `docker exec ... whoami` returns `app`; no `pip`/`uv` in the final image.
- `docker inspect` health status becomes `healthy`.
- A training run started in the container (`prefect deployment run`) completes and rewrites the model as the `app` user.
- `docker stop` still takes a few seconds.
- CI docker job green.

## Out of scope

Persisting the model and the Prefect database outside the container (volumes), and splitting the services. Both are listed as remaining concerns in `.planning/codebase/CONCERNS.md`.

## What changed during the implementation

Found with the Superpowers systematic-debugging skill (measure first, one change at a time):

1. **Bytecode.** The first build was 972 MB, more than the old image (805 MB). Cause: `UV_COMPILE_BYTECODE=1` writes 8,897 `.pyc` files (venv 588 MB vs 404 MB). Same image without it: 722 MB, and the API answers after about 19 s instead of 10 s (3 runs each). The smaller image wins here, so `UV_COMPILE_BYTECODE` was removed.
2. **pip.** pip comes with the base image, so it is removed in the final stage. Running Python in that step wrote `.pyc` files of the standard library (+8 MB); `python -B` avoids it (the layer is 94 kB).
3. **Prefect UI.** As the `app` user, the Prefect server could not copy its UI files into the venv (`Errno 13`), and the UI on port 4200 answered 404. The CI did not see it because it only checked `/api/health`. A CI check of the UI was added first (failing), then `PREFECT_SERVER_UI_STATIC_DIRECTORY=/home/app/.prefect/ui` fixed it.

Results: 722 MB image (805 MB before), user `app`, no pip or uv, `healthy` status, UI 200, a training run in the container completes and the API reloads the new model, `docker stop` in 2 s.
