# Codebase Structure

**Analysis Date:** 2026-10-23

## Directory Layout

```
xhec-mlops-2026-project/
├── .github/
│   └── workflows/
│       └── ci.yaml                 # CI: pre-commit, pytest, docker build and smoke test
├── bin/
│   └── run_services.sh             # container entrypoint: Prefect server, deployment runner, API
├── data/
│   └── abalone.csv                 # training dataset (4,177 rows), copied into the image
├── notebooks/
│   ├── eda.ipynb                   # exploratory analysis (imports nothing from src/)
│   ├── modelling.ipynb             # model comparison with MLflow tracking
│   ├── mlflow.db                   # local MLflow store (generated, gitignored)
│   └── mlruns/                     # local MLflow runs (generated, gitignored)
├── src/
│   ├── modelling/                  # offline training: Prefect flow, tasks, deployment
│   │   ├── deployment.py           # serves train-model as weekly-training
│   │   ├── main.py                 # train-model flow and CLI entry point
│   │   ├── preprocessing.py        # Pandera schema; load, validate, encode, split tasks
│   │   ├── training.py             # model, RMSE and conformal interval tasks
│   │   └── utils.py                # pickle_object and save_json tasks
│   └── web_service/                # online inference: FastAPI app and served artifacts
│       ├── lib/
│       │   ├── inference.py        # build_features, run_inference, prediction_interval
│       │   └── models.py           # InputData and PredictionOut (Pydantic)
│       ├── local_objects/          # artifacts written by training, read by the API
│       │   ├── .gitkeep
│       │   ├── interval.json       # tracked
│       │   └── model.pkl           # tracked (about 366 KB)
│       ├── main.py                 # FastAPI app, routes, artifact cache
│       └── utils.py                # load_object and load_json
├── tests/
│   ├── test_api.py                 # routes, input validation, hot reload
│   ├── test_inference.py           # feature order, prediction interval
│   ├── test_preprocessing.py       # schema, encoding, split
│   └── test_training.py            # RMSE, model, conformal interval
├── .dockerignore                   # excludes .venv, .git, mlruns, mlflow.db from the image
├── .gitattributes                  # *.sh forced to LF line endings
├── .gitignore
├── .pre-commit-config.yaml         # hygiene hooks, ruff, uv-lock
├── Dockerfile.app                  # image: python:3.11-slim, uv, copies src, bin and data
├── pyproject.toml                  # metadata, runtime and dev dependencies, pytest config
├── README.md
└── uv.lock                         # locked dependency versions
```

