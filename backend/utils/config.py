"""Load and validate shared pipeline settings from YAML and environment."""

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AcceptancePolicy:
    min_f1: float = 0.60
    min_recall: float = 0.55
    min_precision: float = 0.63
    min_roc_auc: float = 0.83
    max_f1_drop: float = 0.005
    max_recall_drop: float = 0.01
    require_same_dataset: bool = True

    def __post_init__(self):
        import math
        for name, value in asdict(self).items():
            if name == "require_same_dataset":
                if type(value) is not bool:
                    raise ValueError("acceptance.require_same_dataset must be a boolean")
            elif not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"acceptance.{name} must be finite and between 0 and 1")


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_path: Path
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    prediction_threshold: float = 0.5
    storage_backend: str = "local"
    artifacts_dir: str = "artifacts"
    experiment_name: str = "CustomerPulse-AI"
    tracking_uri: str | None = None
    artifact_root: str | None = None
    acceptance: AcceptancePolicy = field(default_factory=AcceptancePolicy)

    def __post_init__(self):
        if not 0 < self.test_size < 1:
            raise ValueError("data.test_size must be between 0 and 1")
        if not 0 < self.prediction_threshold < 1:
            raise ValueError("training.prediction_threshold must be between 0 and 1")
        if self.cv_folds < 2:
            raise ValueError("training.cv_folds must be at least 2")
        artifact_path = (self.base_dir / self.artifacts_dir).resolve()
        if not artifact_path.is_relative_to(self.base_dir.resolve()):
            raise ValueError("storage.artifacts_dir must stay inside the output directory")

    def snapshot(self):
        return {key: str(value) if isinstance(value, Path) else value
                for key, value in asdict(self).items()}


def load_config(config_path=None, base_dir=None):
    path = Path(config_path).resolve() if config_path else BACKEND_DIR / "config.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data = document.get("data", {})
    training = document.get("training", {})
    storage = document.get("storage", {})
    tracking = document.get("mlflow", {})
    return Settings(
        base_dir=Path(base_dir).resolve() if base_dir else BACKEND_DIR,
        data_path=(path.parent / data.get("path", "data/raw/churn.csv")).resolve(),
        test_size=float(data.get("test_size", 0.2)),
        random_state=int(data.get("random_state", 42)),
        cv_folds=int(training.get("cv_folds", 5)),
        prediction_threshold=float(training.get("prediction_threshold", 0.5)),
        storage_backend=storage.get("backend", "local"),
        artifacts_dir=storage.get("artifacts_dir", "artifacts"),
        experiment_name=tracking.get("experiment_name", "CustomerPulse-AI"),
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI") or tracking.get("tracking_uri"),
        artifact_root=os.getenv("MLFLOW_ARTIFACT_ROOT") or tracking.get("artifact_root"),
        acceptance=AcceptancePolicy(**document.get("acceptance", {})),
    )
