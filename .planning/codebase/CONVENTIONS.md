# Coding Conventions

**Analysis Date:** 2026-10-23

## Naming Patterns

**Files:**
- Python modules are `snake_case.py` and named after their role: `src/modelling/preprocessing.py`, `src/modelling/training.py`, `src/modelling/utils.py`, `src/web_service/lib/inference.py`, `src/web_service/lib/models.py`, `src/web_service/utils.py`.
- Two modules are both called `main.py`: the training flow `src/modelling/main.py` and the FastAPI app `src/web_service/main.py`. Import them by full path (`src.web_service.main`) to avoid a clash.
- Deployment script: `src/modelling/deployment.py`. Shell entry point: `bin/run_services.sh`.
- Tests: `tests/test_<module>.py`, one file per module group (see `TESTING.md`).

**Functions:**
- `snake_case`, verb first for actions: `load_data`, `validate_data`, `encode_sex`, `extract_x_y`, `split_train_test`, `train_model`, `evaluate_model`, `compute_interval`, `pickle_object`, `save_json`, `load_object`, `load_json`, `build_features`, `run_inference`, `prediction_interval`, `get_model`.
- Route handlers are named for what they return or do, not for the HTTP verb: `home` (`GET /`), `model_info` (`GET /model`), `predict` (`POST /predict`) in `src/web_service/main.py`.
- The Prefect flow is the function `main` with a kebab-case display name: `@flow(name="train-model")` in `src/modelling/main.py`.
- Test functions: `test_<unit>_<expected_behavior>`, for example `test_predict_wrong_sex` and `test_validate_data_drops_impossible_rows`.

**Variables:**
- `snake_case`. DataFrames are `df`, or `raw_df` before validation.
- Feature and target splits use the scikit-learn names `X`, `y`, `X_train`, `X_test`, `y_train`, `y_test`. The capital `X` is intentional. Naming rules `N803` and `N806` (capital argument and variable names) are not enabled, so it passes lint.
- Short math names are common in numeric code: `q`, `n`, `level`, `center`, `residuals` (`src/modelling/training.py`, `src/web_service/lib/inference.py`).

**Types:**
- Pydantic models are `PascalCase` nouns. Request: `InputData`. Response: `PredictionOut` (`src/web_service/lib/models.py`). For a new response model, use the `...Out` suffix.
- Fixed choices use `Literal[...]`, as in `sex: Literal["M", "F", "I"]`. The repo has no `Enum` classes.

**Constants and Module State:**
- Module-level constants are `UPPER_SNAKE_CASE`: `SEX_CATEGORIES` and `ABALONE_SCHEMA` (`src/modelling/preprocessing.py`), `LOCAL_OBJECTS`, `MODEL_PATH`, `INTERVAL_PATH` (`src/modelling/main.py`, `src/web_service/main.py`), `DATA_PATH` (`src/modelling/deployment.py`), `ABALONE` (test payload in `tests/test_api.py`).
- Private module state has a leading underscore: `_loaded`, the model cache in `src/web_service/main.py`.
- Hyperparameters and seeds are inline literals, not named constants: `learning_rate=0.05, max_iter=200, max_leaf_nodes=15, random_state=42` (`src/modelling/training.py`), `random_state=42` (`src/modelling/preprocessing.py`), and `coverage=0.9` appears twice in `src/modelling/main.py`.

**Data Column Names:**
- DataFrame columns keep the CSV headers, with spaces and capitals: `"Whole weight"`, `"Shell weight"`, `"Rings"`, `"Sex"`. One-hot columns are `Sex_F`, `Sex_I`, `Sex_M`.
- API fields are `snake_case` (`whole_weight`). The mapping to CSV names lives in one place, `build_features` (`src/web_service/lib/inference.py`). Keep the API field names stable; clients depend on them.

**Prefect Names:**
- Flow `train-model`, deployment `weekly-training`, table artifact key `model-rmse`. All kebab-case (`src/modelling/main.py`, `src/modelling/deployment.py`).

## Code Style

