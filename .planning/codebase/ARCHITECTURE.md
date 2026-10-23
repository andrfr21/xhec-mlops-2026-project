# Architecture

**Analysis Date:** 2026-10-23

## Pattern Overview

**Overall:** Batch training pipeline (Prefect) and online inference service (FastAPI) in one repository, coupled only through a model artifact directory. Each training run overwrites the files the API serves, and the API reloads them when their modification time changes.

**Key Characteristics:**
- Two packages under `src/`: `src/modelling/` (training, run as a Prefect flow) and `src/web_service/` (HTTP API). `pyproject.toml` sets `[tool.uv] package = false`, so uv does not install the project. The image copies `src/` and runs from `/app`, and tests run from the repository root. No `__init__.py` exists under `src/` or `tests/`, so the packages are namespace packages.
- One static input file, `data/abalone.csv` (4,177 rows, 9 columns). The code has no data ingestion, database, message queue, feature store or model registry.
- The only import from training into serving is `encode_sex` (`src/web_service/lib/inference.py` line 5). Training never imports `src/web_service/`. It writes into that package's `local_objects/` directory through a hard-coded path (`src/modelling/main.py` lines 18-20).
- The feature contract is shared by convention, not by a declared schema. Training builds the columns in `encode_sex` (`src/modelling/preprocessing.py`). The API builds the same columns from a hand-written dict in `build_features` (`src/web_service/lib/inference.py` lines 13-22). scikit-learn stores `feature_names_in_` at fit time, and `tests/test_inference.py::test_features_match_the_model` asserts the column order.
- Retraining is reproducible on unchanged inputs (see Data Flow). The weekly schedule changes the served artifacts only when `data/abalone.csv`, the training code or the locked dependencies change.
- One container runs three processes: Prefect server, deployment runner and API (`bin/run_services.sh`).
- The API keeps one model in memory per process. It has no authentication, no CORS middleware and no logging configuration.

## Layers

**Data:**
- Purpose: Static training dataset.
- Location: `data/abalone.csv`
- Contains: One CSV with columns `Sex, Length, Diameter, Height, Whole weight, Shucked weight, Viscera weight, Shell weight, Rings`.
- Depends on: Nothing.
- Used by: `src/modelling/deployment.py` (`DATA_PATH`, line 5), the notebooks (`../data/abalone.csv`), `Dockerfile.app` (`COPY data ./data`).

**Validation and Feature Engineering (training):**
- Purpose: Validate raw rows, one-hot encode `Sex`, split features from target, split train and test.
- Location: `src/modelling/preprocessing.py`
- Contains: `ABALONE_SCHEMA` (Pandera schema, lines 9-28) and Prefect tasks `load_data`, `validate_data`, `encode_sex`, `extract_x_y`, `split_train_test`.
- Depends on: pandas, pandera, prefect, scikit-learn (`train_test_split`).
- Used by: `src/modelling/main.py`, `src/web_service/lib/inference.py` (`encode_sex.fn`), `tests/test_preprocessing.py`.

**Modelling:**
- Purpose: Fit the model, measure test RMSE, compute the conformal interval half-width.
- Location: `src/modelling/training.py`
- Contains: Prefect tasks `train_model`, `evaluate_model`, `compute_interval`.
- Depends on: numpy, pandas, scikit-learn (`TransformedTargetRegressor`, `HistGradientBoostingRegressor`, `mean_squared_error`), prefect.
- Used by: `src/modelling/main.py`, `tests/test_training.py`.

**Orchestration (training):**
- Purpose: Run the pipeline as a Prefect flow and schedule it.
- Location: `src/modelling/main.py` (flow `train-model`, Python function `main`), `src/modelling/deployment.py` (deployment `weekly-training`).
- Contains: One flow, one deployment.
- Depends on: `preprocessing`, `training`, `utils` through bare imports (`from preprocessing import ...`). These resolve only when the file is run by path. See Cross-Cutting Concerns.
- Used by: The CLI (`python src/modelling/main.py <csv>`), the runner started by `deployment.py`, `bin/run_services.sh`.

