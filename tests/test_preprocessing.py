import pandas as pd
import pandera.errors
import pytest

from src.modelling.preprocessing import (
    encode_sex,
    extract_x_y,
    split_train_test,
    validate_data,
)


def make_abalones(n: int) -> pd.DataFrame:
    """n valid abalones (first row of the dataset repeated)."""
    return pd.DataFrame(
        {
            "Sex": ["M"] * n,
            "Length": [0.455] * n,
            "Diameter": [0.365] * n,
            "Height": [0.095] * n,
            "Whole weight": [0.514] * n,
            "Shucked weight": [0.2245] * n,
            "Viscera weight": [0.101] * n,
            "Shell weight": [0.15] * n,
            "Rings": [15] * n,
        }
    )


def test_validate_data_keeps_valid_rows():
    df = make_abalones(3)
    assert len(validate_data.fn(df)) == 3


def test_validate_data_drops_impossible_rows():
    df = make_abalones(3)
    df.loc[1, "Height"] = 0
    df.loc[2, "Shucked weight"] = 1.0  # heavier than the whole abalone
    clean = validate_data.fn(df)
    assert clean.index.tolist() == [0]


def test_validate_data_fails_on_missing_column():
    df = make_abalones(3).drop(columns="Height")
    with pytest.raises(pandera.errors.SchemaErrors):
        validate_data.fn(df)


def test_encode_sex():
    df = pd.DataFrame({"Sex": ["M", "F", "I"], "Length": [0.5, 0.4, 0.3]})
    encoded = encode_sex.fn(df)
    assert "Sex" not in encoded.columns
    assert encoded[["Sex_F", "Sex_I", "Sex_M"]].values.tolist() == [
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
    ]


def test_extract_x_y():
    df = pd.DataFrame({"Length": [0.5, 0.4], "Rings": [10, 8]})
    X, y = extract_x_y.fn(df)
    assert list(X.columns) == ["Length"]
    assert y.tolist() == [10, 8]


def test_split_train_test():
    X = pd.DataFrame({"Length": range(10)})
    y = pd.Series(range(10))
    X_train, X_test, y_train, y_test = split_train_test.fn(X, y)
    assert len(X_train) == len(y_train) == 8
    assert len(X_test) == 2
    assert list(X_test.index) == list(y_test.index)