**Formatting:**
- Tool: `ruff format`, ruff 0.17.2. This is the version locked in `uv.lock`, the `ruff>=0.17.2` pin in the dev group, and the `v0.17.2` pre-commit hook.
- Defaults apply (no `[tool.ruff]` table): 88 columns, 4-space indent, double quotes, magic trailing commas respected. A trailing comma keeps a call one argument per line (see `main.serve(...)` in `src/modelling/deployment.py`).
- Verified 2026-10-23: `ruff format --check` passes on `src` and `tests` (13 files) and on `notebooks` (2 files).
- Line endings are LF in git (`git ls-files --eol` shows `i/lf`). `core.autocrlf=true` makes the Windows working copy CRLF. Only `*.sh` is forced to LF by `.gitattributes`.
- The formatter does not re-wrap comments or docstrings. Two lines currently exceed 88 columns: a 100-column header comment (`src/modelling/main.py`, line 1) and an 89-column docstring (`src/modelling/preprocessing.py`, line 45). Both pass because E501 is not enabled. Keep new ones within 88.

**Linting:**
- Tool: `ruff check`, run with `--fix` by pre-commit (`.pre-commit-config.yaml`). CI runs `uv run pre-commit run --all-files`.
- Rule set: ruff's built-in defaults, since `pyproject.toml` has no `[tool.ruff]` table. `ruff check --show-settings` lists about 400 enabled rules. Enforced families include pyflakes `F` (unused imports, `F401`), isort `I001` (import order), pyupgrade `UP` (`UP006`, `UP007`, `UP035`: built-in generics, no `typing.Optional` or `typing.List`), bugbear `B` (`B006`: no mutable default arguments), `E722` (no bare `except`), `W605` (valid escapes), `SIM`, `RUF`, `PT`, `DTZ`, `G`, `LOG`.
- Not enforced: docstrings (`D100` and similar), annotations (`ANN`), naming beyond `N999`, line length (`E501`), `print` (`T201`), `assert` (`S101`), magic numbers (`PLR2004`), and f-strings in logging (`G004`). Passing lint therefore does not prove that a function has a docstring or a type hint. Check that yourself (the `ast` audits in this document are one way).
- Suppression comments: none in `src/` or `tests/` (`# noqa`, `# type: ignore`). Fix the code instead.
- Notebooks are linted and formatted too: ruff discovers `notebooks/*.ipynb`, and the pre-commit hooks include the `jupyter` file type. Both notebooks pass.

## Import Organization

**Order:** enforced by ruff `I001` (`ruff check --fix` sorts it). Three groups, separated by one blank line:
1. Standard library
2. Third-party
3. Project imports

Example from `src/web_service/main.py`:
```python
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.web_service.lib.inference import prediction_interval, run_inference
from src.web_service.lib.models import InputData, PredictionOut
from src.web_service.utils import load_json, load_object
```

**Two local import styles coexist. Each belongs to one area:**
- Repo-root imports (`src.` prefix) are used by the API and the tests: `from src.modelling.preprocessing import encode_sex` (`src/web_service/lib/inference.py`), `from src.web_service.main import app` (`tests/test_api.py`). Use this style for anything the API or the tests import.
- Bare sibling imports are used inside `src/modelling/`: `from preprocessing import (...)` in `src/modelling/main.py`, `from main import main` in `src/modelling/deployment.py`. They work because the scripts run as files (`python src/modelling/main.py`), which puts `src/modelling/` on `sys.path`.
- Do not import the same file both ways in one process. Python loads `preprocessing` and `src.modelling.preprocessing` as two separate module objects.
- No relative imports (`from .x import`) and no `sys.path` edits anywhere in the repo.

**Packages:** no `__init__.py` anywhere. `src/`, `src/modelling/`, `src/web_service/`, `src/web_service/lib/` and `tests/` are implicit namespace packages. Create new folders the same way.

## Error Handling

**Strategy:** validate at the boundary, raise an HTTP error where the client can act on it, and let everything else propagate. There are no custom exception classes, no retries, and no catch-all handlers.

**Patterns:**
- API input: Pydantic constraints in `src/web_service/lib/models.py` (`PositiveFloat`, `Literal`). Invalid bodies get a 422 from FastAPI with no handler code.
- Missing artifacts: `get_model` in `src/web_service/main.py` converts `FileNotFoundError` into a 503:
```python
    try:
        trained_at = max(MODEL_PATH.stat().st_mtime, INTERVAL_PATH.stat().st_mtime)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="No trained model, run the training flow first"
        )
```
- Bad data rows: `ABALONE_SCHEMA` in `src/modelling/preprocessing.py` uses `drop_invalid_rows=True` and `validate(df, lazy=True)`. Rows that break a check are dropped, and the flow logs the count (`src/modelling/main.py`). A structural error, such as a missing column, raises `pandera.errors.SchemaErrors` and fails the run.
- The training flow catches nothing. An exception is a failed Prefect run.
- Duplicated input rules are kept in sync by hand. The sizes-and-weights `> 0` rule and the sex categories exist in both `src/web_service/lib/models.py` and `src/modelling/preprocessing.py`. The comment at `src/modelling/preprocessing.py` line 8 names the other location.

