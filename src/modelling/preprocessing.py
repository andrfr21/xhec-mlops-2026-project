import pandas as pd
from prefect import task

SEX_CATEGORIES = ["F", "I", "M"]


@task
def load_data(path: str) -> pd.DataFrame:
    """Read the abalone csv file."""
    return pd.read_csv(path)


@task
def encode_sex(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode the Sex column (same columns as pd.get_dummies in the notebook)."""
    df = df.copy()
    for sex in SEX_CATEGORIES:
        df[f"Sex_{sex}"] = (df["Sex"] == sex).astype(int)
    return df.drop(columns="Sex")


@task
def extract_x_y(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split the dataframe into features and target."""
    return df.drop(columns="Rings"), df["Rings"]
