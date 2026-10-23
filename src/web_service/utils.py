import json
import pickle
from pathlib import Path
from typing import Any


def load_object(path: str | Path) -> Any:
    """Load an object (model, encoder...) from a pickle file."""
    with open(path, "rb") as f:
        return pickle.load(f)


def load_json(path: str | Path) -> dict:
    """Load a json file."""
    with open(path) as f:
        return json.load(f)
