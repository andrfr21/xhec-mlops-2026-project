# Abalone age prediction

X-HEC MLOps project. The goal is to predict the age of an abalone from physical measurements (sizes and weights) instead of counting the rings of its shell under a microscope. The age is the number of rings + 1.5.

The repo contains:

- the EDA and a first model in `notebooks/`
- the training code in `src/modelling/`, orchestrated with Prefect (with a weekly retraining)
- a FastAPI app in `src/web_service/` to make predictions, which runs in Docker

## Team

- Francois Andreani ([andrfr21](https://github.com/andrfr21))

## Setup

You need Python 3.11, [uv](https://docs.astral.sh/uv/getting-started/installation/) and Docker (for the API part). Python 3.10 is not supported: the model is saved with scikit-learn 1.9, which needs Python 3.11, and a pickled model should be loaded with the same scikit-learn version (with 3.10, uv installs scikit-learn 1.7 and it warns that the results could be wrong).

```bash
uv sync
uv run pre-commit install
```

The dataset is already in `data/abalone.csv` (it comes from [Kaggle](https://www.kaggle.com/datasets/rodolfomendes/abalone-dataset)).

## Notebooks

`notebooks/eda.ipynb` explores the data and `notebooks/modelling.ipynb` compares the models. The runs of the modelling notebook are tracked with MLflow. To see them:

```bash
cd notebooks
uv run mlflow ui
```

The libraries used only by the notebooks (mlflow, matplotlib, seaborn) are dev dependencies: `uv sync` installs them, but they are not in the Docker image.

## Train the model

```bash
uv run python -m src.modelling.main data/abalone.csv
```

This runs the Prefect flow `train-model`: it validates the data with a [Pandera](https://pandera.readthedocs.io) schema (6 impossible rows are dropped: height of 0, or a part heavier than the whole abalone), keeps 20% of the data as a test set, trains the model on the rest, logs the RMSE on the test set (around 2.2 rings) and saves the model in `src/web_service/local_objects/model.pkl`.

### Model choice

The models were compared in `notebooks/modelling.ipynb` with a 5-fold cross-validation repeated 5 times (a single 836-row test set is too noisy to see a difference of a few %):

| Model | RMSE (rings) | MAE (rings) |
|---|---|---|
| Linear regression | 2.21 | 1.58 |
| Random forest | 2.16 | 1.52 |
| Gradient boosting on log(1 + rings) | **2.15** | **1.49** |

Gradient boosting (scikit-learn `HistGradientBoostingRegressor`) is the model used by the training flow. The gain over the linear regression (-3% RMSE, -6% MAE) is in line with the TALENT benchmark for abalone (2.24 for linear regression, 2.16 to 2.18 for tuned tree models).

## Prefect

Start the Prefect server (the UI is on http://localhost:4200):

```bash
uv run prefect server start
```

In another terminal, start the deployment that retrains the model every Sunday at midnight (`PREFECT_API_URL` tells it to use this server):

```bash
export PREFECT_API_URL=http://localhost:4200/api
uv run python -m src.modelling.deployment
```

The flow runs can be seen in the UI. Each run also saves its test RMSE in the artifact `model-rmse` (Artifacts tab), so the history of the retrainings is kept. To start a training run without waiting for Sunday, in a third terminal:

```bash
export PREFECT_API_URL=http://localhost:4200/api
uv run prefect deployment run "train-model/weekly-training"
```

On Windows PowerShell, replace the `export` line with `$env:PREFECT_API_URL = "http://localhost:4200/api"`. The variable only exists in the terminal where it is set, so the training script of the previous section still works without a server in a new terminal (`prefect config set` would change it for every terminal).

## API

Run it locally:

```bash
uv run uvicorn src.web_service.main:app --port 8000
```

Or with Docker. The container runs the API, a Prefect server and the weekly training deployment, so the retraining also happens in the container:

```bash
docker build -t abalone-api -f Dockerfile.app .
docker run --init -p 0.0.0.0:8000:8001 -p 0.0.0.0:4200:4201 abalone-api
```

In both cases the API is on http://localhost:8000 (docs on http://localhost:8000/docs). With Docker, the Prefect UI is on http://localhost:4200. The `weekly-training` deployment can also be started by hand from the UI (Run > Quick run): the API uses the new model as soon as the training is done (`GET /model` shows the training time).

The local API and the local Prefect server of the [Prefect](#prefect) section use the same ports (8000 and 4200), so stop them before `docker run`. `--init` lets `docker stop` stop all the processes of the container cleanly.

The image is built in two stages with uv (the final image only has the virtualenv, no pip or uv), runs as a non-root user and has a healthcheck on the API (`docker ps` shows `healthy`). The design and the measurements are in `docs/superpowers/specs/2026-10-23-dockerfile-design.md`.

Example of prediction:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sex": "M", "length": 0.455, "diameter": 0.365, "height": 0.095, "whole_weight": 0.514, "shucked_weight": 0.2245, "viscera_weight": 0.101, "shell_weight": 0.15}'
```

It returns the predicted number of rings, the age (`rings + 1.5`) and a 90% prediction interval for the rings:

```json
{"rings": 9.23, "age": 10.73, "rings_low": 6.73, "rings_high": 12.56}
```

The interval comes from split conformal prediction ([Angelopoulos & Bates, arXiv:2107.07511](https://arxiv.org/abs/2107.07511)): the training flow takes the 90% quantile of the errors of the model on the test set (on the log(1 + rings) scale, so the interval is wider for old abalones) and saves it in `src/web_service/local_objects/interval.json`. Over 10 random splits, the real coverage was 90% overall, but 95% for abalones with less than 12 rings and only 74% for the older ones (the model underestimates the oldest abalones). So the interval is reliable on average, not for every age.

`GET /model` tells which model is used and when it was trained. The API checks the model files at each request and loads them again when a new training has saved them, so a retraining is used without restarting the API. If there is no model yet, `/predict` answers 503.

## Tests

```bash
uv run pytest
```

The tests (in `tests/`) check the preprocessing and the API. They also run in the CI with pre-commit. pre-commit also checks the type hints with [mypy](https://mypy-lang.org) (`uv run mypy src tests`).

## References

- Dataset: [Abalone on Kaggle](https://www.kaggle.com/datasets/rodolfomendes/abalone-dataset), originally from the [UCI repository](https://archive.ics.uci.edu/dataset/1/abalone)
- Ye et al., *A Closer Look at Deep Learning Methods on Tabular Datasets* (TALENT benchmark), [arXiv:2407.00956](https://arxiv.org/abs/2407.00956), [results on abalone](https://github.com/LAMDA-Tabular/TALENT/blob/main/results/regression.md)
- [Pandera](https://pandera.readthedocs.io) for the data validation
- Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, [arXiv:2107.07511](https://arxiv.org/abs/2107.07511), for the prediction interval
