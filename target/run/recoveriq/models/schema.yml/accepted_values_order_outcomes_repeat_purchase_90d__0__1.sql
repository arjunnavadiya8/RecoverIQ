
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

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



  
  
      
    ) dbt_internal_test