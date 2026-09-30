# Career packaging

## LinkedIn launch draft

I built RecoverIQ to answer a product question that a classifier alone cannot: if an order looks likely to arrive late, what evidence would justify a customer-recovery intervention?

The project joins nine marketplace tables in DuckDB/dbt, creates point-in-time seller features, compares a simple operating rule with calibrated ML on a chronological holdout, estimates observational effects using cross-fitted doubly robust methods, and turns the result into a powered customer-level experiment. A Streamlit decision app makes the cost and lift assumptions explicit; FastAPI and Docker expose the scoring contract.

The most important conclusion is methodological: the dataset contains late deliveries, reviews and repeat purchases, but no randomized recovery offers. So the app never presents coupon lift as fact. It shows the break-even assumption and the experiment needed to learn it.

[Add repository URL] · [Add live demo URL]

## Résumé bullets

Replace bracketed values only with numbers from the real-data artifacts.

- Built a leakage-safe e-commerce delivery-risk system across nine relational tables using DuckDB, dbt, Python and LightGBM; achieved `[PR-AUC]` chronological holdout PR-AUC and captured `[top-decile recall]` of late orders in the highest-risk decile.
- Developed a cross-fitted doubly robust causal analysis and customer-level experiment planner linking delivery reliability to reviews and 90-day retention; deployed a calibrated FastAPI model and interactive ROI/power dashboard with automated tests and Docker CI.

## Three-minute demo outline

1. 20 seconds: stakeholder, decision and honest limitation.
2. 40 seconds: warehouse and leakage-safe feature lineage.
3. 45 seconds: holdout metrics, calibration and risk explorer.
4. 45 seconds: causal interval, overlap and confounding warning.
5. 40 seconds: budget scenario and powered experiment.
6. 10 seconds: reproducibility, API and links.

