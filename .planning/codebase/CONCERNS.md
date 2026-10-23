# Codebase Concerns

**Analysis Date:** 2026-10-23

**Evidence tags:** [verified] = reproduced by running code or tools during this audit. [code] = read from source, not executed. [doc] = a claim in the README or a comment, checked against the code.

## Priorities

1. The API accepts inputs the training pipeline rejects, and clamps out-of-range measurements without any signal (Known Bugs, Test Coverage Gaps).
2. The README publishes the API and an unauthenticated Prefect server on all host interfaces (Security Considerations).
3. The weekly retraining reads the same fixed CSV with a fixed seed, so it reproduces the same model. Nothing gates a new model before it goes live (Known Bugs, Missing Critical Features).
4. The model is a `pickle` file tracked in git and loaded by the API on every reload (Security Considerations).
5. Several README and docstring claims have no code behind them: the hyperparameter selection, the 74% coverage figure, "training time" in `GET /model`, and "history is kept" (Tech Debt).

## Tech Debt

**Validation rules are duplicated and diverge between training and the API:**
- Issue: `src/modelling/preprocessing.py` line 8 says the schema uses "the same rules as the API input" (`src/web_service/lib/models.py`). That is only partly true. The training schema also requires `Shucked weight`, `Viscera weight` and `Shell weight` to be at most `Whole weight` (lines 21-26), `Rings >= 1` (line 19), and `Sex` in `F`/`I`/`M` (line 11). `InputData` enforces only `> 0` and the `Sex` literal. [verified: `POST /predict` with `shucked_weight: 5.0` and `whole_weight: 0.514` returns 201 with a prediction.]
- Files: `src/modelling/preprocessing.py`, `src/web_service/lib/models.py`
- Impact: The flow drops 6 of the 4,177 rows in `data/abalone.csv` [verified]. The API serves predictions for rows of that kind, with a normal-looking interval.
- Fix approach: Add a `model_validator` to `InputData` with the three part-vs-whole checks, or move the rules into one definition that both modules import. Add test cases for viscera and shell (see Test Coverage Gaps).

**Serving imports the training package:**
- Issue: `src/web_service/lib/inference.py` line 5 imports `encode_sex` from `src/modelling/preprocessing.py` and calls it through Prefect's task wrapper (`encode_sex.fn`, line 26). The API process therefore imports `prefect` and `pandera` at startup. [code]
- Files: `src/web_service/lib/inference.py`, `src/modelling/preprocessing.py`
- Impact: A change to the training module, or a Prefect upgrade, changes the live API. `pyproject.toml` already carries two Prefect-related pins (lines 14-24).
- Fix approach: Move feature building (a plain `encode_sex` function and the fixed column order) into a module with no Prefect or pandera imports. The flow and the API both import it.

**Model and interval are written as two separate, non-atomic files:**
- Issue: `pickle_object` (`src/modelling/utils.py` lines 9-12) and `save_json` (lines 16-20) open the destination in place. The flow writes `model.pkl` (`src/modelling/main.py` line 53) and then `interval.json` (line 54) as two steps. [code]
- Files: `src/modelling/utils.py`, `src/modelling/main.py`, `src/web_service/main.py`
- Impact: See Known Bugs (mixed pair during a reload, and a read of a partial file).
- Fix approach: Write to a temporary file in the same directory and `os.replace` it into place. Better, keep the model and its interval in one artifact, so there is no pair to keep in sync.

**Docstring claims hyperparameters were chosen by cross-validation; no such search exists:**
- Issue: `src/modelling/training.py` lines 14-15 say "The model and its hyperparameters were chosen with a repeated cross-validation in `notebooks/modelling.ipynb`." The notebook compares three models with fixed settings (cell 7). A search for `GridSearch`, `RandomizedSearch`, `param_grid`, `optuna`, `hyperopt` and `tune` finds nothing in the repo. [verified]
- Files: `src/modelling/training.py` lines 14-19, `notebooks/modelling.ipynb`
- Impact: The provenance of `learning_rate=0.05, max_iter=200, max_leaf_nodes=15` (`training.py` line 19) is undocumented.
- Fix approach: Reword the docstring to "compared with fixed hyperparameters", or commit the tuning code that was actually used.

