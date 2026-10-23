import json
import pickle
from pathlib import Path
from typing import Any

from prefect import task


@task
def pickle_object(obj: Any, path: str | Path) -> None:
    """Save an object (model, encoder...) in a pickle file."""
    with open(path, "wb") as f:
        pickle.dump(obj, f)


@task
def save_json(data: dict, path: str | Path) -> None:
    """Save a dict in a json file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
