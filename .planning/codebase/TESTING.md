# Testing Patterns

**Analysis Date:** 2026-10-23

## Test Framework

**Runner:**
- pytest 9.1.1 (locked in `uv.lock`; `pytest>=9.1.1` in the `dev` dependency group of `pyproject.toml`).
- Config: `[tool.pytest.ini_options]` in `pyproject.toml` with `pythonpath = ["."]`, so `src.` imports resolve from the repo root. No `pytest.ini`, `setup.cfg`, `tox.ini` or `conftest.py` exists.
- No `testpaths` is set, so collection starts at the repo root. Dot-directories such as `.venv` are skipped by pytest's default ignore patterns. The only `test_*.py` files are in `tests/`.

**Assertion Library:**
- Plain `assert` (pytest rewrites it to show values on failure), `pytest.approx` for floats, `pytest.raises` for expected exceptions.
- HTTP tests use `TestClient` from `fastapi.testclient`, which re-exports Starlette's `TestClient` (`fastapi/testclient.py`). Starlette imports `httpx2` first and falls back to `httpx`. The dev group lists `httpx2>=2.14.0` (2.16.0 locked). `httpx` 0.28.1 is installed as a dependency of `prefect`.

**Other test dependencies:** `pandera.errors` (exception type for schema failures), `numpy.random.default_rng` (seeded synthetic data), and the standard library `os` and `shutil` (file copies and timestamps in fixtures).

**Run Commands:**
```bash
uv run pytest                                                # All tests (README and CI command)
uv run pytest tests/test_api.py                              # One file
uv run pytest tests/test_api.py::test_predict_without_model  # One test
uv run pytest -k predict                                     # Tests whose name matches
uv run pytest --collect-only -q                              # List tests without running them
```
- Watch mode: not configured.
- Coverage: not configured. See the Coverage section.
- Measured 2026-10-23 on Windows 11 with the project's `.venv` (pytest 9.1.1): `20 passed in 12.33s`. CI runs the same suite on `ubuntu-latest` (`.github/workflows/ci.yaml`).

## Test File Organization

**Location:**
- A separate top-level `tests/` directory. Tests are not co-located with the code. The directory is flat: no subdirectories, no `conftest.py`, no `__init__.py`.

**Naming:**
- `tests/test_<module>.py`, named after the module or module group under test. Keep basenames unique across the repo, because pytest imports test files without packages.
- Test functions: `test_<unit>_<expected_behavior>` in `snake_case`. No test classes.

**Structure:**
```
tests/
├── test_api.py            # src/web_service/main.py: endpoints and model reload (9 items)
├── test_inference.py      # src/web_service/lib/inference.py (2 items)
├── test_preprocessing.py  # src/modelling/preprocessing.py (6 items)
└── test_training.py       # src/modelling/training.py (3 items)
```
Total: 20 items. `test_api.py` has 8 test functions; `test_predict_measurement_not_positive` runs twice (`[0]` and `[-0.1]`).

## Test Structure

**Suite Organization:**

Module-level functions only. Shared constants come first, then helpers and fixtures, then the tests. Example from `tests/test_api.py`:
```python
ABALONE = {
    "sex": "M",
    "length": 0.455,
    ...
}

@pytest.mark.parametrize("value", [0, -0.1])
def test_predict_measurement_not_positive(value):
    response = client.post("/predict", json={**ABALONE, "height": value})
    assert response.status_code == 422
```

**Patterns:**
- Arrange, act, assert, with no section markers. A comment explains the expected numbers when the setup is not obvious: `# y = 20 * Length, so a linear regression is perfect and the RMSE is 0` (`tests/test_training.py`).
- Invalid variants are built from the valid payload. `{**ABALONE, "sex": "X"}` changes one field. A dict comprehension drops one (`tests/test_api.py::test_predict_missing_field`).
- One behavior per test. A test can make several asserts when they describe one result (`test_predict` checks `rings`, `age` and the interval order).
- No setup or teardown methods. Cleanup comes from `tmp_path`.
- Assert the status code first, then the body.

