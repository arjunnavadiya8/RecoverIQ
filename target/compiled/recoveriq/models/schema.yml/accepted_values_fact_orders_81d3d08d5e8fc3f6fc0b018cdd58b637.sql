
    
    

with all_values as (

    select
        order_status as value_field,
        count(*) as n_records

    from "recoveriq"."analytics"."fact_orders"
    group by order_status

)

select *
from all_values
where value_field not in (
    'approved','canceled','created','delivered','invoiced','processing','shipped','unavailable'
)


