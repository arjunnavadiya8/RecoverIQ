# RecoverIQ product brief

## Stakeholder and decision

The stakeholder is a marketplace Customer Experience lead deciding whether to test proactive recovery offers for orders likely to arrive after their promised date. The immediate decision is **who enters an experiment**, not whether to launch offers to everyone.

## Users

- Operations managers need a prioritized risk queue.
- Product managers need expected reach, economics and experiment duration.
- Data scientists need leakage-safe features, calibrated probabilities and defensible uncertainty.

## Metric tree

**North star:** repeat purchase within 90 days among customers with a complete observation window.

**Drivers:** promised-date miss rate, delivery duration, low-review rate and cancellation rate.

**Decision metrics:** late orders captured in the highest-risk decile, probability calibration, expected net value and break-even offer lift.

**Guardrails:** total offer cost, offers sent to on-time orders, cancellation/return signals, low reviews and performance by customer region.

## Success criteria

- A reviewer can reproduce the warehouse and model from documented commands.
- Model selection uses chronological validation and decision cost.
- The causal report distinguishes association, identification assumptions and uncertainty.
- The product never represents assumed recovery lift as observed evidence.
- The experiment planner returns sample size and duration for 0.5–2 percentage-point MDEs.

## Non-goals

Real-time carrier integration, production coupon issuance, current Olist performance claims and causal claims about recovery offers are outside this historical case study.

