from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from src.data_ingestion import ingest_data, save_raw_copy
from src.handle_missing_values import handle_missing_values, save_clean_data
from src.outlier_detection import detect_outliers_iqr, cap_outliers_iqr, save_data
from src.feature_encoding import encode_features, save_encoded_data
from src.feature_scaling import scale_features, save_scaled_data
from src.data_splitter import split_data, save_split_data
from src.model_training import train_and_select_best_model, save_artifacts


def run_training_pipeline():
    raw_path = BASE_DIR / "data" / "raw" / "churn.csv"
    raw_copy_path = BASE_DIR / "artifacts" / "raw_churn_copy.csv"
    clean_path = BASE_DIR / "data" / "processed" / "churn_clean.csv"
    outlier_path = BASE_DIR / "data" / "processed" / "churn_outliers_capped.csv"
    encoded_path = BASE_DIR / "data" / "processed" / "churn_encoded.csv"
    scaled_path = BASE_DIR / "data" / "processed" / "churn_scaled.csv"
    split_dir = BASE_DIR / "data" / "processed" / "split_data"

    print("\n=== Step 1: Data Ingestion ===")
    df = ingest_data(raw_path)
    print("Loaded data shape:", df.shape)
    save_raw_copy(df, raw_copy_path)
    print(f"Raw copy saved to {raw_copy_path}")

    print("\n=== Step 2: Handle Missing Values ===")
    clean_df = handle_missing_values(df)
    save_clean_data(clean_df, clean_path)
    print(f"Clean data saved to {clean_path}")

    print("\n=== Step 3: Outlier Detection / Capping ===")
    summary = detect_outliers_iqr(clean_df)
    for col, info in summary.items():
        print(f"{col}: {info['count']} outliers")
    capped_df = cap_outliers_iqr(clean_df)
    save_data(capped_df, outlier_path)
    print(f"Outlier-capped data saved to {outlier_path}")

    print("\n=== Step 4: Feature Encoding ===")
    encoded_df = encode_features(capped_df)
    save_encoded_data(encoded_df, encoded_path)
    print(f"Encoded data saved to {encoded_path}")

    print("\n=== Step 5: Feature Scaling ===")
    scaled_df, scaler = scale_features(encoded_df)
    save_scaled_data(scaled_df, scaled_path)
    print(f"Scaled data saved to {scaled_path}")

    print("\n=== Step 6: Data Split ===")
    X_train, X_test, y_train, y_test = split_data(scaled_df)
    save_split_data(X_train, X_test, y_train, y_test, split_dir)
    print(f"Split data saved to {split_dir}")

    print("\n=== Step 7: Model Training ===")
    best_model_name, best_model, best_metrics = train_and_select_best_model(
        X_train, y_train, X_test, y_test
    )

    print(f"\nBest model selected: {best_model_name}")
    print("Best metrics:", best_metrics)

    save_artifacts(BASE_DIR, best_model, best_model_name, best_metrics)
    print("\n=== Pipeline completed successfully ===")


if __name__ == "__main__":
    run_training_pipeline()