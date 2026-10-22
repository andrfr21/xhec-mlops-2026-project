import pandas as pd
from sklearn.linear_model import LinearRegression

from src.web_service.lib.models import InputData

SEX_CATEGORIES = ["F", "I", "M"]


def run_inference(input_data: InputData, model: LinearRegression) -> float:
    """Predict the number of rings of one abalone."""
    df = pd.DataFrame(
        [
            {
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
    # same encoding as in src/modelling/preprocessing.py
    for sex in SEX_CATEGORIES:
        df[f"Sex_{sex}"] = int(input_data.sex == sex)
    return float(model.predict(df)[0])
