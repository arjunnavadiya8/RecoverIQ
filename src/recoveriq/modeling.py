from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from recoveriq.config import (
    ARTIFACT_DIR,
    CATEGORICAL_FEATURES,
    DB_PATH,
    FEATURE_COLUMNS,
    MODEL_VERSION,
    NUMERIC_FEATURES,
    RANDOM_STATE,
    REPORT_DIR,
    ROOT,
)


@dataclass
class ModelBundle:
    pipeline: Pipeline
    calibrator: IsotonicRegression
    threshold: float
    model_name: str
    model_version: str
    feature_columns: list[str]
    global_drivers: list[dict[str, Any]]
    deployment_recommendation: str

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        raw = self.pipeline.predict_proba(frame[self.feature_columns])[:, 1]
        return np.clip(self.calibrator.predict(raw), 0.0, 1.0)


def make_preprocessor(sparse_output: bool = True) -> ColumnTransformer:
    numeric = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore", min_frequency=2, sparse_output=sparse_output
                ),
            ),
        ]
    )
    return ColumnTransformer(
        [("num", numeric, NUMERIC_FEATURES), ("cat", categorical, CATEGORICAL_FEATURES)]
    )


def load_model_frame(db_path: Path = DB_PATH) -> pd.DataFrame:
    query = """
      select f.*, o.late_delivery, o.low_review, o.repeat_purchase_90d,
             o.repeat_observed_90d
      from analytics.order_features f
      join analytics.order_outcomes o using (order_id)
      join analytics.fact_orders fo using (order_id)
      where fo.order_status = 'delivered'
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        frame = con.execute(query).df()
    frame["order_purchase_timestamp"] = pd.to_datetime(frame["order_purchase_timestamp"])
    return frame.sort_values(["order_purchase_timestamp", "order_id"]).reset_index(drop=True)


def chronological_split(frame: pd.DataFrame) -> pd.Series:
    n = len(frame)
    if n < 100:
        raise ValueError("At least 100 delivered orders are required for chronological validation.")
    split = np.full(n, "test", dtype=object)
    split[: int(n * 0.70)] = "train"
    split[int(n * 0.70) : int(n * 0.85)] = "validation"
    return pd.Series(split, index=frame.index, name="split")


def _safe_auc(metric, y: pd.Series, probability: np.ndarray) -> float:
    return float(metric(y, probability)) if y.nunique() > 1 else float("nan")


def _best_threshold(y: pd.Series, probability: np.ndarray, fn_cost: float = 5.0) -> float:
    candidates = np.linspace(0.02, 0.80, 158)
    costs = []
    for threshold in candidates:
        pred = probability >= threshold
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        costs.append((fn * fn_cost + fp) / len(y))
    return float(candidates[int(np.argmin(costs))])


def classification_metrics(
    y: pd.Series, probability: np.ndarray, threshold: float
) -> dict[str, float]:
    pred = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    top_n = max(1, int(len(y) * 0.10))
    top_idx = np.argsort(probability)[-top_n:]
    positives = max(1, int(y.sum()))
    return {
        "pr_auc": _safe_auc(average_precision_score, y, probability),
        "roc_auc": _safe_auc(roc_auc_score, y, probability),
        "brier": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, np.clip(probability, 1e-6, 1 - 1e-6), labels=[0, 1])),
        "recall_at_top_10pct": float(y.iloc[top_idx].sum() / positives),
        "threshold": threshold,
        "expected_cost_per_order": float((5 * fn + fp) / len(y)),
        "precision": float(tp / max(1, tp + fp)),
        "recall": float(tp / max(1, tp + fn)),
        "positive_rate": float(y.mean()),
    }


def _rule_probability(frame: pd.DataFrame) -> np.ndarray:
    slack = pd.to_numeric(frame["estimated_delivery_days"], errors="coerce").fillna(15)
    distance = pd.to_numeric(frame["customer_seller_distance_km"], errors="coerce").fillna(500)
    history = pd.to_numeric(frame["seller_prior_late_rate"], errors="coerce").fillna(0)
    score = 0.45 * history + 0.30 * (1 / (1 + np.exp((slack - 12) / 3))) + 0.25 * np.clip(
        distance / 2500, 0, 1
    )
    return np.asarray(np.clip(score, 0, 1))


def _global_drivers(pipeline: Pipeline, model_name: str) -> list[dict[str, Any]]:
    preprocessor = pipeline.named_steps["preprocess"]
    names = preprocessor.get_feature_names_out()
    model = pipeline.named_steps["model"]
    if model_name == "lightgbm":
        values = model.feature_importances_.astype(float)
    else:
        values = np.abs(model.coef_[0]).astype(float)
    order = np.argsort(values)[::-1][:15]
    return [
        {"feature": str(names[i]).replace("num__", "").replace("cat__", ""), "importance": float(values[i])}
        for i in order
    ]


def local_contributions(bundle: ModelBundle, frame: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    transformed = bundle.pipeline.named_steps["preprocess"].transform(frame[bundle.feature_columns])
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    names = bundle.pipeline.named_steps["preprocess"].get_feature_names_out()
    model = bundle.pipeline.named_steps["model"]
    if bundle.model_name == "lightgbm":
        contributions = model.predict(transformed, pred_contrib=True)[0][:-1]
    else:
        contributions = np.asarray(transformed)[0] * model.coef_[0]
    order = np.argsort(np.abs(contributions))[::-1][:limit]
    return [
        {
            "feature": str(names[i]).replace("num__", "").replace("cat__", ""),
            "contribution": float(contributions[i]),
        }
        for i in order
    ]


def train_models(db_path: Path = DB_PATH, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    frame = load_model_frame(db_path)
    frame["split"] = chronological_split(frame)
    train = frame[frame.split == "train"]
    validation = frame[frame.split == "validation"]
    test = frame[frame.split == "test"]
    y_train, y_val, y_test = train.late_delivery, validation.late_delivery, test.late_delivery

    candidates = {
        "logistic_regression": LogisticRegression(
            C=0.5, class_weight="balanced", max_iter=1500, random_state=RANDOM_STATE
        ),
        "lightgbm": LGBMClassifier(
            n_estimators=300,
            learning_rate=0.035,
            num_leaves=24,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=2,
            verbosity=-1,
        ),
    }
    validation_metrics: dict[str, dict[str, float]] = {}
    fitted: dict[str, tuple[Pipeline, IsotonicRegression, float]] = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline([("preprocess", make_preprocessor()), ("model", estimator)])
        pipeline.fit(train[FEATURE_COLUMNS], y_train)
        raw_validation = pipeline.predict_proba(validation[FEATURE_COLUMNS])[:, 1]
        calibrator = IsotonicRegression(out_of_bounds="clip").fit(raw_validation, y_val)
        calibrated = calibrator.predict(raw_validation)
        threshold = _best_threshold(y_val, calibrated)
        validation_metrics[name] = classification_metrics(y_val, calibrated, threshold)
        fitted[name] = (pipeline, calibrator, threshold)

    constant = np.repeat(float(y_train.mean()), len(validation))
    rule = _rule_probability(validation)
    validation_metrics["constant"] = classification_metrics(y_val, constant, 0.5)
    rule_threshold = _best_threshold(y_val, rule)
    validation_metrics["rule"] = classification_metrics(y_val, rule, rule_threshold)

    winner = min(
        candidates,
        key=lambda name: validation_metrics[name]["expected_cost_per_order"],
    )
    pipeline, calibrator, threshold = fitted[winner]
    drivers = _global_drivers(pipeline, winner)
    bundle = ModelBundle(
        pipeline=pipeline,
        calibrator=calibrator,
        threshold=threshold,
        model_name=winner,
        model_version=MODEL_VERSION,
        feature_columns=FEATURE_COLUMNS,
        global_drivers=drivers,
        deployment_recommendation="pending final holdout evaluation",
    )

    # The test period is evaluated only after model choice and threshold are frozen.
    test_probability = bundle.predict_proba(test)
    test_metrics = classification_metrics(y_test, test_probability, threshold)
    rule_test = _rule_probability(test)
    test_rule_metrics = classification_metrics(y_test, rule_test, rule_threshold)
    deployment_recommendation = (
        "use calibrated model for prioritization"
        if test_metrics["expected_cost_per_order"] < test_rule_metrics["expected_cost_per_order"]
        else "retain simple rule; keep ML in shadow mode"
    )
    bundle.deployment_recommendation = deployment_recommendation

    artifact_dir.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, artifact_dir / "model.joblib")
    prediction_frames = []
    for split_name, subset in frame.groupby("split", sort=False):
        probability = bundle.predict_proba(subset)
        prediction_frames.append(
            pd.DataFrame(
                {
                    "order_id": subset.order_id,
                    "order_purchase_timestamp": subset.order_purchase_timestamp,
                    "split": split_name,
                    "actual_late": subset.late_delivery,
                    "late_probability": probability,
                }
            )
        )
    pd.concat(prediction_frames).to_csv(artifact_dir / "predictions.csv", index=False)
    pd.DataFrame(drivers).to_csv(artifact_dir / "feature_importance.csv", index=False)

    manifest_path = ROOT / "data" / "raw" / "manifest.json"
    data_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    results = {
        "created_at": datetime.now(UTC).isoformat(),
        "model_version": MODEL_VERSION,
        "selected_model": winner,
        "selection_rule": "minimum validation expected cost; false negative cost = 5x false positive",
        "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "periods": {
            name: {
                "start": str(group.order_purchase_timestamp.min()),
                "end": str(group.order_purchase_timestamp.max()),
            }
            for name, group in frame.groupby("split")
        },
        "validation": validation_metrics,
        "test": {"selected_model": test_metrics, "rule": test_rule_metrics},
        "deployment_recommendation": deployment_recommendation,
        "data_source": data_manifest.get("source", "unknown"),
    }
    (artifact_dir / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    _write_model_card(results, drivers)

    import mlflow

    tracking_db = (ROOT / "mlflow.db").as_posix()
    mlflow.set_tracking_uri(f"sqlite:///{tracking_db}")
    mlflow.set_experiment("recoveriq-delivery-risk")
    with mlflow.start_run(run_name=f"{winner}-{MODEL_VERSION}"):
        mlflow.log_params({"selected_model": winner, "threshold": threshold, "random_state": RANDOM_STATE})
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items() if np.isfinite(v)})
        mlflow.log_artifact(str(artifact_dir / "metrics.json"))
        mlflow.log_artifact(str(artifact_dir / "feature_importance.csv"))
    return results


def _write_model_card(results: dict[str, Any], drivers: list[dict[str, Any]]) -> None:
    test = results["test"]["selected_model"]
    source_warning = (
        "**DEMO DATA ONLY — these metrics must not be used in portfolio claims.**"
        if results["data_source"] == "synthetic_demo"
        else "Results use the historical, anonymized Olist dataset."
    )
    text = f"""# Delivery-risk model card

{source_warning}

## Intended use

Estimate late-delivery risk at order approval for prioritization and experiment planning. It is not a promise to customers and must not trigger an offer without a randomized evaluation.

## Model and evaluation

- Version: `{results['model_version']}`
- Selected model: `{results['selected_model']}`
- Chronological test PR-AUC: `{test['pr_auc']:.3f}`
- Chronological test Brier score: `{test['brier']:.3f}`
- Recall among highest-risk 10%: `{test['recall_at_top_10pct']:.3f}`
- Decision threshold: `{test['threshold']:.3f}`
- Decision recommendation: **{results['deployment_recommendation']}**

## Leading global drivers

{chr(10).join(f"- {d['feature']}: {d['importance']:.3f}" for d in drivers[:8])}

## Limitations

The data covers a historical Brazilian marketplace. Geography, operations, promised-date policy and customer behavior may not generalize. Labels arrive after delivery, subgroup metrics can be noisy, and the model does not estimate coupon response. Monitor input drift, calibration and delayed outcomes before any real use.
"""
    (REPORT_DIR / "model_card.md").write_text(text, encoding="utf-8")


def load_bundle(path: Path | None = None) -> ModelBundle:
    return joblib.load(path or ARTIFACT_DIR / "model.joblib")