Generated and not committed: `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `xhec_mlops_project_student.egg-info/`. The `.planning/` directory holds GSD planning and codebase documents, not code, and git does not track it.

## Directory Purposes

**`src/modelling/`:**
- Purpose: Training pipeline as a Prefect flow and tasks.
- Contains: 5 Python modules, no `__init__.py`.
- Key files: `src/modelling/main.py` (flow `train-model`, CLI), `src/modelling/deployment.py` (weekly deployment), `src/modelling/preprocessing.py` (Pandera schema, data tasks), `src/modelling/training.py` (model, RMSE, interval), `src/modelling/utils.py` (persistence tasks).

**`src/web_service/`:**
- Purpose: HTTP API that serves the model.
- Contains: `main.py`, `utils.py`, `lib/`, `local_objects/`.
- Key files: `src/web_service/main.py` (`app`, routes, artifact cache), `src/web_service/lib/inference.py` (features, prediction, interval), `src/web_service/lib/models.py` (request and response schemas).

**`src/web_service/lib/`:**
- Purpose: Logic and schemas used by the routes. Route definitions stay in `src/web_service/main.py`.
- Contains: `inference.py`, `models.py`.

**`src/web_service/local_objects/`:**
- Purpose: Model artifacts shared by training and the API.
- Contains: `model.pkl`, `interval.json`, `.gitkeep`.
- Key files: `src/web_service/local_objects/model.pkl` (written by `src/modelling/main.py` line 53, read by `src/web_service/main.py` line 11), `src/web_service/local_objects/interval.json` (written by `src/modelling/main.py` line 54, read by `src/web_service/main.py` line 12).

**`tests/`:**
- Purpose: pytest suite for `src/`.
- Contains: 4 modules and 19 test functions (`test_api.py` 8, `test_inference.py` 2, `test_preprocessing.py` 6, `test_training.py` 3). No `conftest.py`.
- Mapping: `test_api.py` covers `src/web_service/main.py`, `lib/models.py` and `utils.py` through the routes. `test_inference.py` covers `src/web_service/lib/inference.py`. `test_preprocessing.py` covers `src/modelling/preprocessing.py`. `test_training.py` covers `src/modelling/training.py`.
- Not imported by any test: `src/modelling/main.py`, `src/modelling/deployment.py`, `src/modelling/utils.py`.

**`data/`:**
- Purpose: Training input.
- Contains: `abalone.csv` (a header line and 4,177 rows, 9 columns).
- Used at runtime by: the weekly deployment (`DATA_PATH` in `src/modelling/deployment.py`, line 5). The image copies it (`COPY data ./data` in `Dockerfile.app`).

**`notebooks/`:**
- Purpose: Exploration and model selection. Not part of the runtime.
- Contains: `eda.ipynb` (sections: Imports, Data, EDA, Conclusions) and `modelling.ipynb` (sections: Modelling, Model selection with repeated cross-validation).
- Notes: They read `../data/abalone.csv`, so they must run from `notebooks/`. They import nothing from `src/`. The docstrings of `src/modelling/training.py` (lines 14-15) and `src/modelling/preprocessing.py` (lines 45 and 60) say that the model and the preprocessing follow these notebooks. That port is manual.

**`bin/`:**
- Purpose: Container entrypoint scripts.
- Contains: `run_services.sh`.

**`.github/workflows/`:**
- Purpose: CI definition.
- Contains: `ci.yaml` (jobs `CI` and `docker`).

**Repository root:**
- Purpose: Project configuration, container build, documentation.
- Contains: `Dockerfile.app`, `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.dockerignore`, `.gitignore`, `.gitattributes`, `README.md`.

## Key File Locations

**Entry Points:**
- `src/modelling/main.py`: training flow `train-model` and its CLI (`python src/modelling/main.py <csv>`).
- `src/modelling/deployment.py`: serves `weekly-training` (`python src/modelling/deployment.py`).
- `src/web_service/main.py`: FastAPI `app` (`uvicorn src.web_service.main:app`).
- `bin/run_services.sh`: starts the three container processes.

**Configuration:**
- `pyproject.toml`: `requires-python = ">=3.11,<3.12"`, runtime dependencies (`[project].dependencies`), dev group (`[dependency-groups].dev`), `[tool.uv] package = false`, `[tool.pytest.ini_options] pythonpath = ["."]`. There is no `[tool.ruff]` section, so ruff runs with its defaults.
- `uv.lock`: locked versions. Relevant here: `scikit-learn` 1.9.1 (the pickle depends on it) and `prefect` 3.8.8.
- `Dockerfile.app`: image build (`python:3.11-slim`, `uv sync --frozen --no-dev`).
- `.pre-commit-config.yaml`: trailing whitespace, end of file, TOML, YAML and JSON checks, large files, `ruff-check --fix`, `ruff-format`, `uv-lock`.
- `.github/workflows/ci.yaml`: CI on pull requests and pushes to `main`.
- `.dockerignore`: excludes `.venv`, `.git`, `**/mlruns`, `**/mlflow.db`.
- `.gitignore`: ignores `.venv`, `*.egg-info/`, `mlruns/`, `mlflow.db`, `.env`, `secrets/*`.
- `.gitattributes`: `*.sh text eol=lf`.

**Core Logic:**
- `src/modelling/preprocessing.py`: validation schema and feature construction. The API reuses `encode_sex`.
- `src/modelling/training.py`: model definition, RMSE, conformal interval.
- `src/web_service/lib/inference.py`: API feature construction, prediction, interval.
- `src/web_service/main.py`: routes and the artifact cache.

**Testing:**
- `tests/`: 4 modules. Runner and import path: `[tool.pytest.ini_options]` in `pyproject.toml`.

**Data and Artifacts:**
- `data/abalone.csv`: training input.
- `src/web_service/local_objects/model.pkl` and `interval.json`: the served artifacts.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`, one concern per module (`preprocessing.py`, `training.py`, `inference.py`, `models.py`, `utils.py`).
- Test modules: `test_<module>.py`, named after the module under test.
- Shell script: `bin/run_services.sh` (LF line endings, forced by `.gitattributes`).
- Dockerfile: `Dockerfile.app`, built with `docker build -f Dockerfile.app .`.
- Artifacts: fixed names `model.pkl` and `interval.json` in `local_objects/`.
- Duplicate basenames: `main.py` and `utils.py` exist in both packages. They are told apart by import style (see Imports).

**Directories:**
- Packages under `src/`: `snake_case`, one per concern (`modelling`, `web_service`).
- `lib/` inside `web_service` holds logic and schemas. `local_objects/` holds artifacts.
- No `__init__.py` anywhere, so the packages are namespace packages.

**Identifiers:**
- Functions: `snake_case` verbs (`load_data`, `validate_data`, `encode_sex`, `extract_x_y`, `split_train_test`, `train_model`, `evaluate_model`, `compute_interval`, `pickle_object`, `save_json`, `build_features`, `run_inference`, `prediction_interval`, `load_object`, `load_json`, `get_model`).
- Route handlers are named by role, not by path: `home` for `/`, `model_info` for `/model`, `predict` for `/predict`.
- Constants: `UPPER_SNAKE_CASE` (`SEX_CATEGORIES`, `ABALONE_SCHEMA`, `LOCAL_OBJECTS`, `MODEL_PATH`, `INTERVAL_PATH`, `DATA_PATH`).
- Classes: `PascalCase`. API schemas end in `Data` for input and `Out` for output (`InputData`, `PredictionOut`).
- Prefect names: flow `train-model`, deployment `weekly-training`, artifact key `model-rmse` (all kebab-case).
- Routes: lowercase single words (`/`, `/model`, `/predict`).
- JSON keys: `snake_case` (`log_half_width`, `coverage`, `rings_low`, `rings_high`, `trained_at`, `interval_coverage`).

**Column and Field Names (two conventions, bridged by hand):**
- Training data and the CSV: Title Case with spaces (`Whole weight`, `Shell weight`, `Rings`).
- One-hot columns: `Sex_F`, `Sex_I`, `Sex_M`.
- API fields: `snake_case` (`whole_weight`, `shell_weight`).
- The mapping between the two is the explicit dict in `build_features` (`src/web_service/lib/inference.py` lines 13-22). Renaming a column on either side means changing that mapping, and retraining.

**Imports:**
- Inside `src/modelling/`, `main.py` and `deployment.py` use bare sibling imports (`from preprocessing import ...`). They run only as scripts, by path. `python -m src.modelling.main` raises `ModuleNotFoundError`.
- Everywhere else, imports are `src.`-rooted (`from src.web_service.lib.models import InputData`, `from src.modelling.preprocessing import encode_sex`). Run commands from the repository root.

## Where to Add New Code

**New Feature:**
- Training-side data step: a `@task` function in `src/modelling/preprocessing.py`, called from the flow in `src/modelling/main.py`. Test it in `tests/test_preprocessing.py` through `.fn`.
- Model or hyperparameter change: `src/modelling/training.py` (`train_model`). Then retrain and commit the regenerated `model.pkl` and `interval.json`. `tests/test_api.py::test_model_info` asserts the class name `HistGradientBoostingRegressor` and must be updated for a different model.
- New input feature column: update `ABALONE_SCHEMA`, `encode_sex` and `extract_x_y` in `src/modelling/preprocessing.py`, `InputData` in `src/web_service/lib/models.py`, and the mapping in `build_features` (`src/web_service/lib/inference.py`). Retrain, commit the artifacts, and keep `tests/test_inference.py::test_features_match_the_model` passing.
- New endpoint: route in `src/web_service/main.py`, request and response models in `src/web_service/lib/models.py`, logic in `src/web_service/lib/inference.py` or a new module in `src/web_service/lib/`, tests in `tests/test_api.py` (which uses `TestClient(app)`).
- Test file: `tests/test_<module>.py`, importing with the `src.` prefix. The `model_copy` fixture in `tests/test_api.py` copies the artifacts so a test can change them without touching the committed files.

**New Component/Module:**
- Training-side module: `src/modelling/<name>.py`. Import it bare from `main.py`, like the existing modules, so the flow keeps running as a script.
- Serving-side module: `src/web_service/lib/<name>.py`, imported as `src.web_service.lib.<name>`.
- New schedule: add it next to the existing `main.serve(...)` call in `src/modelling/deployment.py`.

**Utilities:**
- Training-only helpers: `src/modelling/utils.py`.
- API-only helpers: `src/web_service/utils.py`.
- Code needed by both packages: follow the existing direction. `src/web_service/` imports `src.modelling.preprocessing`. Do not import from `src/web_service/` in `src/modelling/`, because the training side never imports the API.

**New Dependency:**
- Needed at runtime (API or flow): `[project].dependencies` in `pyproject.toml`.
- Needed only for tests, notebooks or linting: `[dependency-groups].dev`.
- Then run `uv lock`. CI runs `uv sync --locked`, and `.pre-commit-config.yaml` runs `uv-lock`. `Dockerfile.app` installs runtime dependencies only (`--no-dev`).

**New Data:**
- Put it under `data/`. The image copies the whole directory (`COPY data ./data`).

## Special Directories

**`src/web_service/local_objects/`:**
- Purpose: Model artifacts shared by training and the API.
- Generated: Yes, by `src/modelling/main.py`.
- Committed: Yes. `model.pkl` and `interval.json` are tracked, and `model.pkl` appears in 4 commits. `.gitkeep` keeps the directory.

**`data/`:**
- Purpose: Training input.
- Generated: No.
- Committed: Yes. Copied into the image.

**`notebooks/mlruns/` and `notebooks/mlflow.db`:**
- Purpose: Local MLflow store for the notebook runs. `mlflow ui` reads it from `notebooks/` (README).
- Generated: Yes.
- Committed: No (`.gitignore`). Excluded from the image (`.dockerignore`). Contents were not inspected.

**`.venv/`:**
- Purpose: uv virtual environment (Python 3.11.16 in this checkout).
- Generated: Yes (`uv sync`).
- Committed: No.

**`.pytest_cache/`, `.ruff_cache/`:**
- Purpose: Tool caches.
- Generated: Yes.
- Committed: No. Each directory contains its own `.gitignore`.

**`xhec_mlops_project_student.egg-info/`:**
- Purpose: setuptools package metadata.
- Generated: Yes.
- Committed: No (`*.egg-info/` in `.gitignore`). No code imports it.

**`.planning/`:**
- Purpose: GSD planning and codebase analysis documents, including this file. Not code.
- Generated: Yes, by GSD commands.
- Committed: No. Git does not track it.

---

*Structure analysis: 2026-10-23*
