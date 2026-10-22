# Abalone age prediction

X-HEC MLOps project. The goal is to predict the age of an abalone from physical measurements (sizes and weights) instead of counting the rings of its shell under a microscope. The age is the number of rings + 1.5.

The repo contains:

- the EDA and a first model in `notebooks/`
- the training code in `src/modelling/`, orchestrated with Prefect (with a weekly retraining)
- a FastAPI app in `src/web_service/` to make predictions, which runs in Docker

## Team

- Francois Andreani ([andrfr21](https://github.com/andrfr21))

## Setup

You need Python 3.10 or 3.11, [uv](https://docs.astral.sh/uv/getting-started/installation/) and Docker (for the API part).

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
uv run python src/modelling/main.py data/abalone.csv
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

In another terminal, start the deployment that retrains the model every Sunday at midnight:

```bash
uv run prefect config set PREFECT_API_URL=http://localhost:4200/api
uv run python src/modelling/deployment.py
```

The flow runs can be seen in the UI. Each run also saves its test RMSE in the artifact `model-rmse` (Artifacts tab), so the history of the retrainings is kept. To start a training run without waiting for Sunday:

```bash
uv run prefect deployment run "train-model/weekly-training"
```

## API

Run it locally:

```bash
uv run uvicorn src.web_service.main:app --port 8001
```

Or with Docker (the container runs the API and a Prefect server):

```bash
docker build -t abalone-api -f Dockerfile.app .
docker run -p 0.0.0.0:8000:8001 -p 0.0.0.0:4200:4201 abalone-api
```

With Docker, the API is on http://localhost:8000 (docs on http://localhost:8000/docs) and the Prefect UI on http://localhost:4200.

Example of prediction:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sex": "M", "length": 0.455, "diameter": 0.365, "height": 0.095, "whole_weight": 0.514, "shucked_weight": 0.2245, "viscera_weight": 0.101, "shell_weight": 0.15}'
```

It returns the predicted number of rings and the age (`rings + 1.5`).

## Tests

```bash
uv run pytest
```

The tests (in `tests/`) check the preprocessing and the API. They also run in the CI with pre-commit.

## References

- Dataset: [Abalone on Kaggle](https://www.kaggle.com/datasets/rodolfomendes/abalone-dataset), originally from the [UCI repository](https://archive.ics.uci.edu/dataset/1/abalone)
- Ye et al., *A Closer Look at Deep Learning Methods on Tabular Datasets* (TALENT benchmark), [arXiv:2407.00956](https://arxiv.org/abs/2407.00956), [results on abalone](https://github.com/LAMDA-Tabular/TALENT/blob/main/results/regression.md)
- [Pandera](https://pandera.readthedocs.io) for the data validation
