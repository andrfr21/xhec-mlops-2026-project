# Technology Stack

**Analysis Date:** 2026-10-23

## Languages

**Primary:**
- Python 3.11 (exact minor: `requires-python = ">=3.11,<3.12"` in `pyproject.toml`, lock `requires-python = "==3.11.*"`) - all code in `src/` and `tests/`
- Python 3.11.16 - kernel version recorded in `notebooks/eda.ipynb` and `notebooks/modelling.ipynb`

**Secondary:**
- Bash - container entrypoint `bin/run_services.sh`; `run:` steps in `.github/workflows/ci.yaml`
- Dockerfile - `Dockerfile.app` (single stage)
- YAML - `.github/workflows/ci.yaml`, `.pre-commit-config.yaml`
- TOML - `pyproject.toml`, `uv.lock`
- Jupyter notebooks (JSON) - `notebooks/eda.ipynb`, `notebooks/modelling.ipynb`

## Runtime

**Environment:**
- CPython 3.11 only. Python 3.10 and 3.12+ are rejected by `requires-python`. `README.md` gives the reason: on 3.10 uv installs scikit-learn 1.7 for a model saved with 1.9.
- Docker base image: `python:3.11-slim` (`Dockerfile.app`, floating tag, no digest pin)
- CI runner: `ubuntu-latest`, Python matrix `["3.11"]` (`.github/workflows/ci.yaml`)

**Package Manager:**
- uv (Astral). Not pinned in `Dockerfile.app` (`pip install --no-cache-dir uv` takes the latest release). Not pinned in CI (`astral-sh/setup-uv@v10.3.2` with no uv version input). The pre-commit `uv-pre-commit` hook is pinned to `0.7.17`.
- Lockfile: present and tracked, `uv.lock` (`version = 1`, `revision = 3`). 204 `[[package]]` entries: 203 from `https://pypi.org/simple`, 1 virtual entry for the project.
- `[tool.uv] package = false` in `pyproject.toml`: the project itself is not installed. `setuptools` is declared as the build backend but uv never runs it.
- `xhec_mlops_project_student.egg-info/` is a local, gitignored build artifact and is out of date (its `requires.txt` lists only `pydantic`).

## Frameworks

**Core (installed in the Docker image):**
- FastAPI 0.154.0 (`>=0.150.0,<0.155`) - HTTP API in `src/web_service/main.py`. The `<0.155` cap is justified by a `pyproject.toml` comment that cites Prefect 3.9, but the lock pins Prefect 3.8.8 (see Key Dependencies).
- Starlette 1.9.0 (transitive via FastAPI) - ASGI layer under FastAPI
- Uvicorn 0.54.0 (`>=0.54.0`) - ASGI server, started by `bin/run_services.sh` on `0.0.0.0:8001`. No Gunicorn.
- Prefect 3.8.8 (`>=3.8.8`) - orchestration: `@flow`/`@task` in `src/modelling/`, `flow.serve()` in `src/modelling/deployment.py`, Prefect server started by `bin/run_services.sh` on `0.0.0.0:4201`
- scikit-learn 1.9.1 (`>=1.7.2`) - model: `HistGradientBoostingRegressor` wrapped in `TransformedTargetRegressor` (`src/modelling/training.py`), plus `train_test_split` and metrics (`src/modelling/preprocessing.py`, `src/modelling/training.py`)
- pandas 3.1.0 (`>=2.3.3`) - data loading and feature frames (`src/modelling/preprocessing.py`, `src/web_service/lib/inference.py`)
- Pandera 0.34.1 (`>=0.34.1`) - data validation via `pandera.pandas` (`src/modelling/preprocessing.py`)
- Pydantic 2.14.1 (`>=2.14.1`) - API request and response models (`src/web_service/lib/models.py`)
- NumPy 2.4.6 (transitive, imported directly, see Key Dependencies) - `src/modelling/training.py`, `src/web_service/lib/inference.py`

**Testing:**
- pytest 9.1.1 (`>=9.1.1`, dev group) - tests in `tests/`. Config: `[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`.
- FastAPI `TestClient` (`tests/test_api.py`) - re-exports Starlette's `TestClient`, which imports `httpx2` (dev group) and only falls back to `httpx` with a deprecation warning (`starlette/testclient.py`).

**Build/Dev:**
- ruff 0.17.2 (`>=0.17.2`, dev group) - lint (`ruff-check --fix`) and format (`ruff-format`) through pre-commit. No `[tool.ruff]` section, so defaults apply.
- pre-commit 4.7.0 (`>=4.6.2`, dev group) - hooks in `.pre-commit-config.yaml`: `pre-commit/pre-commit-hooks` v4.4.0 (trailing-whitespace, end-of-file-fixer, check-toml, check-yaml, check-json, check-added-large-files), `ruff-pre-commit` v0.17.2, `uv-pre-commit` 0.7.17 (`uv-lock`)
- ipykernel 7.4.0 (`>=7.3.0`, dev group) - notebook kernel
- Docker - builds `abalone-api` from `Dockerfile.app`. CI uses Buildx via `docker/setup-buildx-action@v4`.

**Notebook-only (dev group, excluded from the Docker image by `--no-dev`):**
- MLflow 3.17.2 (`>=3.17.2`) - experiment tracking in `notebooks/modelling.ipynb` (`mlflow.set_experiment("abalone")`)
- matplotlib 3.11.2 (`>=3.10.9`) and seaborn 0.13.2 (`>=0.13.2`) - plots in `notebooks/eda.ipynb`

**Not present:** web frontend framework, ORM, task queue or broker, cache server, GPU/CUDA stack, Node.js.