**README numbers with no reproducing code:**
- Issue: `README.md` line 114 reports 90% coverage overall, 95% for abalones under 12 rings, and 74% above that, over 10 random splits. No code in `src/`, `tests/`, `notebooks/` or `bin/` produces these numbers. [verified]
- Files: `README.md` line 114
- Impact: The interval caveat in the README cannot be audited from this repository.
- Fix approach: Commit the simulation, or label the figures as a dated one-off measurement.

**`GET /model` "training time" is a file timestamp:**
- Issue: `README.md` line 96 says `GET /model` shows the training time. `get_model()` takes the latest mtime of the two artifact files (`src/web_service/main.py` lines 25 and 47). [verified: `trained_at` equalled the `interval.json` write time. A fresh git checkout rewrites mtimes.]
- Files: `src/web_service/main.py`, `README.md` line 96
- Fix approach: Store `trained_at` in the artifact at training time and return that value.

**Notebook and shipped pipeline differ:**
- Issue: `notebooks/modelling.ipynb` cell 2 uses all 4,177 rows with no validation step, while the flow drops 6 first (4,171). [verified] The model table in `README.md` lines 49-53 matches the notebook's cell 7 output exactly [verified: 2.211/2.162/2.154 RMSE], so it is not produced by the shipped pipeline. The notebook also builds the dummies with `pd.get_dummies`, which puts the `Sex` columns first. `encode_sex` appends them last. [code]
- Impact: Not quantified. The numbers are presumably close, but the table cannot be reproduced from the shipped code.

**The trained model is committed to git:**
- Issue: `src/web_service/local_objects/model.pkl` (365,717 bytes) is tracked. Four commits changed it (`git log`), and `.git` is 3.4 MB. The `check-added-large-files` hook (`.pre-commit-config.yaml` line 10, default 500 KB) only inspects newly added files, so changes to `model.pkl` are not checked. [verified: hook source]
- Files: `src/web_service/local_objects/model.pkl`, `.pre-commit-config.yaml`
- Impact: Each retrain commit adds about 365 KB of binary history.
- Fix approach: Keep model binaries out of git (release asset or model registry), or accept the cost and document it.

**Implicit top-level imports in the training package:**
- Issue: `src/modelling/main.py` lines 8-16 and `src/modelling/deployment.py` line 3 import `preprocessing`, `training`, `utils` and `main` as top-level modules. These resolve only when `src/modelling/` is on `sys.path`. `src/web_service/` uses package imports (`src.web_service...`). No `__init__.py` exists under `src/` or `tests/`. [verified: `import src.modelling.main` raises `ModuleNotFoundError: No module named 'preprocessing'`.]
- Files: `src/modelling/main.py`, `src/modelling/deployment.py`
- Fix approach: Make `src/modelling` a package, use `from src.modelling.preprocessing import ...`, and run the flow with `python -m`.

**Duplicated constants:**
- `coverage=0.9` at `src/modelling/main.py` line 50 and `"coverage": 0.9` at line 54 must stay equal.
- `SEX_CATEGORIES` (`src/modelling/preprocessing.py` line 6) and `Literal["M", "F", "I"]` (`src/web_service/lib/models.py` line 7) encode the same domain.
- The age offset `1.5` appears in `src/web_service/main.py` line 67 and in `README.md` line 108.
- Fix approach: One constant each, imported on both sides.

**Smaller items (low priority):**
- `src/modelling/main.py` line 24 annotates `trainset_path: Path`, but the CLI and the deployment pass a `str`. `load_object(path: str)` (`src/web_service/utils.py` line 6) receives a `Path`.
- JSON is read and written without `encoding="utf-8"` (`src/modelling/utils.py` line 18, `src/web_service/utils.py` line 14). This is harmless for ASCII content, but the Windows default is cp1252.
- Ruff runs at its defaults, since `pyproject.toml` has no `[tool.ruff]` section. The current code passes [verified]. No type checker is configured.
- Notebooks are committed with their outputs (`notebooks/eda.ipynb` is 265 KB). Pre-commit does not strip outputs.
- Two uv versions are in play: pre-commit pins `uv-pre-commit` 0.7.17 (`.pre-commit-config.yaml` line 18), and the image installs the latest `uv` (`Dockerfile.app` line 5).

## Known Bugs

