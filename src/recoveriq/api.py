from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from recoveriq import __version__
from recoveriq.config import ARTIFACT_DIR
from recoveriq.modeling import ModelBundle, load_bundle, local_contributions

app = FastAPI(
    title="RecoverIQ Delivery Risk API",
    version=__version__,
    description="Approval-time late-delivery risk. Historical case study; not a customer promise.",
)


class PredictionRequest(BaseModel):
    price: Annotated[float, Field(ge=0, le=1_000_000)]
    freight_value: Annotated[float, Field(ge=0, le=1_000_000)]
    item_count: Annotated[int, Field(ge=1, le=100)]
    seller_count: Annotated[int, Field(ge=1, le=100)] = 1
    estimated_delivery_days: Annotated[float, Field(gt=0, le=180)]
    customer_seller_distance_km: Annotated[float | None, Field(ge=0, le=20_000)] = None
    seller_prior_orders: Annotated[int, Field(ge=0)] = 0
    seller_prior_late_rate: Annotated[float, Field(ge=0, le=1)] = 0.0
    purchase_hour: Annotated[int, Field(ge=0, le=23)]
    purchase_day_of_week: Annotated[int, Field(ge=0, le=6)]
    purchase_month: Annotated[int, Field(ge=1, le=12)]
    customer_state: Annotated[str, Field(min_length=2, max_length=20)]
    seller_state: Annotated[str, Field(min_length=2, max_length=20)]
    product_category_name_english: Annotated[str, Field(min_length=1, max_length=100)]


class Contribution(BaseModel):
    feature: str
    contribution: float


class PredictionResponse(BaseModel):
    late_delivery_probability: float
    risk_band: str
    decision_threshold: float
    model_version: str
    leading_feature_contributions: list[Contribution]


@lru_cache(maxsize=1)
def get_bundle() -> ModelBundle:
    path = ARTIFACT_DIR / "model.joblib"
    if not path.exists():
        raise FileNotFoundError("Model artifact is missing. Run `make train` first.")
    return load_bundle(path)


def _risk_band(probability: float, threshold: float) -> str:
    if probability >= max(0.65, threshold * 1.5):
        return "high"
    if probability >= threshold:
        return "medium"
    return "low"


@app.get("/health")
def health() -> dict[str, Any]:
    path = ARTIFACT_DIR / "model.joblib"
    return {"status": "ok" if path.exists() else "degraded", "model_loaded": path.exists(), "version": __version__}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    try:
        bundle = get_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "model_name": bundle.model_name,
        "model_version": bundle.model_version,
        "decision_threshold": bundle.threshold,
        "feature_columns": bundle.feature_columns,
        "global_drivers": bundle.global_drivers,
        "deployment_recommendation": bundle.deployment_recommendation,
        "intended_use": "Order-approval risk prioritization and experiment planning",
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        bundle = get_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    frame = pd.DataFrame([request.model_dump()])
    probability = float(bundle.predict_proba(frame)[0])
    return PredictionResponse(
        late_delivery_probability=probability,
        risk_band=_risk_band(probability, bundle.threshold),
        decision_threshold=bundle.threshold,
        model_version=bundle.model_version,
        leading_feature_contributions=local_contributions(bundle, frame),
    )