## Logging

**Framework:** Prefect run logger inside the flow; no logging in the API.

**Patterns:**
- In the flow: `logger = get_run_logger()` at the top of `main` (`src/modelling/main.py`), then `logger.info(f"...")`. f-strings are accepted here.
- Metrics history goes to a Prefect artifact, not the log: `create_table_artifact(key="model-rmse", ...)` adds one row per run.
- In `src/web_service/`: no logger, no `print`. Uvicorn's access log is the only request log.
- `print` does not appear anywhere in `src/` or `tests/`.

## Comments

**When to Comment:**
- Comments explain why, not what. Examples:
  - `# same rules as the API input (src/web_service/lib/models.py): sizes and weights > 0` (`src/modelling/preprocessing.py`)
  - `# .fn runs the function without the prefect task machinery` (`src/web_service/lib/inference.py`)
  - `# exec: uvicorn replaces bash, so it gets the signal of docker stop` (`bin/run_services.sh`)
- Two styles. Section markers inside a function start with a capital (`# Read and validate data`, `# Train and evaluate the model` in `src/modelling/main.py`). Explanatory comments start lowercase and have no final period.
- Inline comments use two spaces before `#` and stay short: `df.loc[2, "Shucked weight"] = 1.0  # heavier than the whole abalone` (`tests/test_preprocessing.py`).
- No commented-out code. No module docstrings in the Python modules. The only module header comment is at the top of `src/modelling/main.py`.

**JSDoc/TSDoc (docstrings):**
- Every function in `src/` has a docstring (checked with `ast`, 2026-10-23). Use a single line in the imperative or descriptive form, ending with a period: `"""Read the abalone csv file."""`.
- For a contract that needs a formula or a warning, use a summary line, a blank line, then details. `compute_interval` in `src/modelling/training.py` does this to explain the calibration set and the log scale.
- No `Args:` or `Returns:` sections. The types are in the signature.
- A FastAPI route's docstring becomes its OpenAPI description: `home` is documented as "Health check of the API.". Keep route docstrings readable by API users.
- Test functions have no docstrings. Helpers and fixtures do (`make_abalones` in `tests/test_preprocessing.py`, `model_copy` in `tests/test_api.py`).

## Type Hints

- Every function in `src/` has parameter and return annotations (checked with `ast`). Side-effect functions return `-> None`: `pickle_object`, `save_json`.
- Use built-in generics only: `tuple[pd.DataFrame, pd.Series]`, `dict`, `list`. `typing.Optional`, `typing.List` and `typing.Dict` are flagged by `UP006` and `UP007`.
- Pickled objects are typed `Any` (`src/modelling/utils.py`, `src/web_service/utils.py`).
- Path parameters are inconsistent. `load_data`, `pickle_object`, `save_json`, `load_object` and `load_json` annotate `path: str`, while callers pass `pathlib.Path` objects (`MODEL_PATH`, `INTERVAL_PATH`). Both work with `open()` and `pd.read_csv()`. For new code, annotate a path parameter as `Path` when its callers pass `Path`.
- The flow parameter `main(trainset_path: Path)` is annotated `Path`, but the CLI and the deployment pass a `str`. The value is used as a path either way.

## Function Design

**Size:** 39 of the 41 functions in `src/` and `tests/` are 15 lines or fewer (mean 7.4 lines, measured 2026-10-23). The longest are the flow `main` (32 lines, `src/modelling/main.py`, a sequence of steps) and `build_features` (18 lines, `src/web_service/lib/inference.py`).

**Pipeline steps are Prefect tasks.** Each step is a `@task` in `src/modelling/preprocessing.py`, `src/modelling/training.py` or `src/modelling/utils.py`, and `main` calls them in order: `load_data`, `validate_data`, `encode_sex`, `extract_x_y`, `split_train_test`, `train_model`, `evaluate_model`, `compute_interval`, `pickle_object`, `save_json`. A new step follows the same pattern: a typed, documented function with `@task`.

**Calling a task's plain function:** outside a flow, call `task.fn(...)`. The API uses `encode_sex.fn(df)` and every test does the same (`validate_data.fn(df)`). `.fn` skips the Prefect task machinery.

