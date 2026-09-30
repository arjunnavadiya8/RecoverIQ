select
  i.order_id,
  count(*) as item_count,
  count(distinct i.seller_id) as seller_count,
  sum(i.price) as price,
  sum(i.freight_value) as freight_value,
  min(i.seller_id) as primary_seller_id,
  min(s.seller_state) as seller_state,
  min(s.seller_zip_code_prefix) as seller_zip_code_prefix,
  min(coalesce(t.product_category_name_english, p.product_category_name, 'unknown')) as product_category_name_english
from raw.order_items i
left join raw.sellers s using (seller_id)
left join raw.products p using (product_id)
left join raw.category_translation t using (product_category_name)
group by 1

