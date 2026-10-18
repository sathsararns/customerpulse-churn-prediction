import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold, cross_validate

from src.outlier_detection import cap_outliers_iqr
from src.preprocessing import CONTINUOUS_COLUMNS, build_pipeline, normalize_features


def test_single_customer_keeps_categorical_information(customers):
    X, y = customers
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    first = X.iloc[[0]].copy()
    changed = first.assign(Contract="Month-to-month", InternetService="DSL")
    original_encoded = pipeline[:-1].transform(first)
    changed_encoded = pipeline[:-1].transform(changed)
    names = pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()
    contract = names.index("categorical__Contract_Month-to-month")
    internet = names.index("categorical__InternetService_DSL")
    assert original_encoded[0, contract] == 0
    assert changed_encoded[0, contract] == 1
    assert original_encoded[0, internet] == 0
    assert changed_encoded[0, internet] == 1
    # Scoring one record uses exactly the same representation as a batch.
    np.testing.assert_allclose(pipeline.predict_proba(first)[0], pipeline.predict_proba(X)[0])


def test_senior_citizen_is_not_capped_or_scaled(customers):
    X, y = customers
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    names = pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()
    senior_column = names.index("binary__SeniorCitizen")
    np.testing.assert_array_equal(pipeline[:-1].transform(X)[:, senior_column], X.SeniorCitizen)
    capped = cap_outliers_iqr(X, columns=["SeniorCitizen", "tenure"])
    pd.testing.assert_series_equal(capped.SeniorCitizen, X.SeniorCitizen)


def test_each_cv_fold_learns_its_own_statistics(customers):
    X, y = customers
    X = X.copy()
    X["PaymentMethod"] = [f"category-{i}" for i in range(len(X))]
    folds = list(KFold(n_splits=2).split(X, y))
    result = cross_validate(build_pipeline(LogisticRegression()), X, y,
                            cv=folds, return_estimator=True)
    for estimator, (train, validation) in zip(result["estimator"], folds):
        processor = estimator.named_steps["preprocessor"]
        expected_medians = normalize_features(X.iloc[train])[CONTINUOUS_COLUMNS].median()
        np.testing.assert_allclose(
            processor.named_transformers_["continuous"]["imputer"].statistics_, expected_medians
        )
        encoder = processor.named_transformers_["categorical"]["encoder"]
        learned_categories = set(encoder.categories_[-1])
        assert learned_categories == set(X.iloc[train].PaymentMethod)
        assert learned_categories.isdisjoint(X.iloc[validation].PaymentMethod)


def test_inference_reuses_training_bounds_and_scaler(customers):
    X, y = customers
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    numeric = pipeline.named_steps["preprocessor"].named_transformers_["continuous"]
    bounds = numeric["outliers"].upper_bounds_.copy()
    mean = numeric["scaler"].mean_.copy()
    extreme = X.iloc[[0]].assign(MonthlyCharges=1e9, TotalCharges=" ")
    assert np.isfinite(pipeline.predict_proba(extreme)).all()
    np.testing.assert_array_equal(numeric["outliers"].upper_bounds_, bounds)
    np.testing.assert_array_equal(numeric["scaler"].mean_, mean)


def test_unseen_category_does_not_change_feature_shape(customers):
    X, y = customers
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    unknown = X.iloc[[0]].assign(PaymentMethod="New payment method")
    assert pipeline[:-1].transform(unknown).shape[1] == pipeline[:-1].transform(X).shape[1]
    assert np.isfinite(pipeline.predict_proba(unknown)).all()


def test_missing_required_column_is_not_silently_filled(customers):
    X, y = customers
    pipeline = build_pipeline(LogisticRegression()).fit(X, y)
    with pytest.raises(ValueError, match="Missing customer features: Contract"):
        pipeline.predict(X.drop(columns="Contract"))
