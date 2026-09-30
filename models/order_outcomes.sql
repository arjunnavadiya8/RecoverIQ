with bounds as (
  select max(order_purchase_timestamp) as observation_end from {{ ref('fact_orders') }}
)
select
  o.order_id,
  case when o.order_status = 'delivered'
    and cast(o.order_delivered_customer_date as date) > cast(o.order_estimated_delivery_date as date)
    then 1 else 0 end as late_delivery,
  case when o.review_score <= 2 then 1 else 0 end as low_review,
  case when exists (
    select 1 from {{ ref('fact_orders') }} future
    where future.customer_unique_id = o.customer_unique_id
      and future.order_purchase_timestamp > o.order_delivered_customer_date
      and future.order_purchase_timestamp <= o.order_delivered_customer_date + interval 90 day
  ) then 1 else 0 end as repeat_purchase_90d,
  case when o.order_delivered_customer_date <= b.observation_end - interval 90 day then 1 else 0 end as repeat_observed_90d
from {{ ref('fact_orders') }} o
cross join bounds b

