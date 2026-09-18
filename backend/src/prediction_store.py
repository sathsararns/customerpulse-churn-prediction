import json
from typing import Any, Dict, List

from src.db import get_connection, init_db


def save_prediction(
    model_name: str,
    prediction: str,
    probability: float,
    risk_level: str,
    customer_payload: Dict[str, Any],
) -> None:
    """
    Save one prediction record to SQLite.
    """
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO predictions (model_name, prediction, probability, risk_level, customer_payload)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            model_name,
            prediction,
            float(probability),
            risk_level,
            json.dumps(customer_payload),
        ),
    )

    conn.commit()
    conn.close()


def get_recent_predictions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Return recent prediction records from SQLite.
    """
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, created_at, model_name, prediction, probability, risk_level, customer_payload
        FROM predictions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "model_name": row["model_name"],
                "prediction": row["prediction"],
                "probability": row["probability"],
                "risk_level": row["risk_level"],
                "customer_payload": json.loads(row["customer_payload"]),
            }
        )

    return results