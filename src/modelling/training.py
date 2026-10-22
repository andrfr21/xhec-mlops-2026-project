import pandas as pd
from prefect import task
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error


@task
def train_model(X: pd.DataFrame, y: pd.Series) -> LinearRegression:
    """Train a linear regression model."""
    model = LinearRegression()
    model.fit(X, y)
    return model


@task
def evaluate_model(model: LinearRegression, X: pd.DataFrame, y: pd.Series) -> float:
    """Compute the RMSE of the model on the given data."""
    return mean_squared_error(y, model.predict(X)) ** 0.5
