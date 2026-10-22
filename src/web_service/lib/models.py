from typing import Literal

from pydantic import BaseModel, PositiveFloat


class InputData(BaseModel):
    sex: Literal["M", "F", "I"]
    length: PositiveFloat
    diameter: PositiveFloat
    height: PositiveFloat
    whole_weight: PositiveFloat
    shucked_weight: PositiveFloat
    viscera_weight: PositiveFloat
    shell_weight: PositiveFloat


class PredictionOut(BaseModel):
    rings: float
    age: float
    # 90% prediction interval for the number of rings
    rings_low: float
    rings_high: float