## Mocking

**Framework:** none. The repo has no `unittest.mock` and no `pytest-mock`. Pytest's built-in `monkeypatch` redirects module-level paths and state.

**Patterns:**
```python
@pytest.fixture
def model_copy(tmp_path, monkeypatch):
    """Use a copy of the model files, so a test can change or delete them."""
    for path in [main.MODEL_PATH, main.INTERVAL_PATH]:
        shutil.copy(path, tmp_path / path.name)
    monkeypatch.setattr(main, "MODEL_PATH", tmp_path / main.MODEL_PATH.name)
    monkeypatch.setattr(main, "INTERVAL_PATH", tmp_path / main.INTERVAL_PATH.name)
    monkeypatch.setattr(main, "_loaded", {})
    return tmp_path
```
- A retraining is simulated by changing a file's modification time, not by training again: `os.utime(model_copy / "model.pkl", (stat.st_atime, stat.st_mtime + 3600))` (`tests/test_api.py::test_new_model_is_loaded_without_restart`). `get_model` in `src/web_service/main.py` reloads when the newer of the two artifact mtimes changes.

**What to Mock:**
- The artifact locations (`MODEL_PATH`, `INTERVAL_PATH`) in `src/web_service/main.py`, via `monkeypatch`, when a test must delete, replace or touch the files.
- The module-level cache `_loaded` in `src/web_service/main.py`. Reset it with `monkeypatch.setattr(main, "_loaded", {})` in any test whose result depends on cache state.

**What NOT to Mock:**
- The model, scikit-learn, pandas, pandera and FastAPI. The existing tests use the real libraries and the real pickled model, so a version mismatch between the pickle and the installed scikit-learn shows up as a failing test. The README warns about exactly this.
- No network calls and no Prefect server are needed. Prefect tasks are called through `.fn` (see Common Patterns).

## Fixtures and Factories

**Fixtures:**
- `model_copy` in `tests/test_api.py` (function scope). Copies the two artifacts into `tmp_path`, redirects the module paths and the cache, and returns the temporary directory.
- Built-in fixtures in use: `tmp_path` and `monkeypatch`.
- No fixture is shared across files. There is no `conftest.py`.

**Factories and test data:**
- `make_abalones(n)` in `tests/test_preprocessing.py` returns `n` identical valid rows with the pipeline column names. The rows copy the first row of `data/abalone.csv`. To test a rule, break one row: `df.loc[1, "Height"] = 0`.
- `ABALONE` in `tests/test_api.py` is a valid request body, using the API's snake_case field names.
- Synthetic regression data uses a fixed generator: `rng = np.random.default_rng(0)` with `y = np.round(3 + 20 * X["Length"])` (`tests/test_training.py`).
- Tests never read `data/abalone.csv`. No fixture files are stored under `tests/`.

**Committed artifacts used directly:**
- `src/web_service/local_objects/model.pkl` and `src/web_service/local_objects/interval.json` are tracked in git. `tests/test_inference.py` loads the real model. `tests/test_api.py` serves it directly, except in the tests that use `model_copy`.
- `test_model_info` asserts the estimator name `HistGradientBoostingRegressor`. If the model class changes, update that test.
- Retraining overwrites the tracked files. `uv run python src/modelling/main.py data/abalone.csv` rewrites `model.pkl` and `interval.json` in the working tree, and the API tests then run against the new model.

## Coverage

**Requirements:** none enforced. `pytest-cov` and `coverage` are not in the dev dependencies, there is no `[tool.coverage]` section, and CI has no coverage step.

**View Coverage:** not available as configured. Add `pytest-cov` to the dev group before measuring. Nothing has been measured for this repo.

