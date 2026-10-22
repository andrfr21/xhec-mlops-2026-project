# This module is the training flow: it reads the data, preprocesses it, trains a model and saves it.

import argparse
from pathlib import Path

from preprocessing import encode_sex, extract_x_y, load_data
from training import train_model
from utils import pickle_object

MODEL_PATH = Path(__file__).parents[1] / "web_service" / "local_objects" / "model.pkl"


def main(trainset_path: Path) -> None:
    """Train a model using the data at the given path and save the model (pickle)."""
    # Read data
    df = load_data(trainset_path)

    # Preprocess data
    df = encode_sex(df)
    X, y = extract_x_y(df)

    # Train model
    model = train_model(X, y)

    # Pickle model
    pickle_object(model, MODEL_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a model using the data at the given path."
    )
    parser.add_argument("trainset_path", type=str, help="Path to the training set")
    args = parser.parse_args()
    main(args.trainset_path)
