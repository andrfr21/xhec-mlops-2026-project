# This module is the training flow: it reads the data, preprocesses it, trains a model and saves it.

import argparse
from pathlib import Path

from prefect import flow, get_run_logger
from preprocessing import (
    encode_sex,
    extract_x_y,
    load_data,
    split_train_test,
    validate_data,
)
from training import evaluate_model, train_model
from utils import pickle_object

MODEL_PATH = Path(__file__).parents[1] / "web_service" / "local_objects" / "model.pkl"


@flow(name="train-model")
def main(trainset_path: Path) -> float:
    """Train a model on the data at the given path, evaluate it and save it (pickle)."""
    logger = get_run_logger()

    # Read and validate data
    raw_df = load_data(trainset_path)
    df = validate_data(raw_df)
    logger.info(f"{len(raw_df) - len(df)} invalid rows dropped")

    # Preprocess data
    df = encode_sex(df)
    X, y = extract_x_y(df)
    X_train, X_test, y_train, y_test = split_train_test(X, y)

    # Train and evaluate the model
    model = train_model(X_train, y_train)
    rmse = evaluate_model(model, X_test, y_test)
    logger.info(f"RMSE on the test set: {rmse:.2f}")

    # Pickle model
    pickle_object(model, MODEL_PATH)
    return rmse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a model using the data at the given path."
    )
    parser.add_argument("trainset_path", type=str, help="Path to the training set")
    args = parser.parse_args()
    main(args.trainset_path)
