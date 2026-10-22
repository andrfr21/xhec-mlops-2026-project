import pandas as pd

from src.modelling.preprocessing import encode_sex, extract_x_y


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
