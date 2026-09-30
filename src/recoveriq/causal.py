from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from recoveriq.config import ARTIFACT_DIR, FEATURE_COLUMNS, RANDOM_STATE, REPORT_DIR
from recoveriq.modeling import load_model_frame, make_preprocessor


def _standardized_differences(x: pd.DataFrame, treatment: np.ndarray, weights=None) -> pd.DataFrame:
    numeric = x.select_dtypes(include="number").copy()
    rows = []
    if weights is None:
        weights = np.ones(len(x))
    for column in numeric.columns:
        values = numeric[column].fillna(numeric[column].median()).to_numpy(float)
        treated, control = treatment == 1, treatment == 0
        mt = np.average(values[treated], weights=weights[treated])
        mc = np.average(values[control], weights=weights[control])
        vt = np.average((values[treated] - mt) ** 2, weights=weights[treated])
        vc = np.average((values[control] - mc) ** 2, weights=weights[control])
        rows.append({"feature": column, "standardized_difference": (mt - mc) / np.sqrt((vt + vc) / 2 + 1e-9)})
    return pd.DataFrame(rows)


def aipw_effect(
    frame: pd.DataFrame,
    outcome: str,
    bootstrap: int = 500,
    placebo: bool = False,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    x = frame[FEATURE_COLUMNS]
    treatment = frame.late_delivery.to_numpy(int).copy()
    y = frame[outcome].to_numpy(float)
    if placebo:
        treatment = np.random.default_rng(RANDOM_STATE).permutation(treatment)

    n = len(frame)
    propensity, mu1, mu0 = np.zeros(n), np.zeros(n), np.zeros(n)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    for train_idx, test_idx in folds.split(x, treatment):
        propensity_model = Pipeline(
            [
                ("preprocess", make_preprocessor()),
                ("model", LogisticRegression(max_iter=1200, random_state=RANDOM_STATE)),
            ]
        )
        outcome_template = Pipeline(
            [
                ("preprocess", make_preprocessor()),
                ("model", LogisticRegression(C=0.5, max_iter=1200, random_state=RANDOM_STATE)),
            ]
        )
        propensity_model.fit(x.iloc[train_idx], treatment[train_idx])
        propensity[test_idx] = propensity_model.predict_proba(x.iloc[test_idx])[:, 1]
        for value, target in [(1, mu1), (0, mu0)]:
            subset = train_idx[treatment[train_idx] == value]
            model = clone(outcome_template)
            model.fit(x.iloc[subset], y[subset])
            target[test_idx] = model.predict_proba(x.iloc[test_idx])[:, 1]

    propensity = np.clip(propensity, 0.02, 0.98)
    influence = mu1 - mu0 + treatment * (y - mu1) / propensity - (1 - treatment) * (y - mu0) / (1 - propensity)
    estimate = float(influence.mean())
    rng = np.random.default_rng(RANDOM_STATE)
    draws = np.array([rng.choice(influence, len(influence), replace=True).mean() for _ in range(bootstrap)])
    weights = treatment / propensity + (1 - treatment) / (1 - propensity)
    result = {
        "estimate": estimate,
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
        "treated_rate": float(treatment.mean()),
        "effective_sample_size": float(weights.sum() ** 2 / np.square(weights).sum()),
        "poor_overlap_share": float(((propensity <= 0.020001) | (propensity >= 0.979999)).mean()),
        "tipping_point_bias": abs(estimate),
    }
    diagnostics = pd.DataFrame(
        {"treatment": treatment, "outcome": y, "propensity": propensity, "mu1": mu1, "mu0": mu0, "influence": influence}
    )
    before = _standardized_differences(x, treatment).rename(columns={"standardized_difference": "before"})
    after = _standardized_differences(x, treatment, weights).rename(columns={"standardized_difference": "after"})
    balance = before.merge(after, on="feature")
    return result, diagnostics, balance


def run_causal_analysis(bootstrap: int = 500, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    frame = load_model_frame()
    outcomes = {
        "low_review": frame.dropna(subset=["low_review"]),
        "repeat_purchase_90d": frame[frame.repeat_observed_90d == 1],
    }
    results: dict[str, Any] = {
        "method": "5-fold cross-fitted augmented inverse probability weighting",
        "warning": "Observational estimates; validity depends on no important unmeasured confounding.",
        "outcomes": {},
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for outcome, subset in outcomes.items():
        estimate, diagnostics, balance = aipw_effect(subset, outcome, bootstrap=bootstrap)
        placebo_result, _, _ = aipw_effect(subset, outcome, bootstrap=max(50, bootstrap // 5), placebo=True)
        estimate["placebo_permuted_treatment_estimate"] = placebo_result["estimate"]
        estimate["placebo_pass"] = bool(
            abs(placebo_result["estimate"]) < max(0.005, abs(estimate["estimate"]) * 0.25)
        )
        estimate["n"] = len(subset)
        results["outcomes"][outcome] = estimate
        diagnostics.to_csv(artifact_dir / f"causal_{outcome}_diagnostics.csv", index=False)
        balance.to_csv(artifact_dir / f"causal_{outcome}_balance.csv", index=False)
    (artifact_dir / "causal_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    _write_causal_report(results)
    return results


def _write_causal_report(results: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Causal analysis report",
        "",
        "> Observational evidence, not proof of causation. No recovery offer exists in this dataset.",
        "",
        "Late delivery is the exposure. Models adjust for approval-time order, seller, product and geographic variables using cross-fitted AIPW.",
        "",
    ]
    for outcome, result in results["outcomes"].items():
        lines.extend(
            [
                f"## {outcome.replace('_', ' ').title()}",
                "",
                f"Estimated risk difference: **{result['estimate']:.3f}** (95% bootstrap CI {result['ci_low']:.3f} to {result['ci_high']:.3f}; n={result['n']:,}).",
                f"Poor-overlap share: {result['poor_overlap_share']:.1%}; effective sample size: {result['effective_sample_size']:.0f}.",
                f"A systematic unmeasured bias of {result['tipping_point_bias']:.3f} risk-difference points could move the estimate to zero.",
                "",
            ]
        )
    lines.extend(
        [
            "## Identification limitations",
            "",
            "Unrecorded carrier quality, customer expectations, seller operations and local disruptions may affect both lateness and outcomes. Positivity can fail for unusually distant or operationally difficult orders. The estimates should motivate an experiment, not authorize a rollout.",
        ]
    )
    (REPORT_DIR / "causal_report.md").write_text("\n".join(lines), encoding="utf-8")
