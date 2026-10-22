from src.web_service.lib.inference import build_features, prediction_interval
from src.web_service.lib.models import InputData
from src.web_service.main import MODEL_PATH
from src.web_service.utils import load_object


def test_features_match_the_model():
    abalone = InputData(
        sex="F",
        length=0.5,
        diameter=0.4,
        height=0.1,
        whole_weight=0.6,
        shucked_weight=0.3,
        viscera_weight=0.1,
        shell_weight=0.2,
    )
    model = load_object(MODEL_PATH)
    features = build_features(abalone)
    assert list(features.columns) == list(model.feature_names_in_)
    assert features[["Sex_F", "Sex_I", "Sex_M"]].values.tolist() == [[1, 0, 0]]


def test_prediction_interval_is_wider_for_old_abalones():
    young_low, young_high = prediction_interval(5, log_half_width=0.3)
    old_low, old_high = prediction_interval(15, log_half_width=0.3)
    assert young_low < 5 < young_high
    assert old_low < 15 < old_high
    assert old_high - old_low > young_high - young_low
