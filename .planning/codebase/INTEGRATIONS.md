# External Integrations

**Analysis Date:** 2026-10-23

## APIs & External Services

**Runtime (inside the container):**
- None. No code in `src/` or `tests/` makes outbound HTTP calls: no `requests`, `httpx`, `urllib`, `aiohttp`, or cloud SDK client. The only URL fetch is the health probe in `bin/run_services.sh` (`urllib.request.urlopen('$PREFECT_API_URL/health')`), which targets the local Prefect server.
- Prefect's client talks to the Prefect server at `PREFECT_API_URL` (`http://127.0.0.1:4201/api` in the container).
- `amplitude-analytics` is a Prefect dependency in `uv.lock`. The repo sets no analytics opt-out variable. Whether it sends data by default is not verified in this mapping.

**Public data source (provenance only, not fetched at runtime):**
- Kaggle `rodolfomendes/abalone-dataset`, originally UCI dataset 1 (`README.md`). The CSV is vendored in `data/abalone.csv` (tracked, 4,177 data rows; Pandera drops 6 invalid rows at training time).

**Build and CI services:**
- GitHub Actions (`.github/workflows/ci.yaml`): `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.2`, `docker/setup-buildx-action@v4`, `docker/build-push-action@v7` with the GitHub Actions cache backend (`type=gha`)
- PyPI: uv resolves from `https://pypi.org/simple`. Files are served from `files.pythonhosted.org` (URLs in `uv.lock`).
- Docker Hub: base image `python:3.11-slim` (`Dockerfile.app`)
- Pre-commit hook repositories on GitHub (`.pre-commit-config.yaml`): `pre-commit/pre-commit-hooks` v4.4.0, `astral-sh/ruff-pre-commit` v0.17.2, `astral-sh/uv-pre-commit` 0.7.17

**Not present:** cloud SDKs (AWS, GCP, Azure), LLM or model-hosting APIs, payment, email, messaging, feature stores. Grep for `boto3`, `kaggle`, `requests`, and `httpx` in code finds nothing.

**Internal links between container processes:**
- Training flow to Prefect server: HTTP to `PREFECT_API_URL` (`src/modelling/deployment.py`)
- API to training flow: no network call. The API reads files that the training flow writes (see File Storage).
- `bin/run_services.sh` waits for `$PREFECT_API_URL/health` before it starts the training deployment.
- Prefect UI calls its own API at `PREFECT_UI_API_URL` (`http://localhost:4200/api`, set in `Dockerfile.app`).

## Data Storage

**Databases:**
- No application database. No database driver or ORM is used in `src/` or `tests/`.
- Prefect server database (Prefect internal): flow runs, deployments and schedules, and the `model-rmse` table artifact written by `src/modelling/main.py`. Prefect's default is a SQLite file under `PREFECT_HOME` (default `~/.prefect`). The repo does not set `PREFECT_API_DATABASE_CONNECTION_URL`. This default comes from Prefect's documented behaviour and is not verified against the installed package in this mapping.
  - Connection: none configured in the repo
  - Client: Prefect server with SQLAlchemy 2.0.55 and aiosqlite 0.22.1 (locked)
  - `flow.serve(..., pause_on_shutdown=False)` keeps the schedule active after the serving process stops (`src/modelling/deployment.py`)
- MLflow (notebooks only): `notebooks/modelling.ipynb` calls `mlflow.set_experiment("abalone")`, `mlflow.start_run`, `mlflow.log_metrics`, and `mlflow.sklearn.log_model`. It sets no tracking URI, so MLflow's default store applies. Local stores `notebooks/mlruns/` and `notebooks/mlflow.db` exist and are gitignored. `.dockerignore` keeps both out of the image.
  - Client: `mlflow` 3.17.2 (dev group)

**File Storage:**
- Local filesystem only. No object storage (S3, GCS, Azure Blob) in code or lock.
- Dataset in: `data/abalone.csv`, read by `load_data` (`pd.read_csv`) in `src/modelling/main.py`. The weekly deployment resolves it as `Path(__file__).parents[2] / "data" / "abalone.csv"` (`src/modelling/deployment.py`). Notebooks read `../data/abalone.csv`.
- Model hand-off from training to API. In the container both sides use the same directory:
  - Training writes `src/web_service/local_objects/model.pkl` (`pickle_object` in `src/modelling/utils.py`), then `src/web_service/local_objects/interval.json` (`save_json`).
  - The API reads them with `load_object` (`pickle.load` in `src/web_service/utils.py`) and `load_json`. `get_model()` in `src/web_service/main.py` reloads when `max(mtime(model.pkl), mtime(interval.json))` changes. There is no lock and no version check.
  - Writes are not atomic (`open(path, "wb")`). Inference, not reproduced: a `/predict` request during a write can hit a partial pickle and return 500 until the next request. A request between the two writes can pair the new model with the old interval.
  - `pickle.load` can execute code embedded in the file. `model.pkl` is tracked in git, so changes to it show up only as binary diffs.
