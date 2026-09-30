# Monitoring plan

## Before scoring

- Validate request schema, allowed categories, nonnegative monetary values and plausible distance/delivery windows.
- Compare numeric input distributions with training data using PSI; investigate PSI above 0.20.
- Track unseen-category frequency and missing-value rate.

## With delayed labels

- Weekly: calibration curve, Brier score, PR-AUC and recall in the top risk decile.
- Slice by purchase month, state, category and seller-history depth; report sample size with every slice.
- Recalibrate before retraining when ranking remains useful but probabilities drift.

## Experiment health

- Assignment logging completeness and customer-level contamination
- Sample-ratio mismatch at p < 0.001
- Offer delivery rate, spend, cancellations and low reviews
- Intention-to-treat primary analysis after the fixed 90-day window

## Response

Pause intervention decisions on schema failures, severe calibration drift or assignment defects. Keep scoring shadow-only while investigating. Never silently retrain on partially observed outcomes.

