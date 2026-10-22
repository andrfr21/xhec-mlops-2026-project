import pickle
from typing import Any

from prefect import task


@task
def pickle_object(obj: Any, path: str) -> None:
    """Save an object (model, encoder...) in a pickle file."""
    with open(path, "wb") as f:
        pickle.dump(obj, f)
