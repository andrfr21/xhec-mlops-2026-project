import pytest
from fastapi.testclient import TestClient

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


def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_predict():
    response = client.post("/predict", json=ABALONE)
    assert response.status_code == 201
    result = response.json()
    assert result["rings"] > 0
    assert result["age"] == pytest.approx(result["rings"] + 1.5)


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