**Persistence Helpers:**
- Purpose: Write the model and interval files; read them back in the API.
- Location: `src/modelling/utils.py` (`pickle_object`, `save_json`, both Prefect tasks), `src/web_service/utils.py` (`load_object`, `load_json`, plain functions).
- Used by: `src/modelling/main.py` (writes), `src/web_service/main.py` (reads).

**Artifact Store (contract between the two packages):**
- Purpose: Hold the single served model and its interval.
- Location: `src/web_service/local_objects/` with `model.pkl` (about 366 KB) and `interval.json` (`{"coverage": 0.9, "log_half_width": 0.2812...}`). Both are tracked in git.
- Written by: `src/modelling/main.py` (lines 53-54).
- Read by: `src/web_service/main.py` (constants lines 11-12, `get_model` lines 21-34).

**Inference:**
- Purpose: Turn one API payload into features, predict, and build the interval.
- Location: `src/web_service/lib/inference.py` (`build_features`, `run_inference`, `prediction_interval`).
- Depends on: `src.modelling.preprocessing.encode_sex`, `src.web_service.lib.models.InputData`, numpy, pandas.
- Used by: `src/web_service/main.py`, `tests/test_inference.py`.

**API Schemas:**
- Purpose: Request and response contract of the API.
- Location: `src/web_service/lib/models.py` (`InputData`, `PredictionOut`).
- Used by: `src/web_service/main.py` (request body of `/predict`, `response_model`), `src/web_service/lib/inference.py`.

**HTTP API:**
- Purpose: Health check, model information, predictions.
- Location: `src/web_service/main.py` (`app`, `get_model`, three routes).
- Depends on: `lib/inference`, `lib/models`, `utils`.
- Used by: HTTP clients (port 8000 locally, port 8001 inside the container), `tests/test_api.py` (FastAPI `TestClient`), the CI smoke test.

**Runtime and Delivery:**
- Purpose: Build and run the service, verify changes.
- Location: `Dockerfile.app`, `bin/run_services.sh`, `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.github/workflows/ci.yaml`, `tests/`.
- Depends on: uv, Docker, Prefect server, GitHub Actions.

## Data Flow

**Training run (Prefect flow `train-model`, `src/modelling/main.py:main`):**

1. `load_data(trainset_path)` reads the CSV with `pd.read_csv` (4,177 rows on the committed file).
2. `validate_data` runs `ABALONE_SCHEMA.validate(df, lazy=True)` with `drop_invalid_rows=True`. Rows that fail an element check (a measurement at or below 0, `Sex` outside F/I/M, `Rings` below 1) or the cross-column check (a part heavier than the whole) are dropped. A missing column raises `SchemaErrors` and fails the run (`tests/test_preprocessing.py`). Six rows are dropped on the committed file.
3. `encode_sex` adds `Sex_F`, `Sex_I`, `Sex_M` (0/1 integers) and drops `Sex`.
4. `extract_x_y` returns 10 features in this order: `Length, Diameter, Height, Whole weight, Shucked weight, Viscera weight, Shell weight, Sex_F, Sex_I, Sex_M`, and the target `Rings`.
5. `split_train_test` splits 80/20 with `random_state=42`: 3,336 training rows and 835 test rows on the committed file.
6. `train_model` fits, on the training split only, `TransformedTargetRegressor(regressor=HistGradientBoostingRegressor(learning_rate=0.05, max_iter=200, max_leaf_nodes=15, random_state=42), func=np.log1p, inverse_func=np.expm1)`. The model learns `log1p(Rings)` and returns predictions on the rings scale.
7. `evaluate_model` computes the RMSE on the test split. `main` logs it and writes the Prefect table artifact `model-rmse`. The key is fixed, so each run adds an entry under the same key and the Prefect UI keeps the history.
8. `compute_interval` computes the split-conformal half-width on the `log1p` scale, using the test split as the calibration set. The level is `min(1, ceil((n+1)*0.9)/n)` and the quantile uses `method="higher"` (`src/modelling/training.py` lines 44-47).
9. `pickle_object` writes `src/web_service/local_objects/model.pkl`, then `save_json` writes `interval.json` (`src/modelling/main.py` lines 53-54).

