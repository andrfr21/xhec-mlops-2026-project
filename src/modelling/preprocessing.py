import pandas as pd
import pandera.pandas as pa
from prefect import task
from sklearn.model_selection import train_test_split

SEX_CATEGORIES = ["F", "I", "M"]

# same rules as the API input (src/web_service/lib/models.py): sizes and weights > 0
ABALONE_SCHEMA = pa.DataFrameSchema(
    {
        "Sex": pa.Column(str, pa.Check.isin(SEX_CATEGORIES)),
        "Length": pa.Column(float, pa.Check.gt(0)),
        "Diameter": pa.Column(float, pa.Check.gt(0)),
        "Height": pa.Column(float, pa.Check.gt(0)),
        "Whole weight": pa.Column(float, pa.Check.gt(0)),
        "Shucked weight": pa.Column(float, pa.Check.gt(0)),
        "Viscera weight": pa.Column(float, pa.Check.gt(0)),
        "Shell weight": pa.Column(float, pa.Check.gt(0)),
        "Rings": pa.Column(int, pa.Check.ge(1)),
    },
    # a part of the abalone cannot be heavier than the whole abalone
    checks=[
        pa.Check(lambda df: df["Shucked weight"] <= df["Whole weight"]),
        pa.Check(lambda df: df["Viscera weight"] <= df["Whole weight"]),
        pa.Check(lambda df: df["Shell weight"] <= df["Whole weight"]),
    ],
    drop_invalid_rows=True,
)


@task
def load_data(path: str) -> pd.DataFrame:
    """Read the abalone csv file."""
    return pd.read_csv(path)


@task
def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Check the columns and types of the data and drop the impossible rows."""
    return ABALONE_SCHEMA.validate(df, lazy=True)


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
