"""Versioned Kafka envelopes reuse the API's raw customer validation."""

from datetime import datetime
import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas import CustomerInput
from src.prediction_store import get_risk_level


class CustomerEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    event_id: UUID
    customer_id: Annotated[str | None, Field(min_length=1, max_length=128, pattern=r"^\S(?:.*\S)?$")]
    occurred_at: datetime
    features: CustomerInput

    @model_validator(mode="after")
    def check_metadata(self):
        if self.features.customer_id is not None:
            raise ValueError("customer_id belongs in the envelope, outside model features")
        if self.customer_id is not None and self.customer_id != self.customer_id.strip():
            raise ValueError("customer_id must not have surrounding whitespace")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return self

    def feature_values(self):
        return self.features.model_dump(exclude={"customer_id"})

    def fingerprint(self):
        # Delivery/replay timestamps do not change the identity of customer input.
        raw = json.dumps({"customer_id": self.customer_id, "features": self.feature_values()},
                         sort_keys=True, allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()


class PredictionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    event_id: UUID
    customer_id: Annotated[str | None, Field(min_length=1, max_length=128, pattern=r"^\S(?:.*\S)?$")]
    occurred_at: datetime
    predicted_at: datetime
    model: Annotated[str, Field(min_length=1)]
    model_version: Annotated[str, Field(min_length=1)]
    prediction_threshold: Annotated[float, Field(gt=0, lt=1)]
    prediction: Literal["Churn", "Not Churn"]
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    risk_level: Literal["Low", "Medium", "High"]
    source: Literal["stream"] = "stream"
    customer_payload: CustomerInput

    @model_validator(mode="after")
    def check_result(self):
        if self.customer_payload.customer_id is not None:
            raise ValueError("Customer identifiers must remain outside model features")
        if self.risk_level != get_risk_level(self.probability):
            raise ValueError("risk_level does not match probability")
        if self.occurred_at.tzinfo is None or self.predicted_at.tzinfo is None:
            raise ValueError("Event timestamps must include a timezone")
        return self
