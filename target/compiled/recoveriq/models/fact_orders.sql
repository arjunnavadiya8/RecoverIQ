with reviews as (
  select order_id, avg(review_score) as review_score
  from raw.order_reviews group by 1
), payments as (
  select order_id, sum(payment_value) as payment_value
  from raw.order_payments group by 1
)
select
  o.order_id,
  c.customer_id,
  c.customer_unique_id,
  c.customer_state,
  c.customer_zip_code_prefix,
  i.primary_seller_id,
  i.seller_state,
  i.seller_zip_code_prefix,
  i.product_category_name_english,
  cast(o.order_purchase_timestamp as timestamp) as order_purchase_timestamp,
  cast(o.order_approved_at as timestamp) as order_approved_at,
  cast(o.order_delivered_customer_date as timestamp) as order_delivered_customer_date,
  cast(o.order_estimated_delivery_date as timestamp) as order_estimated_delivery_date,
  o.order_status,
  i.item_count,
  i.seller_count,
  i.price,
  i.freight_value,
  p.payment_value,
  r.review_score
from raw.orders o
join raw.customers c using (customer_id)
left join "recoveriq"."analytics"."stg_order_items" i using (order_id)
left join payments p using (order_id)
left join reviews r using (order_id)