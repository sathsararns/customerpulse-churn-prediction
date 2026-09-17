from pathlib import Path
import pandas as pd

TARGET_COL = "Churn"


def load_data(file_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Convert TotalCharges to numeric
    if "TotalCharges" in df.columns:
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

    # Drop customerID because it's just an identifier
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    # Fill numeric missing values with median
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    # Fill categorical missing values with mode
    categorical_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in categorical_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0])

    return df


def save_clean_data(df: pd.DataFrame, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    raw_path = base_dir / "data" / "raw" / "churn.csv"
    clean_path = base_dir / "data" / "processed" / "churn_clean.csv"

    df = load_data(raw_path)
    print("Before cleaning:")
    print(df.isnull().sum())

    clean_df = handle_missing_values(df)

    print("\nAfter cleaning:")
    print(clean_df.isnull().sum())

    save_clean_data(clean_df, clean_path)
    print(f"\nClean data saved to {clean_path}")