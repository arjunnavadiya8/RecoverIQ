with base as (
  select
    o.*,
    case when o.order_status = 'delivered'
      and cast(o.order_delivered_customer_date as date) > cast(o.order_estimated_delivery_date as date)
      then 1 else 0 end as observed_late
  from "recoveriq"."analytics"."fact_orders" o
), seller_history as (
  select
    *,
    count(*) over (
      partition by primary_seller_id order by order_purchase_timestamp, order_id
      rows between unbounded preceding and 1 preceding
    ) as seller_prior_orders,
    avg(observed_late) over (
      partition by primary_seller_id order by order_purchase_timestamp, order_id
      rows between unbounded preceding and 1 preceding
    ) as seller_prior_late_rate
  from base
), enriched as (
  select
    h.*,
    cg.latitude as customer_lat,
    cg.longitude as customer_lng,
    sg.latitude as seller_lat,
    sg.longitude as seller_lng
  from seller_history h
  left join "recoveriq"."analytics"."stg_geo" cg on h.customer_zip_code_prefix = cg.zip_code_prefix
  left join "recoveriq"."analytics"."stg_geo" sg on h.seller_zip_code_prefix = sg.zip_code_prefix
)
select
  order_id,
  order_purchase_timestamp,
  price,
  freight_value,
  item_count,
  seller_count,
  date_diff('day', order_approved_at, order_estimated_delivery_date) as estimated_delivery_days,
  case when customer_lat is null or seller_lat is null then null else
    6371 * 2 * asin(sqrt(
      pow(sin(radians(customer_lat - seller_lat) / 2), 2) +
      cos(radians(seller_lat)) * cos(radians(customer_lat)) *
      pow(sin(radians(customer_lng - seller_lng) / 2), 2)
    )) end as customer_seller_distance_km,
  seller_prior_orders,
  coalesce(seller_prior_late_rate, 0.0) as seller_prior_late_rate,
  extract(hour from order_purchase_timestamp) as purchase_hour,
  extract(dow from order_purchase_timestamp) as purchase_day_of_week,
  extract(month from order_purchase_timestamp) as purchase_month,
  coalesce(customer_state, 'unknown') as customer_state,
  coalesce(seller_state, 'unknown') as seller_state,
  coalesce(product_category_name_english, 'unknown') as product_category_name_english
from enriched
where order_approved_at is not null