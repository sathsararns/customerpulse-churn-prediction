from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from src.model_inference import load_artifacts, predict_single


def run_inference_pipeline():
    model, scaler, train_columns, model_name = load_artifacts(BASE_DIR)
    print(f"Loaded model: {model_name}")

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


if __name__ == "__main__":
    run_inference_pipeline()