## Key Dependencies

**Critical:**
- scikit-learn 1.9.1 - the served model is a pickle (`src/web_service/local_objects/model.pkl`, 365,717 bytes, tracked in git). `README.md` says a pickled model must be loaded with the scikit-learn version it was saved with. Upgrading scikit-learn means retraining (`src/modelling/main.py`) and committing the new `model.pkl`.
- Prefect 3.8.8 - runs the training flow and the Prefect server. The lock resolves to the floor (`>=3.8.8`). Two other pins exist because of Prefect: `fastapi<0.155` (commit `8eca5c1`) and `sqlalchemy<2.1` (commit `f42b676`, "breaks the prefect scheduler").
- FastAPI 0.154.0 - capped `<0.155`. The cap comment cites Prefect 3.9, which is not in the lock.
- pandas 3.1.0 - locked on major version 3. The declared floor is `>=2.3.3` and there is no upper bound, so a lock refresh can move it further. Not checked against pandas 3 behaviour in this mapping.
- Pydantic 2.14.1 - validates `/predict` input: `PositiveFloat` measurements and `Literal["M", "F", "I"]` sex (`src/web_service/lib/models.py`). Validation failures return 422 (`tests/test_api.py`).

**Infrastructure:**
- SQLAlchemy 2.0.55 (`<2.1`, declared directly) - used by Prefect (server database) and MLflow. No direct use in repo code.
- aiosqlite 0.22.1 and asyncpg 0.32.0 - Prefect's database drivers (lock: dependencies of `prefect`)
- httpx 0.28.1 (transitive via Prefect, `http2` extra) - used by Prefect's client
- SciPy 1.17.1 and joblib 1.6.0 (transitive via scikit-learn)

**Undeclared direct dependencies (imported in code, absent from `pyproject.toml`):**
- NumPy - `import numpy` in `src/modelling/training.py`, `src/web_service/lib/inference.py`, `tests/test_training.py`. It is present only as a transitive dependency of pandas and scikit-learn.

**Test client dependency:**
- `httpx2` 2.16.0 (`>=2.14.0`, dev group, commit `dea1270`). No repo file imports it directly: Starlette 1.9's `TestClient` imports it (`starlette/testclient.py`, lines 26-42), and using plain `httpx` there raises a `StarletteDeprecationWarning`.

## Configuration

**Environment:**
- No `.env` file in the repo. No `os.environ` or `getenv` call in `src/` or `tests/`.
- `PREFECT_API_URL` - read by Prefect. Used by `src/modelling/deployment.py` and `prefect deployment run` (set per terminal, see `README.md`). Set to `http://127.0.0.1:4201/api` in `Dockerfile.app`. Probed by `bin/run_services.sh`.
- `PREFECT_UI_API_URL=http://localhost:4200/api` - set in `Dockerfile.app` for the Prefect UI.
- `PATH` prepended with `/app/.venv/bin` in `Dockerfile.app`.
- Hard-coded values: uvicorn port 8001 and Prefect port 4201 in the container (mapped to 8000 and 4200 on the host, per `README.md`); weekly cron `0 0 * * 0` in `src/modelling/deployment.py` (no timezone set); `test_size=0.2` and `random_state=42` in `src/modelling/preprocessing.py`; model artifacts under `src/web_service/local_objects/`.
- Not present: `[tool.ruff]`, `[tool.mypy]`, `.python-version`, `.nvmrc`, `Makefile`, `prefect.yaml`.

**Build:**
- `pyproject.toml`: `[build-system]` (setuptools), `[project]` (runtime dependencies), `[dependency-groups] dev`, `[tool.uv] package = false`, `[tool.pytest.ini_options]`
- `uv.lock`: `uv sync` (local), `uv sync --locked` (CI, fails when the lock is stale), `uv sync --frozen --no-dev` (Docker build)
- `Dockerfile.app`: copies `pyproject.toml uv.lock` before `src`, `bin`, `data`, so the dependency layer is cached. `EXPOSE 8001 4201`. `CMD ["bash", "bin/run_services.sh"]`. Built with `docker build -t abalone-api -f Dockerfile.app .` (`README.md`).
- `.dockerignore`: `.venv`, `.git`, `**/mlruns`, `**/mlflow.db`
- `.gitignore`: `.env`, `.venv`, `*.egg-info/`, `mlruns/`, `mlflow.db`, `secrets/*`
- `.gitattributes`: `*.sh text eol=lf`
- `.pre-commit-config.yaml`: installed with `uv run pre-commit install` (`README.md`)
- `.github/workflows/ci.yaml`: GitHub Actions

## Platform Requirements

**Development:**
- Python 3.11 exactly, uv, Git (pre-commit hooks). Docker only for the containerised run (`README.md`).
- `README.md` gives both PowerShell (`$env:PREFECT_API_URL = ...`) and bash (`export ...`) commands.
- `bin/run_services.sh` is bash. It runs only inside the container.

**Production:**
- No hosting target configured. No Procfile, cloud, Kubernetes, Helm, or Terraform config in the repo.
- Only deployable artifact: the Docker image `abalone-api` from `Dockerfile.app`. CI builds it with `push: false`, so it is never published.
- The container runs three processes from `bin/run_services.sh`: the Prefect server (port 4201), the weekly training deployment (started once the Prefect health probe passes), and the uvicorn API (port 8001, started with `exec` so it receives the `docker stop` signal).
- Container hardening: runs as root (no `USER` directive), no `HEALTHCHECK`, no `VOLUME`.

---

*Stack analysis: 2026-10-23*