Points that follow from the code:
- The served model is trained on 80% of the data and is not refitted on the full dataset.
- Both files are written in place, without a temporary file or rename.
- Nothing compares the new model with the previous one. Every successful run overwrites both files.
- Reproducibility (checked by retraining in memory on the committed CSV, with the locked scikit-learn version): the predictions matched the committed `model.pkl` exactly (maximum difference 0.0), and the half-width matched `interval.json`.

**Prediction request (`POST /predict`, `src/web_service/main.py:predict`):**

1. FastAPI parses the body into `InputData`: `sex` must be `M`, `F` or `I`, and the seven measurements must be positive floats. Invalid input returns 422 before the route runs.
2. `get_model()` stats both artifact files. If either is missing it raises 503. If the newest modification time differs from the cached `trained_at`, it loads `model.pkl` and `interval.json` again.
3. `run_inference` calls `build_features`, which builds a one-row DataFrame with the CSV column names and passes it through `encode_sex.fn`. Then `model.predict` returns `rings`.
4. `prediction_interval(rings, log_half_width)` returns `expm1(log1p(rings) - h)` and `expm1(log1p(rings) + h)`.
5. The response is `PredictionOut`: `rings`, `age = rings + 1.5`, `rings_low`, `rings_high`, with HTTP status 201.

**Retraining handoff:**

1. Trigger: the cron deployment `weekly-training` (`0 0 * * 0`, no timezone argument) registered by `src/modelling/deployment.py`, or a manual run from the Prefect UI or `prefect deployment run "train-model/weekly-training"` (README).
2. The run calls `main` with `trainset_path` set to `<repo>/data/abalone.csv`.
3. Both artifacts are overwritten (step 9 above). `model.pkl` is written before `interval.json`, so a request that lands between the two writes can use the new model with the old interval until the next request sees the newer modification time.
4. The API picks up the new files on its next request, with no restart. `GET /model` reports `trained_at`, the newest artifact modification time in UTC.

**State Management:**
- Training: Stateless between runs. Run history, schedules and the `model-rmse` artifact live in the Prefect server, which uses its default local database (no database is configured in the repository).
- API: One module-level dict `_loaded` in `src/web_service/main.py` (line 18) with keys `model`, `interval`, `trained_at`. It is keyed on the newest artifact modification time and is written only after both files load successfully.

```python
# src/web_service/main.py, get_model (condensed, lines 24-33)
trained_at = max(MODEL_PATH.stat().st_mtime, INTERVAL_PATH.stat().st_mtime)
if _loaded.get("trained_at") != trained_at:
    _loaded["model"] = load_object(MODEL_PATH)
    _loaded["interval"] = load_json(INTERVAL_PATH)
    _loaded["trained_at"] = trained_at
```

- The route handlers are plain `def` functions, so FastAPI runs them in its threadpool. `get_model` has no lock, so concurrent first requests can both load the files. Both load the same files, so the only cost is duplicate loading, unless a retrain is writing at that moment.

## Key Abstractions

**Prefect task and flow (`@task`, `@flow`):**
- Purpose: Unit of orchestration. Each training step is a task, and `train-model` is the flow.
- Examples: `src/modelling/preprocessing.py`, `src/modelling/training.py`, `src/modelling/utils.py`, `src/modelling/main.py`.
- Pattern: The API and the tests call the undecorated function through `.fn`, which runs the logic without creating Prefect task runs. Examples: `encode_sex.fn(df)` in `src/web_service/lib/inference.py` (line 26), `validate_data.fn(df)` in `tests/test_preprocessing.py`.

**Pandera schema (`ABALONE_SCHEMA`):**
- Purpose: Training-data contract: column names, types, value ranges, cross-column rules, row dropping.
- Examples: `src/modelling/preprocessing.py` lines 9-28.
- Pattern: `pa.DataFrameSchema(..., drop_invalid_rows=True)` used with `validate(..., lazy=True)`.

**Pydantic models (`InputData`, `PredictionOut`):**
- Purpose: API request and response contract.
- Examples: `src/web_service/lib/models.py`.
- Pattern: `Literal["M", "F", "I"]` for `sex`, `PositiveFloat` for the seven measurements. Used as the FastAPI body and `response_model`.

