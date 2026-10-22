import pickle
from typing import Any


def load_object(path: str) -> Any:
    """Load an object (model, encoder...) from a pickle file."""
    with open(path, "rb") as f:
        return pickle.load(f)
