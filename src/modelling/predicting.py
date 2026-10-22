import numpy as np
import pandas as pd
from prefect import task
from sklearn.linear_model import LinearRegression


@task
def predict(model: LinearRegression, X: pd.DataFrame) -> np.ndarray:
    """Predict the number of rings."""
    return model.predict(X)
