# Delivery-risk model card

Results use the historical, anonymized Olist dataset.

## Intended use

Estimate late-delivery risk at order approval for prioritization and experiment planning. It is not a promise to customers and must not trigger an offer without a randomized evaluation.

## Model and evaluation

- Version: `0.1.0`
- Selected model: `lightgbm`
- Chronological test PR-AUC: `0.091`
- Chronological test Brier score: `0.041`
- Recall among highest-risk 10%: `0.261`
- Decision threshold: `0.159`
- Decision recommendation: **retain simple rule; keep ML in shadow mode**

## Leading global drivers

- estimated_delivery_days: 916.000
- customer_seller_distance_km: 830.000
- purchase_month: 706.000
- freight_value: 609.000
- seller_prior_orders: 603.000
- seller_prior_late_rate: 532.000
- price: 526.000
- purchase_hour: 290.000

## Limitations

The data covers a historical Brazilian marketplace. Geography, operations, promised-date policy and customer behavior may not generalize. Labels arrive after delivery, subgroup metrics can be noisy, and the model does not estimate coupon response. Monitor input drift, calibration and delayed outcomes before any real use.
