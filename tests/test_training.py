import pandas as pd
import pytest

from src.modelling.training import evaluate_model, train_model


def test_train_and_evaluate():
    # y = 20 * Length, so a linear regression should be perfect
    X = pd.DataFrame({"Length": [0.1, 0.2, 0.3, 0.4]})
    y = pd.Series([2.0, 4.0, 6.0, 8.0])
    model = train_model.fn(X, y)
    assert evaluate_model.fn(model, X, y) == pytest.approx(0)
