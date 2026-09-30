
    
    

with all_values as (

    select
        repeat_purchase_90d as value_field,
        count(*) as n_records

    from "recoveriq"."analytics"."order_outcomes"
    group by repeat_purchase_90d

)

select *
from all_values
where value_field not in (
    '0','1'
)


