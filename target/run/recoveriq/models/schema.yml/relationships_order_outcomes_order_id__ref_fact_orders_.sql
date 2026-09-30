
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select  as from_field
    from "recoveriq"."analytics"."order_outcomes"
    where  is not null
),

parent as (
    select order_id as to_field
    from "recoveriq"."analytics"."fact_orders"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test