# Data dictionary

## Core analytical tables

| Table | Grain | Purpose |
|---|---|---|
| `fact_orders` | One order | Customer, lifecycle, item, seller, payment and review rollup |
| `order_features` | One approved order | Approval-time model inputs only |
| `order_outcomes` | One order | Late, low-review and censored 90-day repeat outcomes |

## Model features

| Feature | Availability and meaning |
|---|---|
| `price`, `freight_value`, `item_count`, `seller_count` | Basket attributes known at approval |
| `estimated_delivery_days` | Days from approval to promised delivery |
| `customer_seller_distance_km` | Approximate haversine distance between ZIP-prefix centroids |
| `seller_prior_orders` | Seller orders strictly before the current order |
| `seller_prior_late_rate` | Expanding historical late rate, excluding the current and future orders |
| purchase hour/day/month | Order timing known at approval |
| customer/seller state | Coarse geography |
| product category | English category rollup |

## Outcomes

| Outcome | Definition |
|---|---|
| `late_delivery` | Delivered calendar date is later than promised calendar date |
| `low_review` | Mean order review score is 2 or lower |
| `repeat_purchase_90d` | Same `customer_unique_id` purchases after delivery and within 90 days |
| `repeat_observed_90d` | Dataset continues at least 90 days beyond delivery |

`customer_unique_id`, not per-order `customer_id`, is used for repeat behavior. The raw Olist spellings such as `product_name_lenght` are preserved only in the raw layer.