**Out-of-range measurements are clamped silently:**
- Symptoms: `length: 1e6` and `length: Infinity` both return `rings: 8.588161072332964` with status 201, and the same interval [verified]. The outputs are identical, which indicates both values fall into the same edge bin of the tree model [inference]. The API gives no signal that the input is outside what the model was trained on.
- Files: `src/web_service/lib/models.py` (`PositiveFloat` has no upper bound), `src/web_service/lib/inference.py`
- Trigger: any measurement outside the training range. Ranges in the raw CSV [verified]: Length 0.075-0.815, Diameter 0.055-0.650, Height 0-1.130, Whole weight 0.002-2.826, Shucked weight 0.001-1.488, Viscera weight 0.0005-0.760, Shell weight 0.0015-1.005.
- Workaround: validate ranges on the client.

**Impossible part-vs-whole combinations are accepted:**
- Symptoms: `shucked_weight: 5.0` with `whole_weight: 0.514` returns 201 with a prediction [verified].
- Files: `src/web_service/lib/models.py`
- Trigger: any `shucked_weight`, `viscera_weight` or `shell_weight` larger than `whole_weight`.

**The advertised 90% interval is 74% for old abalones, and the API does not say so:**
- Symptoms: `README.md` line 114 reports 74% real coverage above 12 rings. The `/predict` response and `GET /model` (`interval_coverage: 0.9`) present the interval as 90% for every input [doc].
- Files: `src/web_service/main.py` lines 53 and 62-70, `README.md` line 114
- Note: the 74% figure itself has no reproducing code (see Tech Debt).

**Mixed model and interval during a reload (latent):**
- Symptoms: while the flow is writing, a request can load the new `model.pkl` together with the old `interval.json`. The next request sees the newer `interval.json` mtime and reloads both files, so the pair heals itself [code]. The window is the gap between the two writes. Not reproduced.
- Files: `src/web_service/main.py` lines 21-34, `src/modelling/main.py` lines 53-54
- Trigger: a retrain running while requests arrive.

**Request-time 500 during a partial write (latent):**
- Symptoms: `load_object` and `load_json` are not wrapped in error handling. A read during a non-atomic write raises (`EOFError` or `JSONDecodeError`), and that request returns 500 [code].
- Files: `src/web_service/utils.py` lines 6-15, `src/web_service/main.py` lines 30-33
- Also: `_loaded` is a module-level dict that is updated without a lock (`src/web_service/main.py` lines 18 and 30-33). Concurrent requests right after a retrain can each reload the model [code].

**The shell loop waits forever when `PREFECT_API_URL` is empty, or when the Prefect server never starts:**
- Symptoms: the training deployment is never served, and nothing is logged. [verified: with an empty variable the probe raises `ValueError: unknown url type: '/health'`. The `until` loop ends only on success, and stderr is sent to `/dev/null`.]
- Files: `bin/run_services.sh` lines 6-11. The image sets the variable (`Dockerfile.app` line 18), so only local runs of the script are affected by an unset value. A Prefect server that fails to start is not covered by the image setting.

**The weekly retraining reproduces the same model:**
- Symptoms: two training runs on the same data gave identical predictions on this machine [verified: `np.array_equal` returned True]. The committed `model.pkl` reproduces exactly from the current code and CSV, with a maximum difference of 0 [verified]. The weekly job always reads `data/abalone.csv` (`src/modelling/deployment.py` line 5), which the image bakes in (`Dockerfile.app` line 13). Each Sunday run therefore yields the same model and the same RMSE artifact. Floating-point differences across different hardware were not tested.
- Impact: the weekly retraining described in `README.md` lines 57-77 adds no information with the current data. See also Missing Critical Features, "Data refresh".

## Security Considerations

