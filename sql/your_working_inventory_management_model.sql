-- =====================================================
-- YOUR WORKING INVENTORY MANAGEMENT MODEL
-- Standalone SQL using Shopify API data exclusively
-- =====================================================

-- Inventory management using unit cost exclusively from {{raw.shopify.inventory_item}}. No external cost table.
with
    product_variants as (
        select
            pv.id as variant_id,
            pv.sku as product_sku,
            pv.product_id as product_id,
            pv.price as selling_price_gbp,
            pv.inventory_item_id as inventory_item_id,
            p.title as product_name,
            p.product_type as category,
            p.status as product_status,
            p.created_at as product_created_date,
            p.updated_at as product_updated_at,
            COALESCE(pv.inventory_quantity, 0) as variant_inventory_quantity
        from
            {{raw.shopify.product_variant}} pv
            join {{raw.shopify.product}} p on pv.product_id = p.id
        where
            p.status = 'active'
            and pv.sku is not null
    ),
    inventory_items as (
        -- Use the inventory_item table for unit cost only (no on-hand quantity available in this table)
        select
            ii.id as inventory_item_id,
            SAFE_CAST(ii.cost as FLOAT64) as inventory_item_cost
        from
            {{raw.shopify.inventory_item}} ii
    ),
    sales_90d as (
        -- Sales quantity in the last 90 days (used to compute average daily sales)
        select
            ol.product_id as product_id,
            SUM(COALESCE(ol.quantity, 0)) as qty_90d
        from
            {{raw.shopify.order_line}} ol
            join {{raw.shopify.order}} o on ol.order_id = o.id
        where
            o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
            and o.cancelled_at is null
        group by
            ol.product_id
    ),
    revenue_30d as (
        -- Revenue per product over the last 30 days (price * quantity)
        select
            ol.product_id as product_id,
            SUM(COALESCE(ol.price, 0) * COALESCE(ol.quantity, 0)) as revenue_30d
        from
            {{raw.shopify.order_line}} ol
            join {{raw.shopify.order}} o on ol.order_id = o.id
        where
            o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            and o.cancelled_at is null
        group by
            ol.product_id
    ),
    revenue_ranked as (
        select
            r.product_id,
            r.revenue_30d,
            (
                PERCENT_RANK() over (
                    order by
                        COALESCE(r.revenue_30d, 0) desc
                ) * 100
            ) as monthly_revenue_rank
        from
            revenue_30d r
    ),
    inventory_base as (
        select
            pv.product_sku,
            pv.product_id,
            pv.product_name,
            pv.category,
            COALESCE(pv.variant_inventory_quantity, 0) as current_inventory_level,
            0 as reserved_inventory,
            COALESCE(pv.variant_inventory_quantity, 0) as available_inventory,
            -- Use inventory_item.cost exclusively (fallback to 0.0)
            COALESCE(ii.inventory_item_cost, 0.0) as unit_cost_gbp,
            COALESCE(pv.selling_price_gbp, 0.0) as selling_price_gbp,
            'Unknown' as supplier_name,
            null as last_reorder_date,
            pv.product_created_date,
            pv.product_updated_at as last_updated
        from
            product_variants pv
            left join inventory_items ii on pv.inventory_item_id = ii.inventory_item_id
    ),
    inventory_enhanced as (
        select
            ib.*,
            ROUND(
                (
                    (ib.selling_price_gbp - ib.unit_cost_gbp) / NULLIF(ib.selling_price_gbp, 0)
                ) * 100,
                2
            ) as profit_margin_percentage,
            ROUND(ib.selling_price_gbp - ib.unit_cost_gbp, 2) as profit_per_unit_gbp,
            ROUND(ib.current_inventory_level * ib.unit_cost_gbp, 2) as inventory_value_gbp,
            case
                when LOWER(ib.category) = 'apparel_tops' then 14
                when LOWER(ib.category) = 'apparel_bottoms' then 21
                when LOWER(ib.category) = 'accessories' then 28
                else 21
            end as reorder_point,
            case
                when LOWER(ib.category) = 'apparel_tops' then 50
                when LOWER(ib.category) = 'apparel_bottoms' then 30
                when LOWER(ib.category) = 'accessories' then 20
                else 30
            end as reorder_quantity,
            case
                when LOWER(ib.category) = 'apparel_tops' then 100
                when LOWER(ib.category) = 'apparel_bottoms' then 75
                when LOWER(ib.category) = 'accessories' then 50
                else 75
            end as max_stock_level,
            case
                when LOWER(ib.category) = 'apparel_tops' then 5
                when LOWER(ib.category) = 'apparel_bottoms' then 3
                when LOWER(ib.category) = 'accessories' then 2
                else 3
            end as min_stock_level,
            42 as lead_time_days,
            14 as safety_stock_days,
            case
                when EXTRACT(
                    MONTH
                    from
                        CURRENT_DATE()
                ) in (11, 12, 1) then 1.3
                when EXTRACT(
                    MONTH
                    from
                        CURRENT_DATE()
                ) in (6, 7, 8) then 1.1
                when EXTRACT(
                    MONTH
                    from
                        CURRENT_DATE()
                ) in (9, 10) then 1.2
                else 1.0
            end as seasonality_factor
        from
            inventory_base ib
    ),
    inventory_with_analytics as (
        select
            ie.*,
            COALESCE(s.qty_90d, 0) / 90.0 as average_daily_sales,
            case
                when COALESCE(s.qty_90d, 0) > 0 then ROUND(
                    ie.available_inventory / (COALESCE(s.qty_90d, 0) / 90.0),
                    1
                )
                else 999
            end as days_of_stock_remaining,
            case
                when ie.available_inventory <= ie.reorder_point then 'URGENT'
                when ie.available_inventory <= (ie.reorder_point * 1.5) then 'HIGH'
                when ie.available_inventory <= (ie.reorder_point * 2.0) then 'MEDIUM'
                else 'LOW'
            end as reorder_urgency,
            case
                when ie.available_inventory > ie.max_stock_level then 'HIGH'
                when ie.available_inventory > (ie.max_stock_level * 0.8) then 'MEDIUM'
                else 'LOW'
            end as overstock_risk,
            case
                when COALESCE(rr.monthly_revenue_rank, 100) <= 20 then 'A'
                when COALESCE(rr.monthly_revenue_rank, 100) <= 50 then 'B'
                else 'C'
            end as abc_classification,
            COALESCE(rr.monthly_revenue_rank, 100) as monthly_revenue_rank
        from
            inventory_enhanced ie
            left join sales_90d s on ie.product_id = s.product_id
            left join revenue_ranked rr on ie.product_id = rr.product_id
    )
select
    product_sku,
    product_id,
    product_name,
    category,
    current_inventory_level,
    reserved_inventory,
    available_inventory,
    reorder_point,
    reorder_quantity,
    max_stock_level,
    min_stock_level,
    lead_time_days,
    safety_stock_days,
    unit_cost_gbp,
    selling_price_gbp,
    profit_margin_percentage,
    profit_per_unit_gbp,
    inventory_value_gbp,
    supplier_name,
    last_reorder_date,
    average_daily_sales,
    days_of_stock_remaining,
    reorder_urgency,
    overstock_risk,
    seasonality_factor,
    abc_classification,
    monthly_revenue_rank,
    last_updated
from
    inventory_with_analytics
order by
    case reorder_urgency
        when 'URGENT' then 4
        when 'HIGH' then 3
        when 'MEDIUM' then 2
        when 'LOW' then 1
        else 0
    end desc,
    days_of_stock_remaining asc;