from pathlib import Path

from fastapi import FastAPI

from src.web_service.lib.inference import run_inference
from src.web_service.lib.models import InputData, PredictionOut
from src.web_service.utils import load_object

MODEL_PATH = Path(__file__).parent / "local_objects" / "model.pkl"

app = FastAPI(
    title="Abalone age prediction",
    description="Predict the age of an abalone from its physical measurements.",
)
model = load_object(MODEL_PATH)


@app.get("/")
def home() -> dict:
    """Health check of the API."""
    return {"health_check": "App up and running!"}


@app.post("/predict", response_model=PredictionOut, status_code=201)
def predict(payload: InputData) -> dict:
    """Predict the number of rings and the age (rings + 1.5) of an abalone."""
    rings = run_inference(payload, model)
    return {"rings": rings, "age": rings + 1.5}
