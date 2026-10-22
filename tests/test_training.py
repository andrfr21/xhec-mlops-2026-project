import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from src.modelling.training import compute_interval, evaluate_model, train_model


def test_evaluate_model():
    # y = 20 * Length, so a linear regression is perfect and the RMSE is 0
    X = pd.DataFrame({"Length": [0.1, 0.2, 0.3, 0.4]})
    y = pd.Series([2.0, 4.0, 6.0, 8.0])
    model = LinearRegression().fit(X, y)
    assert evaluate_model.fn(model, X, y) == pytest.approx(0)


def test_train_model_learns_a_simple_relation():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"Length": rng.uniform(0.1, 0.8, 500)})
    y = pd.Series(np.round(3 + 20 * X["Length"]))
    model = train_model.fn(X, y)
    assert evaluate_model.fn(model, X, y) < 1
    assert (model.predict(X) > 0).all()


def test_compute_interval_covers_the_calibration_set():
    rng = np.random.default_rng(1)
    X = pd.DataFrame({"Length": rng.uniform(0.1, 0.8, 1000)})
    y = pd.Series(3 + 20 * X["Length"] + rng.normal(0, 1, 1000))
    model = LinearRegression().fit(X[:500], y[:500])
    X_cal, y_cal = X[500:], y[500:]

    q = compute_interval.fn(model, X_cal, y_cal, coverage=0.9)
    pred = np.log1p(model.predict(X_cal))
    low, high = np.expm1(pred - q), np.expm1(pred + q)
    assert q > 0
    assert ((y_cal >= low) & (y_cal <= high)).mean() >= 0.9
