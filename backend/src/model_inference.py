from pathlib import Path
import sys
import json
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))


def load_artifacts(base_dir: Path):
    metrics_path = base_dir / "reports" / "model_metrics.json"
    scaler_path = base_dir / "artifacts" / "scaler.pkl"
    train_x_path = base_dir / "data" / "processed" / "split_data" / "X_train.csv"

    if not metrics_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_path}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
    if not train_x_path.exists():
        raise FileNotFoundError(f"Training data file not found: {train_x_path}")

    with open(metrics_path, "r", encoding="utf-8") as f:
        report_info = json.load(f)

    best_model_name = report_info["best_model"]
    model_path = base_dir / "models" / f"{best_model_name}.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    train_columns = pd.read_csv(train_x_path, nrows=1).columns.tolist()

    return model, scaler, train_columns, best_model_name


def preprocess_input(raw_input: dict, train_columns: list, scaler):
    df = pd.DataFrame([raw_input])

    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    # One-hot encode raw categorical columns
    df = pd.get_dummies(df, drop_first=True)

    # Match the exact columns seen during training
    df = df.reindex(columns=train_columns, fill_value=0)

    # Scale using the saved scaler
    scaled_array = scaler.transform(df)
    scaled_df = pd.DataFrame(scaled_array, columns=train_columns)

    return scaled_df


def predict_single(model, scaler, train_columns, input_data: dict):
    df = preprocess_input(input_data, train_columns, scaler)

    prediction = model.predict(df)[0]
    probability = model.predict_proba(df)[0][1]

    return {
        "prediction": "Churn" if prediction == 1 else "Not Churn",
        "probability": round(float(probability), 4),
    }


if __name__ == "__main__":
    model, scaler, train_columns, model_name = load_artifacts(BASE_DIR)
    print(f"Loaded model: {model_name}")

    # Use RAW customer fields, not encoded dummy fields
    sample_customer = {
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 12,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "No",
        "DeviceProtection": "Yes",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 70.35,
        "TotalCharges": 845.2,
    }

    result = predict_single(model, scaler, train_columns, sample_customer)
    print("Prediction Result:")
    print(result)