**Model artifact (`TransformedTargetRegressor` around `HistGradientBoostingRegressor`):**
- Purpose: Predict the number of rings. The regressor works on `log1p(rings)`, and the wrapper applies `expm1` to the output.
- Examples: `src/web_service/local_objects/model.pkl`, built by `train_model` in `src/modelling/training.py`.
- Pattern: The pickle references only scikit-learn and numpy objects (`np.log1p`, `np.expm1`), so loading it needs no project module. `/model` unwraps it with `getattr(loaded["model"], "regressor", loaded["model"])` to report the regressor class name.

**Interval artifact (`interval.json`):**
- Purpose: One scalar, `log_half_width`, applied on the `log1p` scale. `coverage` (0.9) is stored for reporting by `/model`.
- Examples: `src/web_service/local_objects/interval.json`. Written by `src/modelling/main.py` line 54. The value 0.9 also appears as the default of `compute_interval`.
- Pattern: The interval is asymmetric on the rings scale and wider for older abalones. Both ends are computed from the same centre, `log1p(rings)`.

**Feature vector (10 columns, fixed order):**
- Purpose: The input to the model.
- Pattern: Built by `encode_sex` on both the training and the API side. The fitted model stores the order in `feature_names_in_`.

## Entry Points

**Training CLI:**
- Location: `src/modelling/main.py` (`if __name__ == "__main__":`, argparse argument `trainset_path`).
- Triggers: `uv run python src/modelling/main.py data/abalone.csv`. Works without a Prefect server (README).
- Responsibilities: One run of `train-model`. Writes both artifacts.

**Deployment runner:**
- Location: `src/modelling/deployment.py`.
- Triggers: `uv run python src/modelling/deployment.py` with `PREFECT_API_URL` set. In the container, `bin/run_services.sh` starts it in the background once `$PREFECT_API_URL/health` answers.
- Responsibilities: `main.serve(name="weekly-training", cron="0 0 * * 0", parameters={"trainset_path": ...}, pause_on_shutdown=False)`. Stays in the foreground and runs the flow on schedule and on demand.

**API:**
- Location: `src/web_service/main.py` (`app = FastAPI(...)`, line 14).
- Triggers: `uv run uvicorn src.web_service.main:app --port 8000` locally, or `exec uvicorn src.web_service.main:app --host 0.0.0.0 --port 8001` in the container. Run from the repository root.
- Routes:
  - `GET /` (`home`): static health check. It returns 200 even when no model is loaded.
  - `GET /model` (`model_info`): model class name, `trained_at`, `interval_coverage`. Returns 503 without artifacts.
  - `POST /predict` (`predict`): returns 201 on success, 422 on invalid input, 503 without artifacts.
  - `GET /docs`: FastAPI generated documentation.

**Container entrypoint:**
- Location: `bin/run_services.sh` (`CMD` in `Dockerfile.app`).
- Process topology:

| Process | How it starts | Container port (host port) | Role |
|---|---|---|---|
| Prefect server | Background: `prefect server start --host 0.0.0.0 --port 4201` | 4201 (4200) | Flow API and UI |
| Deployment runner | Background, after `$PREFECT_API_URL/health` answers: `python src/modelling/deployment.py` | none | Serves `weekly-training` |
| API | Foreground, `exec uvicorn ... --port 8001` (replaces bash) | 8001 (8000) | Prediction service |

- No supervision: nothing restarts the Prefect server or the runner. The API does not wait for Prefect, and the wait loop has no timeout.

**Notebooks (manual):**
- Location: `notebooks/eda.ipynb`, `notebooks/modelling.ipynb`.
- Triggers: Run by hand from `notebooks/`, because they read `../data/abalone.csv`.
- Responsibilities: Exploration, and model comparison with repeated 5-fold cross-validation logged to MLflow (`mlflow.set_experiment("abalone")`). They import nothing from `src/`.

**Tests:**
- Location: `tests/`, run with `uv run pytest` (`pythonpath = ["."]` in `pyproject.toml`).

**CI:**
- Location: `.github/workflows/ci.yaml`.
- Triggers: Pull requests, and pushes to `main`.
- Responsibilities: Job `CI` runs `uv sync --locked`, `pre-commit run --all-files` and `pytest`. Job `docker` builds `Dockerfile.app`, runs the container, calls `GET /` and `POST /predict`, and checks the Prefect health endpoint.

