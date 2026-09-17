from pathlib import Path
import pandas as pd

NUMERIC_COLS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]


def load_data(file_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def detect_outliers_iqr(df: pd.DataFrame, columns=None):
    """
    Detect outliers using IQR method.
    """
    if columns is None:
        columns = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

    summary = {}

    for col in columns:
        if col not in df.columns:
            continue

        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]

        summary[col] = {
            "count": len(outliers),
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }

    return summary


def cap_outliers_iqr(df: pd.DataFrame, columns=None) -> pd.DataFrame:
    """
    Cap outliers using IQR boundaries.
    """
    df = df.copy()

    if columns is None:
        columns = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

    for col in columns:
        if col not in df.columns:
            continue

        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    return df


def save_data(df: pd.DataFrame, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    input_path = base_dir / "data" / "processed" / "churn_clean.csv"
    output_path = base_dir / "data" / "processed" / "churn_outliers_capped.csv"

    df = load_data(input_path)

    summary = detect_outliers_iqr(df, NUMERIC_COLS)
    print("Outlier Summary:")
    for col, info in summary.items():
        print(f"{col}: {info['count']} outliers | bounds=({info['lower_bound']:.2f}, {info['upper_bound']:.2f})")

    capped_df = cap_outliers_iqr(df, NUMERIC_COLS)
    save_data(capped_df, output_path)

    print(f"Outlier-capped data saved to {output_path}")