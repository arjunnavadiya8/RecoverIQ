# Five-minute interview walkthrough

**0:00–0:40 — Business decision.** A product lead is considering proactive recovery for likely late orders. The project separates prediction, causal evidence and experiment design because none substitutes for the others.

**0:40–1:30 — Data design.** Show the nine-table source, dbt tests and one-row-per-order models. Explain why repeat behavior uses `customer_unique_id`, why recent orders are censored, and how seller history excludes the current/future orders.

**1:30–2:30 — Model judgment.** Explain chronological validation, calibration and why PR-AUC/top-decile recall matter more than accuracy. Compare the selected model with a transparent operational rule and discuss the 5:1 cost assumption.

**2:30–3:30 — Causal honesty.** Late delivery is observed, not randomized. Walk through cross-fitted AIPW, overlap, balance, placebo and tipping-point sensitivity. State the unmeasured-confounding limitation before discussing the estimate.

**3:30–4:30 — Product decision.** Use the dashboard to change budget, offer cost, assumed lift and retained-customer value. Point out that lift is a scenario input because no offer exists in the data.

**4:30–5:00 — Experiment and production.** Show the powered customer-level test, guardrails, SRM check, API contract, monitoring plan and the point where you would pause a rollout.

## Questions to be ready for

- Why not randomly split the data?
- What leakage did you prevent?
- Why calibrate probabilities?
- What confounders may be missing?
- When would you choose the rule instead of ML?
- How would delayed labels affect monitoring and retraining?

