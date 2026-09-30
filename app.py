from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from recoveriq.config import ARTIFACT_DIR, DB_PATH
from recoveriq.experimentation import mde_grid, policy_simulation
from recoveriq.modeling import load_bundle

st.set_page_config(page_title="RecoverIQ", page_icon="📦", layout="wide")
st.title("RecoverIQ")
st.caption("Delivery risk, retention evidence, and experiment decisions — a historical case study")


@st.cache_data
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        orders = con.execute(
            """select f.*, o.late_delivery, o.low_review, o.repeat_purchase_90d,
                      o.repeat_observed_90d
               from analytics.order_features f
               join analytics.order_outcomes o using(order_id)"""
        ).df()
    predictions = pd.read_csv(ARTIFACT_DIR / "predictions.csv")
    return orders, predictions


if not DB_PATH.exists() or not (ARTIFACT_DIR / "model.joblib").exists():
    st.error("Project artifacts are missing. Run `python -m recoveriq.cli pipeline --demo` for a demo or run the real-data pipeline.")
    st.stop()

orders, predictions = load_dashboard_data()
data = orders.merge(predictions[["order_id", "split", "late_probability"]], on="order_id", how="left")
manifest_path = Path("data/raw/manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
if manifest.get("source") == "synthetic_demo":
    st.warning("DEMO DATA ONLY — charts and metrics below must not be used as portfolio claims.")

page = st.sidebar.radio(
    "View",
    ["Executive overview", "Risk explorer", "Causal evidence", "Experiment & ROI planner"],
)

if page == "Executive overview":
    observed = data[data.repeat_observed_90d == 1]
    cols = st.columns(4)
    cols[0].metric("Orders", f"{len(data):,}")
    cols[1].metric("Late-delivery rate", f"{data.late_delivery.mean():.1%}")
    cols[2].metric("Low-review rate", f"{data.low_review.mean():.1%}")
    cols[3].metric("90-day repeat rate", f"{observed.repeat_purchase_90d.mean():.1%}")
    monthly = data.assign(month=pd.to_datetime(data.order_purchase_timestamp).dt.to_period("M").astype(str)).groupby("month", as_index=False).agg(late_rate=("late_delivery", "mean"), orders=("order_id", "count"))
    st.plotly_chart(px.line(monthly, x="month", y="late_rate", markers=True, title="Late-delivery rate over time"), width="stretch")
    st.info("Decision: identify high-risk approved orders, quantify downside, and validate any recovery offer with a randomized experiment.")

elif page == "Risk explorer":
    bundle = load_bundle()
    col1, col2 = st.columns(2)
    threshold = col1.slider("Risk threshold", 0.0, 1.0, float(bundle.threshold), 0.01)
    state = col2.selectbox("Customer state", ["All"] + sorted(data.customer_state.dropna().unique().tolist()))
    subset = data if state == "All" else data[data.customer_state == state]
    subset = subset.assign(flagged=subset.late_probability >= threshold)
    a, b, c = st.columns(3)
    a.metric("Flagged orders", f"{subset.flagged.sum():,}")
    b.metric("Flag rate", f"{subset.flagged.mean():.1%}")
    c.metric("Late captured", f"{subset.loc[subset.flagged, 'late_delivery'].sum() / max(1, subset.late_delivery.sum()):.1%}")
    st.plotly_chart(px.histogram(subset, x="late_probability", color="late_delivery", nbins=30, barmode="overlay", title="Risk-score separation"), width="stretch")
    importance = pd.read_csv(ARTIFACT_DIR / "feature_importance.csv").head(12)
    st.plotly_chart(px.bar(importance.sort_values("importance"), x="importance", y="feature", orientation="h", title="Leading global model drivers"), width="stretch")

elif page == "Causal evidence":
    path = ARTIFACT_DIR / "causal_results.json"
    if not path.exists():
        st.warning("Run `python -m recoveriq.cli causal` to generate causal estimates.")
    else:
        results = json.loads(path.read_text(encoding="utf-8"))
        st.warning(results["warning"])
        rows = []
        for outcome, values in results["outcomes"].items():
            rows.append({"outcome": outcome, **values})
        result_frame = pd.DataFrame(rows)
        st.dataframe(result_frame[["outcome", "estimate", "ci_low", "ci_high", "n", "poor_overlap_share", "placebo_permuted_treatment_estimate"]], width="stretch")
        chart = px.scatter(result_frame, x="estimate", y="outcome", error_x=result_frame.ci_high - result_frame.estimate, error_x_minus=result_frame.estimate - result_frame.ci_low, title="Estimated risk difference from late delivery")
        chart.add_vline(x=0, line_dash="dash")
        st.plotly_chart(chart, width="stretch")
        st.markdown("Unrecorded carrier quality, local disruptions, seller operations, and customer expectations may confound these estimates. They motivate an experiment; they do not prove an offer will work.")

else:
    observed = data[data.repeat_observed_90d == 1]
    baseline = float(observed.repeat_purchase_90d.mean())
    st.subheader("Experiment power")
    daily = st.number_input("Eligible customers per day", min_value=10, value=500, step=10)
    st.dataframe(mde_grid(max(0.001, baseline), int(daily)).style.format({"baseline_rate": "{:.1%}", "absolute_mde": "{:.1%}"}), width="stretch")
    st.caption("Customer-level randomization; primary metric: 90-day repeat purchase. Guardrails: cancellations, refunds, low reviews, and offer cost.")
    st.subheader("Service-recovery scenario — not an observed treatment effect")
    c1, c2, c3, c4 = st.columns(4)
    budget = c1.number_input("Budget", min_value=0.0, value=10000.0, step=500.0)
    cost = c2.number_input("Offer cost", min_value=0.01, value=10.0, step=1.0)
    lift = c3.slider("Assumed retention lift", 0.0, 0.10, 0.01, 0.0025)
    value = c4.number_input("Value per retained customer", min_value=0.0, value=150.0, step=10.0)
    simulation = policy_simulation(data.dropna(subset=["late_probability"]), budget, cost, lift, value)
    st.json(simulation)
    st.caption("The lift control is a scenario assumption. Only a randomized experiment can estimate it credibly.")