**Gaps.** Found by static mapping on 2026-10-23: no test imports these modules or names.
- `src/modelling/main.py`: the `main` flow, the argparse CLI, the table artifact and the artifact writes. CI never runs the training flow.
- `src/modelling/utils.py`: `pickle_object` and `save_json`. They run only inside the flow, and no test runs the flow.
- `src/modelling/deployment.py`: the scheduling script.
- `src/modelling/preprocessing.py::load_data`: the CSV reader.
- `src/web_service/utils.py::load_json`: reached only through `get_model` in the API tests.
- `src/web_service/lib/models.py`: reached only through the API tests.
- `train_model` on real data: `tests/test_training.py` uses synthetic linear data. The RMSE of about 2.2 rings stated in the README is not asserted by any test.
- `notebooks/`: not tested.

## Test Types

**Unit Tests:**
- Pure functions on small in-memory DataFrames or arrays: `tests/test_preprocessing.py`, `tests/test_training.py`, and `test_prediction_interval_is_wider_for_old_abalones` in `tests/test_inference.py`.
- Scope: one function, called through `.fn`, asserting on its return value.

**Integration Tests (in-process):**
- `tests/test_api.py`: the FastAPI app through `TestClient`, with the real pickled model, and real files under `tmp_path` for the reload scenarios.
- `tests/test_inference.py::test_features_match_the_model`: builds features and checks column names and order against the model's `feature_names_in_`.

**Statistical Property Test:**
- `tests/test_training.py::test_compute_interval_covers_the_calibration_set`: fits on 500 synthetic points, then asserts that at least 90% of the 500 calibration points fall inside the interval. The seed is fixed (`default_rng(1)`).

**E2E Tests:**
- Not in pytest. The CI `docker` job (`.github/workflows/ci.yaml`) builds `Dockerfile.app`, starts the container and checks it with `curl`: `GET /`, `POST /predict` with a valid body, and the Prefect `/api/health` endpoint. These are smoke checks. They do not assert on response content.

## Common Patterns

**Calling Prefect tasks in tests:**
```python
def test_validate_data_keeps_valid_rows():
    df = make_abalones(3)
    assert len(validate_data.fn(df)) == 3
```
Call `task.fn(...)` to run the plain function. Every test in the repo does this; none calls a task object directly.

**Async Testing:** not applicable. The repo has no async code and no async test plugin.

**Error Testing:**
```python
def test_validate_data_fails_on_missing_column():
    df = make_abalones(3).drop(columns="Height")
    with pytest.raises(pandera.errors.SchemaErrors):
        validate_data.fn(df)
```
For HTTP errors, assert the status code: `422` for invalid input, `503` for a missing model (`tests/test_api.py::test_predict_without_model`).

**Floating-point comparisons:** use `pytest.approx`:
```python
assert result["age"] == pytest.approx(result["rings"] + 1.5)
```

**Parametrization:** `@pytest.mark.parametrize("value", [0, -0.1])` on a single-parameter test. Pytest names the cases `[0]` and `[-0.1]`.

**Determinism:** all randomness is seeded. The model uses `random_state=42` (`src/modelling/training.py`), and the tests use `np.random.default_rng(seed)` with fixed seeds. Temporary files live in `tmp_path`.

## Adding Tests

- A new function in `src/modelling/preprocessing.py` or `training.py`: add it to the matching `tests/test_*.py`, call it through `.fn`, and build the input with a small helper like `make_abalones`.
- A new endpoint, or a change to `src/web_service/main.py`: add it to `tests/test_api.py` and reuse `ABALONE`. If the test changes artifacts, use `model_copy`.
- Testing the flow (`src/modelling/main.py`): there is no test yet, and the module cannot be imported from a test as the repo is set up. Its bare sibling imports (`from preprocessing import ...`) need `src/modelling/` on `sys.path`. With only the repo root on the path, `import src.modelling.main` fails with `ModuleNotFoundError: No module named 'preprocessing'` (verified 2026-10-23). Add the directory in the test (for example with `monkeypatch.syspath_prepend`). Redirect `MODEL_PATH` and `INTERVAL_PATH` with `monkeypatch` too, so the committed artifacts are not overwritten. Pass a small CSV written under `tmp_path`.
- After any change to `encode_sex` or the model, run `tests/test_inference.py`. It fails when the feature names or their order no longer match the pickled model.

---

*Testing analysis: 2026-10-23*
