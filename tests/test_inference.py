from src.web_service.lib.inference import build_features
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
