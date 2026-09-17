from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

TARGET_COL = "Churn"


def load_data(file_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def split_data(df: pd.DataFrame):
    df = df.copy()

    if TARGET_COL not in df.columns:
        raise ValueError(f"Target column '{TARGET_COL}' not found in dataset.")

    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    return X_train, X_test, y_train, y_test


def save_split_data(X_train, X_test, y_train, y_test, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    X_train.to_csv(output / "X_train.csv", index=False)
    X_test.to_csv(output / "X_test.csv", index=False)
    y_train.to_csv(output / "y_train.csv", index=False)
    y_test.to_csv(output / "y_test.csv", index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    input_path = base_dir / "data" / "processed" / "churn_scaled.csv"
    output_dir = base_dir / "data" / "processed" / "split_data"

    df = load_data(input_path)
    X_train, X_test, y_train, y_test = split_data(df)

    print("X_train shape:", X_train.shape)
    print("X_test shape:", X_test.shape)
    print("y_train shape:", y_train.shape)
    print("y_test shape:", y_test.shape)

    save_split_data(X_train, X_test, y_train, y_test, output_dir)
    print(f"Split data saved to {output_dir}")