from pathlib import Path
import pandas as pd


def ingest_data(file_path: str | Path) -> pd.DataFrame:
    """
    Load the raw churn dataset from CSV.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.resolve()}")

    return pd.read_csv(path)


def save_raw_copy(df: pd.DataFrame, output_path: str | Path) -> None:
    """
    Save a copy of the raw dataset into artifacts.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    raw_path = base_dir / "data" / "raw" / "churn.csv"
    artifact_path = base_dir / "artifacts" / "raw_churn_copy.csv"

    df = ingest_data(raw_path)
    print("Data loaded successfully")
    print("Shape:", df.shape)
    print(df.head())

    save_raw_copy(df, artifact_path)
    print(f"Raw copy saved to {artifact_path}")