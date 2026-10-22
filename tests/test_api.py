import os
import shutil

import pytest
from fastapi.testclient import TestClient

from src.web_service import main
from src.web_service.main import app

client = TestClient(app)

ABALONE = {
    "sex": "M",
    "length": 0.455,
    "diameter": 0.365,
    "height": 0.095,
    "whole_weight": 0.514,
    "shucked_weight": 0.2245,
    "viscera_weight": 0.101,
    "shell_weight": 0.15,
}


@pytest.fixture
def model_copy(tmp_path, monkeypatch):
    """Use a copy of the model files, so a test can change or delete them."""
    for path in [main.MODEL_PATH, main.INTERVAL_PATH]:
        shutil.copy(path, tmp_path / path.name)
    monkeypatch.setattr(main, "MODEL_PATH", tmp_path / main.MODEL_PATH.name)
    monkeypatch.setattr(main, "INTERVAL_PATH", tmp_path / main.INTERVAL_PATH.name)
    monkeypatch.setattr(main, "_loaded", {})
    return tmp_path


def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_model_info():
    response = client.get("/model")
    assert response.status_code == 200
    assert response.json()["model"] == "HistGradientBoostingRegressor"


def test_predict():
    response = client.post("/predict", json=ABALONE)
    assert response.status_code == 201
    result = response.json()
    assert result["rings"] > 0
    assert result["age"] == pytest.approx(result["rings"] + 1.5)
    assert result["rings_low"] < result["rings"] < result["rings_high"]


def test_predict_wrong_sex():
    response = client.post("/predict", json={**ABALONE, "sex": "X"})
    assert response.status_code == 422


def test_predict_missing_field():
    data = {key: value for key, value in ABALONE.items() if key != "shell_weight"}
    response = client.post("/predict", json=data)
    assert response.status_code == 422


@pytest.mark.parametrize("value", [0, -0.1])
def test_predict_measurement_not_positive(value):
    response = client.post("/predict", json={**ABALONE, "height": value})
    assert response.status_code == 422


def test_predict_without_model(model_copy):
    (model_copy / "model.pkl").unlink()
    response = client.post("/predict", json=ABALONE)
    assert response.status_code == 503


def test_new_model_is_loaded_without_restart(model_copy):
    first = client.get("/model").json()["trained_at"]
    # same as a new training: the model file is written again later
    stat = os.stat(model_copy / "model.pkl")
    os.utime(model_copy / "model.pkl", (stat.st_atime, stat.st_mtime + 3600))
    assert client.get("/model").json()["trained_at"] != first
