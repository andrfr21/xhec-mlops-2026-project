import pandas as pd
from prefect import task
from sklearn.model_selection import train_test_split

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


@task
def split_train_test(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> list:
    """Split the data into a train set and a test set (same split as the notebook)."""
    return train_test_split(X, y, test_size=test_size, random_state=42)
