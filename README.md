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

`notebooks/eda.ipynb` explores the data and `notebooks/modelling.ipynb` trains a first linear regression. The runs of the modelling notebook are tracked with MLflow. To see them:

```bash
cd notebooks
uv run mlflow ui
```

## Train the model

```bash
uv run python src/modelling/main.py data/abalone.csv
```

This runs the Prefect flow `train-model` and saves the model in `src/web_service/local_objects/model.pkl`.

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

The flow runs can be seen in the UI. To start a training run without waiting for Sunday:

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
