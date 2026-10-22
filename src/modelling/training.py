import numpy as np
import pandas as pd
from prefect import task
from sklearn.base import RegressorMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_squared_error


@task
def train_model(X: pd.DataFrame, y: pd.Series) -> TransformedTargetRegressor:
    """Train a gradient boosting model on log(1 + rings).

    The model and its hyperparameters were chosen with a repeated cross-validation
    in notebooks/modelling.ipynb.
    """
    model = TransformedTargetRegressor(
        regressor=HistGradientBoostingRegressor(
            learning_rate=0.05, max_iter=200, max_leaf_nodes=15, random_state=42
        ),
        func=np.log1p,
        inverse_func=np.expm1,
    )
    model.fit(X, y)
    return model


@task
def evaluate_model(model: RegressorMixin, X: pd.DataFrame, y: pd.Series) -> float:
    """Compute the RMSE of the model on the given data."""
    return mean_squared_error(y, model.predict(X)) ** 0.5
