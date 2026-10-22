from pathlib import Path

from fastapi import FastAPI

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
model = load_object(MODEL_PATH)
interval = load_json(INTERVAL_PATH)


@app.get("/")
def home() -> dict:
    """Health check of the API."""
    return {"health_check": "App up and running!"}


@app.post("/predict", response_model=PredictionOut, status_code=201)
def predict(payload: InputData) -> dict:
    """Predict the number of rings, the age (rings + 1.5) and a 90% interval."""
    rings = run_inference(payload, model)
    rings_low, rings_high = prediction_interval(rings, interval["log_half_width"])
    return {
        "rings": rings,
        "age": rings + 1.5,
        "rings_low": rings_low,
        "rings_high": rings_high,
    }