**Parameters:** keep them few (at most 4 in this repo). Tunable values are keyword arguments with defaults: `split_train_test(X, y, test_size=0.2)`, `compute_interval(model, X, y, coverage=0.9)`.

**Return values:**
- Functions return new objects and do not mutate their input. `encode_sex` starts with `df = df.copy()`, then adds columns and returns `df.drop(columns="Sex")`.
- The API helpers (`build_features`, `run_inference`, `prediction_interval`) take values and return values, with no I/O. File loading happens only in `get_model` (`src/web_service/main.py`).

## Module Design

**Layout:**
- `src/modelling/`: pipeline code. Step functions in `preprocessing.py` and `training.py`, file savers in `utils.py`, the flow in `main.py`, the scheduler script in `deployment.py`.
- `src/web_service/`: `main.py` (FastAPI app), `utils.py` (file loaders), and `lib/` for logic without its own I/O (`inference.py`, `models.py`).

**Exports:** no barrel files and no re-exports. Import from the module that defines the name.

**Entry points** use `if __name__ == "__main__":`:
- `src/modelling/main.py`: `argparse` CLI with one positional argument, `trainset_path`.
- `src/modelling/deployment.py`: `main.serve(name="weekly-training", cron="0 0 * * 0", ...)`.

**Shared between training and serving:** `encode_sex` (`src/modelling/preprocessing.py`) is used by the flow and by the API (`src/web_service/lib/inference.py`). A change to its output changes the model inputs. Retrain and run `tests/test_inference.py` after any change.

**Notebook duplication:** the cross-validation cell of `notebooks/modelling.ipynb` repeats the model definition of `train_model` in `src/modelling/training.py`. Nothing links the two. A hyperparameter change has to be made in both.

## Pydantic and FastAPI

- Request and response bodies are Pydantic v2 `BaseModel` classes. Put constraints in the types (`PositiveFloat`, `Literal`) rather than in route code.
- Route decorators declare the contract: `@app.post("/predict", response_model=PredictionOut, status_code=201)`. Handlers return a `dict` that matches the model.
- `GET /model` reports the inner estimator name by unwrapping the `TransformedTargetRegressor` (`getattr(loaded["model"], "regressor", loaded["model"])`, `src/web_service/main.py`).

## Notebooks

- `notebooks/eda.ipynb` and `notebooks/modelling.ipynb` are committed with their outputs, including four PNG plots in `eda.ipynb`.
- Data paths are relative to the notebook (`pd.read_csv("../data/abalone.csv")`), so run them from `notebooks/`.
- MLflow output (`mlruns/`, `mlflow.db`) is git-ignored (`.gitignore`).

## Configuration

- Paths resolve from `__file__`, never from the working directory: `Path(__file__).parents[1] / "web_service" / "local_objects"` (`src/modelling/main.py`), `Path(__file__).parents[2] / "data" / "abalone.csv"` (`src/modelling/deployment.py`), `Path(__file__).parent / "local_objects"` (`src/web_service/main.py`). Exception: the training CLI takes the CSV path as an argument, relative to the current directory.
- Runtime settings come from environment variables only: `PREFECT_API_URL` (README), and `PREFECT_API_URL` and `PREFECT_UI_API_URL` (`Dockerfile.app`). The app has no settings file.

## Dependencies

- `uv` manages everything. Runtime dependencies are in `[project] dependencies`; tools and notebook libraries are in `[dependency-groups] dev` (`pyproject.toml`).
- `uv.lock` is committed. CI runs `uv sync --locked`, and the `uv-lock` pre-commit hook keeps the lock in step.
- Version pins carry their reason on the line above, with an upstream link: `"fastapi>=0.150.0,<0.155"` (Prefect 3.9 uses an argument that FastAPI 0.155 removed) and `"sqlalchemy<2.1"` (breaks the Prefect scheduler). Add a pin the same way.
- Python 3.11 only: `requires-python = ">=3.11,<3.12"`. Use 3.11 features freely (`datetime.UTC` is already used).

## Git

- Commit subjects are lowercase, imperative and short, with an optional `area:` prefix. Examples from `git log`: `readme: set PREFECT_API_URL per terminal instead of prefect config set`, `keep fastapi below 0.155, it breaks the prefect server`. Put the reason after a comma when a pin or workaround is involved.
- Branches are kebab-case (`ci-docker-build`, `fix-fastapi-prefect`). Changes merge through pull requests, recorded as merge commits (`Merge pull request #42 from andrfr21/readme-fixes`).

---

*Convention analysis: 2026-10-23*
