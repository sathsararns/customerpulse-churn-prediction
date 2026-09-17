from pathlib import Path
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

TARGET_COL = "Churn"


def load_data(file_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def scale_features(df: pd.DataFrame):
    df = df.copy()

    if TARGET_COL in df.columns:
        target = df[TARGET_COL]
        features = df.drop(columns=[TARGET_COL])
    else:
        target = None
        features = df

    numeric_cols = features.select_dtypes(include=["int64", "float64", "bool"]).columns.tolist()

    scaler = StandardScaler()
    features[numeric_cols] = scaler.fit_transform(features[numeric_cols])

    if target is not None:
        features[TARGET_COL] = target.values

    return features, scaler


def save_scaled_data(df: pd.DataFrame, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    input_path = base_dir / "data" / "processed" / "churn_encoded.csv"
    output_path = base_dir / "data" / "processed" / "churn_scaled.csv"
    scaler_path = base_dir / "artifacts" / "scaler.pkl"

    df = load_data(input_path)
    scaled_df, scaler = scale_features(df)

    print(scaled_df.head())
    print(scaled_df.shape)

    save_scaled_data(scaled_df, output_path)
    joblib.dump(scaler, scaler_path)

    print(f"Scaled data saved to {output_path}")
    print(f"Scaler saved to {scaler_path}")