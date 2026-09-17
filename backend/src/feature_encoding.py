from pathlib import Path
import pandas as pd

TARGET_COL = "Churn"


def load_data(file_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Drop ID column
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    # Convert target to binary
    if TARGET_COL in df.columns:
        df[TARGET_COL] = df[TARGET_COL].map({"Yes": 1, "No": 0})

    # One-hot encode all categorical columns except target
    categorical_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    categorical_cols = [col for col in categorical_cols if col != TARGET_COL]

    if categorical_cols:
        df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    return df


def save_encoded_data(df: pd.DataFrame, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    input_path = base_dir / "data" / "processed" / "churn_outliers_capped.csv"
    output_path = base_dir / "data" / "processed" / "churn_encoded.csv"

    df = load_data(input_path)
    encoded_df = encode_features(df)

    print(encoded_df.head())
    print(encoded_df.shape)

    save_encoded_data(encoded_df, output_path)
    print(f"Encoded data saved to {output_path}")