- Committed artifacts: `src/web_service/local_objects/model.pkl` (365,717 bytes) and `src/web_service/local_objects/interval.json` are tracked. The CI smoke test and `tests/test_inference.py` depend on them.
- Container storage: no `VOLUME` and no `-v` in `README.md` or the CI workflow. A retrained model and the Prefect state therefore live only in the container's writable layer.

**Caching:**
- None external. The API keeps the loaded model in the module-level dict `_loaded` (`src/web_service/main.py`), invalidated by file mtime.

## Authentication & Identity

**Auth Provider:**
- None. No auth library, API-key check, token handling, or `Depends`/security scheme in the repo.
  - Implementation: every endpoint is open. This covers `GET /`, `GET /model`, `POST /predict`, and FastAPI's default `/docs`, `/redoc`, and `/openapi.json`.
  - Prefect server: no auth configured. Anyone who can reach port 4201 can start the `weekly-training` deployment from the UI ("Run > Quick run", `README.md`).
  - Exposure: `README.md` publishes ports as `-p 0.0.0.0:8000:8001 -p 0.0.0.0:4200:4201`, which binds both services on every host interface.
- No CORS middleware (`add_middleware` is absent from `src/web_service/main.py`).

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Rollbar, Datadog, or similar SDK in `pyproject.toml` or the code.

**Logs:**
- Training flow: Prefect run logger (`get_run_logger()` in `src/modelling/main.py`) logs the number of dropped rows and the test RMSE. Visible in the Prefect UI.
- API: no `logging` usage in the repo. Output comes from uvicorn's default logging to the container's stdio. `docker logs` shows it. CI dumps it on failure (`.github/workflows/ci.yaml`).
- Metrics: test RMSE per training run is stored as the Prefect table artifact `model-rmse` (`create_table_artifact` in `src/modelling/main.py`). The API has no `/metrics` endpoint.
- Health: API `GET /` returns `{"health_check": "App up and running!"}`. Prefect `GET /api/health` is used by `bin/run_services.sh` and the CI workflow.
- Instrumentation: none in repo code. `prometheus-client` (Prefect dependency) and `opentelemetry-api` (FastAPI dependency) appear in the lock.

## CI/CD & Deployment

**Hosting:**
- None. No deployment target in the repo. The API and Prefect server run locally (`uv run uvicorn ...`, `uv run prefect server start`) or in the `abalone-api` container (`README.md`).
- CI builds the image with `push: false`. Nothing is pushed or deployed.

**CI Pipeline:** GitHub Actions, `.github/workflows/ci.yaml`
- Triggers: `push` to `main`, and every `pull_request`. Workflow permissions: `contents: read`.
- Job `CI` (ubuntu-latest, Python 3.11): checkout, then `astral-sh/setup-uv` (`enable-cache: true`), then `uv sync --locked`, then `uv run pre-commit run --all-files`, then `uv run pytest`.
- Job `docker`: checkout, then Buildx, then `docker/build-push-action` (`file: Dockerfile.app`, tag `abalone-api:ci`, GHA cache), then `docker run -d --init` (8000 to 8001, 4200 to 4201), then `curl -sf` against `GET /`, `POST /predict` (`-f` fails on HTTP 4xx and 5xx, so the 201 response passes), and `GET /api/health` on port 4200. On failure it runs `docker logs abalone`.
- Secrets: none referenced. No deploy, release, or scheduled job. The matrix contains only Python 3.11.
- The `/predict` smoke test depends on the git-tracked model files. Without them the container answers 503.

## Environment Configuration

**Required env vars:**
- None for the API, or for running the training script directly.
- `PREFECT_API_URL`: needed only to attach `src/modelling/deployment.py` and `prefect deployment run` to a Prefect server. Set in `Dockerfile.app` for the container. Set per terminal when running locally (`README.md`).
- `PREFECT_UI_API_URL`: set in `Dockerfile.app`, used by the Prefect UI only.
- No other environment variable is read anywhere in the repo.

**Secrets location:**
- No secrets are used or stored. No `.env` file is present. Neither the code, the CI workflow, nor the Dockerfile needs a credential.
- `.gitignore` already excludes `.env` and `secrets/*`, so a credential file added later stays out of git.

## Webhooks & Callbacks

**Incoming:**
- None. The inbound HTTP surface is the FastAPI app in `src/web_service/main.py`: `GET /` (line 37), `GET /model` (line 43), and `POST /predict` (line 57). Clients call these routes. Nothing posts webhooks to the repo.
- The Prefect server REST API under `/api` (container port 4201) is internal. The local deployment process and the Prefect UI call it.

**Outgoing:**
- None configured in the repo. No webhook, Slack, email, or HTTP callback code. Prefect notifications or automations, if any, would be set in the Prefect UI and are not stored in this repo.

---

*Integration audit: 2026-10-23*
