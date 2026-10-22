import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from src.modelling.training import evaluate_model, train_model


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
