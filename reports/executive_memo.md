# Executive decision memo

## Recommendation

Do not launch a recovery offer from observational results. Use the calibrated risk model to define an eligible high-risk population, then run a customer-randomized experiment sized by the planner.

## Evidence to fill after the real-data run

- Model test PR-AUC and calibration: see `artifacts/metrics.json`.
- Share of late orders captured in the highest-risk decile: see the model card.
- Observational late-delivery effect and uncertainty: see the causal report.
- Required sample and experiment duration: select the commercially meaningful MDE in the app.
- Break-even lift: vary cost and retained-customer value in the scenario tool.

## Decision rules

1. Do not proceed if the score is materially miscalibrated in recent or major regional cohorts.
2. Randomize by customer, log assignment before sending an offer, and analyze intention-to-treat.
3. Stop and investigate if the sample-ratio-mismatch test has p < 0.001.
4. Ship only if the confidence interval and guardrails support positive net value at the agreed cost assumptions.

## Risks

Historical-domain shift, unmeasured confounding, delayed repeat labels, cold-start sellers and uncertain customer value remain material. The experiment resolves offer lift; it does not resolve all deployment drift.

