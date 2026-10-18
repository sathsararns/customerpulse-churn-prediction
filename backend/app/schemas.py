"""Validated request and response contracts for raw telecom customers."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

YesNo = Literal["Yes", "No"]
InternetOption = Literal["Yes", "No", "No internet service"]


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: Annotated[str | None, Field(min_length=1, max_length=128, pattern=r"^\S(?:.*\S)?$")] = None
    gender: Literal["Female", "Male"]
    SeniorCitizen: Annotated[int, Field(strict=True, ge=0, le=1)]
    Partner: YesNo
    Dependents: YesNo
    tenure: Annotated[int, Field(strict=True, ge=0, le=100)]
    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: InternetOption
    OnlineBackup: InternetOption
    DeviceProtection: InternetOption
    TechSupport: InternetOption
    StreamingTV: InternetOption
    StreamingMovies: InternetOption
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal[
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    ]
    MonthlyCharges: Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)]
    TotalCharges: Annotated[float | None, Field(ge=0, le=50000, allow_inf_nan=False)]

    @model_validator(mode="after")
    def validate_services(self):
        if (self.PhoneService == "No") != (self.MultipleLines == "No phone service"):
            raise ValueError("MultipleLines must match the phone service selection")
        for name in ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                     "TechSupport", "StreamingTV", "StreamingMovies"]:
            if (self.InternetService == "No") != (getattr(self, name) == "No internet service"):
                raise ValueError(f"{name} must match the internet service selection")
        return self


class PredictionResponse(BaseModel):
    event_id: UUID
    customer_id: str | None
    source: Literal["api"] = "api"
    model: str
    model_version: str
    prediction: Literal["Churn", "Not Churn"]
    probability: Annotated[float, Field(ge=0, le=1)]
    risk_level: Literal["Low", "Medium", "High"]
