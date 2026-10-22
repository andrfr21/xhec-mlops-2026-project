import pandas as pd
from sklearn.linear_model import LinearRegression


def train_model(X: pd.DataFrame, y: pd.Series) -> LinearRegression:
    """Train a linear regression model."""
    model = LinearRegression()
    model.fit(X, y)
    return model
