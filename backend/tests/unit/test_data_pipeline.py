from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from pipelines.data_pipeline import run_data_pipeline
from src.data_validation import validate_and_normalize
from utils.artifact_manager import get_artifact_manager, sha256_file
from utils.config import load_config


def test_data_snapshot_is_reproducible_and_has_no_imputation(customers, tmp_path):
    X, y = customers
    source = tmp_path / "customers.csv"
    X.assign(Churn=y.map({0: "No", 1: "Yes"})).to_csv(source, index=False)
    settings = replace(load_config(base_dir=tmp_path), test_size=0.25, random_state=7)
    first = run_data_pipeline(source, settings=settings)
    second = run_data_pipeline(source, settings=settings)
    assert first.metadata["dataset_version"] == second.metadata["dataset_version"]
    assert first.metadata["dataset_sha256"] == sha256_file(source)
    pd.testing.assert_frame_equal(first.X_train, second.X_train)
    assert len(first.X_test) == 10
    assert first.X_train.TotalCharges.isna().sum() + first.X_test.TotalCharges.isna().sum() == 4
    assert set(first.X_train.SeniorCitizen) == {0, 1}
    assert set(first.X_train.index).isdisjoint(first.X_test.index)
    altered = run_data_pipeline(source, settings=replace(settings, random_state=8))
    assert altered.metadata["dataset_version"] != first.metadata["dataset_version"]
    manager = get_artifact_manager(settings)
    loaded = manager.load_dataset(first.metadata["dataset_version"])
    assert len(loaded[0]) == len(first.X_train)
    pd.testing.assert_frame_equal(first.X_train.reset_index(drop=True), loaded[0])


@pytest.mark.parametrize("column,value,error", [
    ("Churn", None, "Churn labels must be non-missing"),
    ("Churn", "Maybe", "Churn labels must be non-missing"),
    ("SeniorCitizen", 2, "SeniorCitizen must be 0 or 1"),
    ("tenure", 1.5, "whole numbers"),
    ("MonthlyCharges", -2, "non-negative"),
    ("TotalCharges", "invalid", "invalid numeric"),
    ("TotalCharges", np.inf, "invalid numeric"),
    ("Contract", "Unsupported", "unsupported categorical"),
])
def test_invalid_training_data_is_rejected(customers, column, value, error):
    X, y = customers
    raw = X.assign(Churn=y.map({0: "No", 1: "Yes"})).astype(object)
    raw.loc[0, column] = value
    with pytest.raises(ValueError, match=error):
        validate_and_normalize(raw)


def test_schema_and_duplicate_identifiers_are_checked(customers):
    X, y = customers
    raw = X.assign(Churn=y.map({0: "No", 1: "Yes"}), customerID="duplicate")
    with pytest.raises(ValueError, match="Duplicate customerID"):
        validate_and_normalize(raw)
    with pytest.raises(ValueError, match="Missing required columns: Contract"):
        validate_and_normalize(raw.drop(columns="Contract"))


def test_modified_split_is_rejected_on_reload(customers, tmp_path):
    X, y = customers
    source = tmp_path / "customers.csv"
    X.assign(Churn=y.map({0: "No", 1: "Yes"})).to_csv(source, index=False)
    settings = load_config(base_dir=tmp_path)
    prepared = run_data_pipeline(source, settings=settings)
    manager = get_artifact_manager(settings)
    directory = manager.root / "datasets" / prepared.metadata["dataset_version"]
    path = directory / "X_train.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="checksum mismatch: X_train.csv"):
        manager.load_dataset(prepared.metadata["dataset_version"])


def test_yaml_settings_and_validation(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("data:\n  path: customers.csv\n  test_size: 0.3\n  random_state: 9\ntraining:\n  cv_folds: 3\n  prediction_threshold: 0.65\n")
    settings = load_config(path, tmp_path)
    assert settings.data_path == tmp_path / "customers.csv"
    assert settings.random_state == 9
    assert settings.prediction_threshold == 0.65
    with pytest.raises(ValueError, match="prediction_threshold"):
        replace(settings, prediction_threshold=1.0)
    with pytest.raises(ValueError, match="inside the output directory"):
        replace(settings, artifacts_dir="../escape")
