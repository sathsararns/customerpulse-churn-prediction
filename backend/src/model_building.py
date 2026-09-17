from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier


def build_models():
    """
    Return a dictionary of candidate models.
    """
    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
    }
    return models


def get_model(model_name: str):
    """
    Return a single model by name.
    """
    models = build_models()

    if model_name not in models:
        raise ValueError(
            f"Model '{model_name}' not found. Available models: {list(models.keys())}"
        )

    return models[model_name]


if __name__ == "__main__":
    models = build_models()
    print("Available models:")
    for name in models:
        print("-", name)