## Error Handling

**Strategy:** Fail at the boundary and report the failure. The repository defines no custom exception classes, no global exception handlers and no retries.

**Patterns:**
- Training data: Pandera runs with `lazy=True`, so it collects all failures. Row-level failures are dropped. Structural failures raise `SchemaErrors` and fail the flow run.
- API input: Pydantic validation returns 422 (`tests/test_api.py`).
- Missing artifacts: `HTTPException(status_code=503)` raised from `get_model()` (`src/web_service/main.py` lines 26-29).
- Unhandled failures, such as a scikit-learn feature-name mismatch or a pickle read while it is being written, are not caught and produce a 500. The cache is updated only after both loads succeed, so the next request retries the load.
- Prefect: no `retries=` is set anywhere in `src/`. A failed run is recorded in the Prefect server. No alerting is configured in the repository.

## Cross-Cutting Concerns

**Logging:**
- Prefect run logger only: `get_run_logger()` in `src/modelling/main.py` (line 26) logs the number of dropped rows and the test RMSE.
- Tasks, the helpers in `src/modelling/` and the API do not log. The API uses uvicorn's defaults.
- The notebooks log to MLflow. That path is not part of the production code.

**Validation:**
- Two independent rule sets, kept in sync by hand. The comment at `src/modelling/preprocessing.py` line 8 says "same rules as the API input".
  - Training (Pandera): every size and weight above 0, `Sex` in F/I/M, `Rings` at least 1, shucked, viscera and shell weight at most the whole weight.
  - API (Pydantic): `sex` in M/F/I, seven `PositiveFloat` measurements. The API has no cross-field rule, so it accepts a shucked weight above the whole weight, which training would drop.

**Authentication:**
- None. The API and the Prefect server have no authentication configured. The container binds both to `0.0.0.0`, and the README publishes both ports with `-p 0.0.0.0:...`.

**Configuration:**
- No settings file. Values are module constants:
  - Artifact paths: `src/modelling/main.py` lines 18-20, `src/web_service/main.py` lines 10-12.
  - Data path and cron: `src/modelling/deployment.py` lines 5 and 11.
  - Hyperparameters and seed: `src/modelling/training.py` lines 17-23, `src/modelling/preprocessing.py` line 61.
  - Coverage 0.9: `src/modelling/main.py` lines 50 and 54.
  - Ports: `bin/run_services.sh`, `Dockerfile.app`, `.github/workflows/ci.yaml`.
- Environment variables: `PREFECT_API_URL` (read by the Prefect client, required by `deployment.py`), `PREFECT_UI_API_URL` (set in `Dockerfile.app` for the UI).

**Serialization and Version Coupling:**
- `model.pkl` is a pickle. It must be loaded with the scikit-learn version that wrote it. The locked version is 1.9.1 (`uv.lock`), and the README requires Python 3.11 for this reason. A version mismatch warns, and results may differ.
- Loading a pickle runs code embedded in the file. Write access to `src/web_service/local_objects/` is therefore the trust boundary of the API.

**Import Conventions:**
- `src/modelling/main.py` and `src/modelling/deployment.py` use bare imports (`from preprocessing import ...`). They run only as scripts (`python src/modelling/main.py`). Module mode fails: `python -m src.modelling.main` raises `ModuleNotFoundError: No module named 'preprocessing'`.
- Every other import uses the `src.` prefix (`from src.web_service.lib.models import InputData`), and tests use it too.
- `main.py` and `utils.py` exist in both packages. This is safe only because the bare imports resolve against `src/modelling/`.

**Artifact Persistence in the Container:**
- `Dockerfile.app` copies the committed `model.pkl` into the image. The documented `docker run` has no volume, so a model written by a retrain lives in the container's writable layer. It is lost when the container is removed, and a rebuild restores the committed model.

**Test Boundary:**
- Tests cover the Prefect tasks through `.fn` and the API through `TestClient`. No test runs the `main` flow body or `deployment.py`. The API test fixture (`model_copy` in `tests/test_api.py`) copies the artifacts so tests can change them without touching the committed files.

---

*Architecture analysis: 2026-10-23*
