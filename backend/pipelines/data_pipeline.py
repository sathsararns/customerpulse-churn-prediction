"""Validate and normalize customer data, then save reproducible raw feature splits."""

import argparse
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data_validation import validate_and_normalize
from utils.artifact_manager import get_artifact_manager, sha256_bytes, utc_now
from utils.config import load_config


@dataclass
class PreparedData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    metadata: dict


def load_prepared_data(version, settings):
    return PreparedData(*get_artifact_manager(settings).load_dataset(version))


def run_data_pipeline(data_path=None, output_dir=None, config_path=None, *, settings=None):
    settings = settings or load_config(config_path, output_dir)
    path = Path(data_path).resolve() if data_path else settings.data_path
    content = path.read_bytes()
    features, target = validate_and_normalize(pd.read_csv(BytesIO(content)))
    if target.value_counts().min() < 2:
        raise ValueError("Each churn class needs at least two records for a stratified split")
    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=settings.test_size,
        random_state=settings.random_state, stratify=target,
    )
    normalized = features.assign(Churn=target).to_csv(index=False).encode()
    split_spec = {"normalization_version": 1, "test_size": settings.test_size,
                  "random_state": settings.random_state,
                  "normalized_sha256": sha256_bytes(normalized)}
    dataset_sha256 = sha256_bytes(content)
    version = "data-" + dataset_sha256[:12] + "-" + sha256_bytes(
        json.dumps(split_spec, sort_keys=True).encode()
    )[:12]
    files = {"source.csv": content, "normalized.csv": normalized}
    files.update({name: frame.to_csv(index=False).encode() for name, frame in [
        ("X_train.csv", X_train), ("X_test.csv", X_test),
        ("y_train.csv", y_train), ("y_test.csv", y_test),
    ]})
    metadata = get_artifact_manager(settings).save_dataset(version, files, {
        **split_spec, "dataset_sha256": dataset_sha256, "source_path": str(path),
        "created_at": utc_now(), "training_rows": len(X_train),
        "test_rows": len(X_test), "dataset_size": len(features),
        "target_mapping": {"No": 0, "Yes": 1},
    })
    print(f"Dataset {version}: {len(X_train)} training / {len(X_test)} test records", flush=True)
    return PreparedData(X_train, X_test, y_train, y_test, metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", dest="config_path", type=Path)
    result = run_data_pipeline(**vars(parser.parse_args()))
    print(json.dumps(result.metadata, indent=2))


if __name__ == "__main__":
    main()
