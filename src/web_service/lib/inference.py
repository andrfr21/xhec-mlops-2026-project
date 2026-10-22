import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin

from src.modelling.preprocessing import encode_sex
from src.web_service.lib.models import InputData


def build_features(input_data: InputData) -> pd.DataFrame:
    """Build the model features from the API input, like for the training."""
    df = pd.DataFrame(
        [
            {
                "Sex": input_data.sex,
                "Length": input_data.length,
                "Diameter": input_data.diameter,
                "Height": input_data.height,
                "Whole weight": input_data.whole_weight,
                "Shucked weight": input_data.shucked_weight,
                "Viscera weight": input_data.viscera_weight,
                "Shell weight": input_data.shell_weight,
            }
        ]
    )
    # .fn runs the function without the prefect task machinery
    return encode_sex.fn(df)


def run_inference(input_data: InputData, model: RegressorMixin) -> float:
    """Predict the number of rings of one abalone."""
    return float(model.predict(build_features(input_data))[0])


def prediction_interval(rings: float, log_half_width: float) -> tuple[float, float]:
    """Interval around a prediction, from the conformal half width on the log scale."""
    center = np.log1p(rings)
    return float(np.expm1(center - log_half_width)), float(
        np.expm1(center + log_half_width)
    )
