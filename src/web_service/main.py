from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.web_service.lib.inference import prediction_interval, run_inference
from src.web_service.lib.models import InputData, PredictionOut
from src.web_service.utils import load_json, load_object

LOCAL_OBJECTS = Path(__file__).parent / "local_objects"
MODEL_PATH = LOCAL_OBJECTS / "model.pkl"
INTERVAL_PATH = LOCAL_OBJECTS / "interval.json"

app = FastAPI(
    title="Abalone age prediction",
    description="Predict the age of an abalone from its physical measurements.",
)
_loaded: dict = {}


def get_model() -> dict:
    """Load the model and its interval, and load them again if the training flow
    saved new ones (so the weekly retraining is used without restarting the API)."""
    try:
        trained_at = max(MODEL_PATH.stat().st_mtime, INTERVAL_PATH.stat().st_mtime)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="No trained model, run the training flow first"
        )
    if _loaded.get("trained_at") != trained_at:
        _loaded["model"] = load_object(MODEL_PATH)
        _loaded["interval"] = load_json(INTERVAL_PATH)
        _loaded["trained_at"] = trained_at
    return _loaded


@app.get("/")
def home() -> dict:
    """Health check of the API."""
    return {"health_check": "App up and running!"}


@app.get("/model")
def model_info() -> dict:
    """Information about the model that is used for the predictions."""
    loaded = get_model()
    trained_at = datetime.fromtimestamp(loaded["trained_at"], tz=timezone.utc)
    # the model is wrapped in a TransformedTargetRegressor (log target)
    model = getattr(loaded["model"], "regressor", loaded["model"])
    return {
        "model": type(model).__name__,
        "trained_at": trained_at.isoformat(),
        "interval_coverage": loaded["interval"]["coverage"],
    }


@app.post("/predict", response_model=PredictionOut, status_code=201)
def predict(payload: InputData) -> dict:
    """Predict the number of rings, the age (rings + 1.5) and a 90% interval."""
    loaded = get_model()
    rings = run_inference(payload, loaded["model"])
    rings_low, rings_high = prediction_interval(
        rings, loaded["interval"]["log_half_width"]
    )
    return {
        "rings": rings,
        "age": rings + 1.5,
        "rings_low": rings_low,
        "rings_high": rings_high,
    }