**Unauthenticated API and Prefect server published on all interfaces:**
- Risk: The README run command publishes both ports on `0.0.0.0` (`README.md` line 93). Nothing configures authentication: no auth variable appears in `Dockerfile.app` or `bin/run_services.sh`. The installed Prefect has an opt-in `PREFECT_SERVER_API_AUTH_STRING` setting, which is unset here [verified]. Anyone who can reach the host can read predictions. Through the Prefect REST API they could also start training runs or change the schedule [inference from Prefect's API design; not tested].
- Files: `README.md` line 93, `Dockerfile.app`, `bin/run_services.sh` lines 3 and 15
- Current mitigation: none in code. The README describes local use.
- Recommendations: publish on `127.0.0.1` in the README command. Set `PREFECT_SERVER_API_AUTH_STRING` for the Prefect server. If the API is ever exposed, add an API-key check in FastAPI.

**`pickle` loading of a git-tracked file:**
- Risk: `pickle.load` runs code embedded in the file (`src/web_service/utils.py` line 9). `src/web_service/local_objects/model.pkl` is tracked in git and loaded on every reload. Anyone who can change that file, or write to `src/web_service/local_objects/` inside the container, can run code in the API process.
- Files: `src/web_service/utils.py`, `src/web_service/local_objects/model.pkl`, `src/modelling/utils.py` lines 9-12
- Current mitigation: none. No hash check and no signature.
- Recommendations: serialize the scikit-learn model in a non-executable format (skops), or store a SHA-256 of the artifact and verify it before loading. Review changes to the binary explicitly.

**Container runs as root:**
- Risk: `Dockerfile.app` has no `USER` directive [verified]. The API, the Prefect server and the training all run as root.
- Recommendations: add an unprivileged user, and give it write access only to `/app/src/web_service/local_objects`.

**Unpinned build inputs:**
- Risk: `FROM python:3.11-slim` is a tag, not a digest (`Dockerfile.app` line 1). `pip install uv` has no version (line 5). Python dependencies are pinned and hashed through `uv.lock`, and CI checks them with `uv sync --locked` (`.github/workflows/ci.yaml` line 31). GitHub Actions are pinned to version tags, not commit SHAs (`.github/workflows/ci.yaml` lines 22, 24, 41, 42, 44).
- Recommendations: pin the base image by digest, pin `uv` in the Dockerfile, and pin actions by SHA.

**Positive controls [verified]:** no secrets in tracked files (pattern search). No `.env` file is present, and `.gitignore` excludes `.env`. The CI token is `contents: read` (`.github/workflows/ci.yaml` lines 10-11).

## Performance Bottlenecks

**No material bottleneck found at this scale.**
- Problem: none measured. The repo contains no latency data.
- Files: `src/web_service/main.py` line 25 (two `stat` calls per request), `src/web_service/lib/inference.py` (one single-row DataFrame and one single-row prediction per request).
- Cause: not applicable. The per-request work is small, and the model is loaded only when the files change (`pickle.load` of a 365 KB file).
- Improvement path: none needed now. The reload race under a burst (see Known Bugs) is the only load-related issue found.

## Fragile Areas

**`src/modelling/main.py` as an importable module:**
- Files: `src/modelling/main.py`, `src/modelling/deployment.py`
- Why fragile: it works only when run as a script or from inside `src/modelling/` [verified]. The module names `utils`, `main` and `preprocessing` are generic and could collide with other top-level packages on `sys.path`.
- Safe modification: change one module at a time, and run the flow end to end (`uv run python src/modelling/main.py data/abalone.csv`). Note that this overwrites the committed artifacts in `src/web_service/local_objects/`.
- Test coverage: none for the flow itself.

**Model and interval pairing:**
- Files: `src/web_service/main.py` lines 21-34, `src/modelling/main.py` lines 53-54
- Why fragile: two files are kept in sync by write order and mtime. A crash between the two writes, a reordered write, or a copy of only one file serves a mismatched pair.
- Safe modification: move to a single artifact (see Tech Debt), then update `get_model` and `test_new_model_is_loaded_without_restart` (`tests/test_api.py` lines 78-83).

**Feature order contract:**
- Files: `src/web_service/lib/inference.py` (`build_features`), `src/modelling/preprocessing.py` (`encode_sex`, `extract_x_y`)
- Why fragile: the API must build the same columns, in the same order, as training. scikit-learn checks the feature names. `tests/test_inference.py::test_features_match_the_model` checks the order, and it passes [verified].
- Safe modification: change `encode_sex` and `build_features` together, retrain, and run that test.

**`bin/run_services.sh`:**
- Files: `bin/run_services.sh`, `Dockerfile.app` lines 15-24
- Why fragile: the Prefect server and the deployment run as background jobs with no supervision and no timeout. If the deployment process exits, nothing restarts it. The container then keeps serving the API with no schedule [code]. The readiness loop depends on `PREFECT_API_URL` (see Known Bugs).
- Safe modification: test with `docker run` and check the Prefect deployments API, not only `/api/health` (`.github/workflows/ci.yaml` line 61).
- Test coverage: CI smoke test only.

**Prefect version coupling:**
- Files: `pyproject.toml` lines 14-24, `uv.lock`
- Why fragile: `fastapi<0.155` and `sqlalchemy<2.1` work around upstream Prefect breakage. The comment refers to Prefect 3.9, while `uv.lock` pins `prefect` 3.8.8. Changing Prefect means re-checking both pins.

**scikit-learn version:**
- Files: `pyproject.toml` line 21, `README.md` line 17, `uv.lock`
- Why fragile: `scikit-learn>=1.7.2` has no upper bound, so a `uv lock --upgrade` can move the library past the version the pickle was written with. The lock pins 1.9.1, and the README says the model needs 1.9. The `requires-python = ">=3.11,<3.12"` range already excludes Python 3.10, so the 3.10 scenario described in `README.md` line 17 cannot happen with the current `pyproject.toml`.
- Safe modification: pin the scikit-learn version family the pickle was written with, and record it next to the artifact.

**Line endings:**
- Files: `.gitattributes` (`*.sh text eol=lf` only)
- Why fragile: the working copies are CRLF because the system Git config sets `core.autocrlf=true` [verified]. The shell script is protected by `.gitattributes`. A new script of another type would not be.

## Scaling Limits

**One process in one container:**
- Current capacity: not measured.
- Limit: `bin/run_services.sh` line 15 starts uvicorn without `--workers`, so one process serves all requests. The model is held in memory per process.
- Scaling path: more workers would each keep their own model copy and reload on mtime change, which works. Horizontal scaling needs the artifact on shared storage.

**Training and serving share a filesystem path:**
- Current capacity: not applicable.
- Limit: the flow writes into `src/web_service/local_objects/` (`src/modelling/main.py` lines 18-19), which the API reads. This works only because both run in the same container.
- Scaling path: move the artifacts to a shared volume or an object store, and read them from there.

**Prefect default database:**
- Current capacity: not applicable.
- Limit: the default is SQLite under `PREFECT_HOME` [verified: `.venv/Lib/site-packages/prefect/settings/models/_defaults.py` line 77]. That suits one local server, not shared use.

## Dependencies at Risk

**Prefect (3.8.8 locked):**
- Risk: frequent upstream breakage. Two pins work around it (`fastapi<0.155`, `sqlalchemy<2.1`).
- Impact: the API image imports Prefect at startup, through `src/modelling/preprocessing.py`.
- Migration plan: remove the serving dependency on Prefect (see Tech Debt), then upgrade Prefect separately.

**scikit-learn (1.9.1 locked):**
- Risk: the pickled model requires this version family.
- Impact: an upgrade means retraining and a new artifact. The constraint in `pyproject.toml` does not record this.
- Migration plan: pin the family in `pyproject.toml`, then retrain and commit the artifact in the same change.

**pandas (3.1.0 locked, `pandas>=2.3.3` allows 2.x):**
- Risk: a major version. Tests pass [verified]. No problem found.
- Migration plan: keep the lock.

**httpx2 (dev group only, 2.16.0):**
- Risk: none found. This is not dead code. Starlette 1.9.0's `TestClient` imports `httpx2` first and falls back to `httpx` with a deprecation warning [verified: `.venv/Lib/site-packages/starlette/testclient.py` lines 26-41]. Package metadata names the pydantic project and Tom Christie as the author [verified].
- Migration plan: do not remove it from the dev group.

**Python 3.11 only:**
- Risk: `requires-python = ">=3.11,<3.12"` (`pyproject.toml` line 12) and `python:3.11-slim` (`Dockerfile.app` line 1). Python 3.11 reaches end of life in October 2027 (general knowledge, not checked here).
- Migration plan: a new lock, a new image, and a retrain to confirm the pickle still loads.

## Missing Critical Features

**Quality gate and rollback:**
- Problem: the flow saves the new model unconditionally (`src/modelling/main.py` lines 50-54). The API reloads it on the next request (`src/web_service/main.py` lines 25-33). A worse model, or a bad data change, replaces the current one immediately, and the previous file is overwritten [code].
- Blocks: safe automatic retraining, and any rollback.

**Model provenance:**
- Problem: `model.pkl` and `interval.json` hold no version, data hash, git SHA, library versions or run ID. `PredictionOut` (`src/web_service/lib/models.py` lines 17-22) does not say which model produced a prediction [code].
- Blocks: auditing which model produced a given prediction.

**Data refresh:**
- Problem: the weekly flow reads only the CSV baked into the image (see Known Bugs, "reproduces the same model"). There is no ingestion step and no change detection [code].
- Blocks: retraining on new data without rebuilding the image.

**Durable state:**
- Problem: the retrained `model.pkl` and the Prefect run history live in the container filesystem. `Dockerfile.app` declares no `VOLUME`, and the README run command has no `-v` (`README.md` line 93). The default Prefect database is SQLite under `PREFECT_HOME` (see Scaling Limits). Removing the container, or starting a new one, serves the image's model again and drops the RMSE history, which contradicts `README.md` line 72 ("the history of the retrainings is kept") [code].
- Blocks: keeping retraining results across container restarts.

**Observability:**
- Problem: no application logging in `src/web_service` (no logging calls found [verified]). Only uvicorn's access log exists. There is no prediction logging, no input or output monitoring, no drift check, and no metrics.
- Blocks: detecting data drift or a broken model after deployment.

**Readiness signal:**
- Problem: `GET /` returns a static 200 whether or not a model is loaded (`src/web_service/main.py` lines 37-40). The image has no `HEALTHCHECK` [verified]. The CI smoke test calls `/` and `/predict` once each (`.github/workflows/ci.yaml` lines 53-58).
- Blocks: an orchestrator or load balancer cannot tell a container without a model from a healthy one.

**Authentication and rate limiting:** none. See Security Considerations.

## Test Coverage Gaps

Current status: 20 tests pass in this environment [verified], and `ruff check` passes [verified].

**The flow end to end:**
- What's not tested: `main` in `src/modelling/main.py` (validation, training, artifact writes). No test imports this module.
- Files: `src/modelling/main.py`, `tests/`
- Risk: a broken flow is found only by running it by hand or in a deployment.
- Priority: High

**API cross-field validation:**
- What's not tested: `shucked_weight`, `viscera_weight` or `shell_weight` above `whole_weight` should return 422. It returns 201 [verified]. The training side tests only the shucked case (`tests/test_preprocessing.py` lines 35-40).
- Files: `tests/test_api.py`, `tests/test_preprocessing.py`, `src/web_service/lib/models.py`
- Risk: impossible inputs are served silently.
- Priority: High

**Out-of-range inputs:**
- What's not tested: behavior for values beyond the training range. The output is identical for `1e6` and `Infinity` [verified].
- Files: `tests/test_api.py`, `src/web_service/lib/inference.py`
- Risk: silent extrapolation.
- Priority: Medium

**Artifact consistency and atomicity:**
- What's not tested: a partially written `model.pkl`, a new model paired with an old `interval.json`, and concurrent requests during a reload. `tests/test_api.py` lines 78-83 only changes the mtime of a copied file.
- Files: `tests/test_api.py`, `src/web_service/main.py`
- Priority: Medium

**The artifact writers:**
- What's not tested: `pickle_object` and `save_json` in `src/modelling/utils.py`. No test references them.
- Priority: Medium

**The coverage claim:**
- What's not tested: coverage on data that the calibration did not use. `tests/test_training.py` lines 26-37 checks coverage on the calibration set itself, which holds by construction.
- Files: `tests/test_training.py`, `src/modelling/training.py` (`compute_interval`)
- Priority: Medium

**Remaining validation rules:**
- What's not tested: `Rings >= 1`, `Sex` membership, and the viscera and shell cross-field checks in `validate_data` (`src/modelling/preprocessing.py` lines 9-27).
- Priority: Low

**The deployment and the shell script:**
- What's not tested: `src/modelling/deployment.py` and `bin/run_services.sh`. CI checks only `/`, `/predict` and `/api/health` (`.github/workflows/ci.yaml` lines 53-62).
- Priority: Low to Medium

**`/model` semantics:**
- What's not tested: that `trained_at` means the training time (see Tech Debt).
- Priority: Low

---

*Concerns audit: 2026-10-23*
