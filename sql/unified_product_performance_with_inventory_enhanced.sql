-- =====================================================
-- ENHANCED UNIFIED PRODUCT PERFORMANCE + INVENTORY MODEL
-- WITH PHASE 2 MARKETING ATTRIBUTION SUPPORT
-- =====================================================

-- Your existing Product Performance Aggregated model
WITH product_performance_base AS (
  SELECT 
    date,
    product_id,
    product_name,
    product_category,
    product_sku,
    shopify_units_sold,
    shopify_revenue,
    shopify_orders,
    shopify_avg_selling_price,
    
    -- Enhanced Facebook Attribution (Phase 2 Requirements)
    facebook_spend,
    facebook_impressions,
    facebook_clicks,
    facebook_attributed_revenue,
    facebook_attributed_units,
    -- NEW: 7-day attribution window for Phase 2
    COALESCE(facebook_7d_attributed_revenue, facebook_attributed_revenue) as facebook_7d_attributed_revenue,
    
    -- Enhanced Klaviyo Attribution (Phase 2 Requirements)
    klaviyo_emails_sent,  -- CRITICAL: Email volume for efficiency calculation
    klaviyo_emails_opened,
    klaviyo_emails_clicked,
    klaviyo_attributed_revenue,
    klaviyo_attributed_units,
    -- NEW: 3-day attribution window for Phase 2
    COALESCE(klaviyo_3d_attributed_revenue, klaviyo_attributed_revenue) as klaviyo_3d_attributed_revenue,
    
    -- Marketing Totals
    total_marketing_spend,
    total_attributed_revenue,
    total_attributed_units,
    organic_revenue,
    organic_units
  FROM {{your_existing_product_performance_aggregated_model}}
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

-- Your working inventory model (embedded directly)
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
    select
        ii.id as inventory_item_id,
        SAFE_CAST(ii.cost as FLOAT64) as inventory_item_cost
    from
        {{raw.shopify.inventory_item}} ii
),
sales_90d as (
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
            when EXTRACT(MONTH from CURRENT_DATE()) in (11, 12, 1) then 1.3
            when EXTRACT(MONTH from CURRENT_DATE()) in (6, 7, 8) then 1.1
            when EXTRACT(MONTH from CURRENT_DATE()) in (9, 10) then 1.2
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

-- =====================================================
-- FINAL UNIFIED OUTPUT: SALES + INVENTORY + PHASE 2 MARKETING
-- =====================================================
SELECT 
  -- Date and Product Identification
  pp.date,
  pp.product_id,
  pp.product_name,
  pp.product_category,
  pp.product_sku,
  
  -- Sales Performance Data (from Product Performance)
  pp.shopify_units_sold,
  pp.shopify_revenue,
  pp.shopify_orders,
  pp.shopify_avg_selling_price,
  
  -- ENHANCED MARKETING ATTRIBUTION DATA (Phase 2 Requirements)
  -- Facebook Attribution with 7-day window
  COALESCE(pp.facebook_spend, 0) as facebook_spend,
  COALESCE(pp.facebook_attributed_revenue, 0) as facebook_attributed_revenue,
  COALESCE(pp.facebook_7d_attributed_revenue, 0) as facebook_7d_attributed_revenue,
  COALESCE(pp.facebook_attributed_units, 0) as facebook_attributed_units,
  
  -- Klaviyo Attribution with 3-day window and email volume
  COALESCE(pp.klaviyo_emails_sent, 0) as klaviyo_emails_sent,
  COALESCE(pp.klaviyo_attributed_revenue, 0) as klaviyo_attributed_revenue,
  COALESCE(pp.klaviyo_3d_attributed_revenue, 0) as klaviyo_3d_attributed_revenue,
  COALESCE(pp.klaviyo_attributed_units, 0) as klaviyo_attributed_units,
  
  -- Marketing Totals
  COALESCE(pp.total_marketing_spend, 0) as total_marketing_spend,
  COALESCE(pp.total_attributed_revenue, 0) as total_attributed_revenue,
  COALESCE(pp.organic_revenue, 0) as organic_revenue,
  COALESCE(pp.organic_units, 0) as organic_units,
  
  -- REAL INVENTORY DATA (from your working inventory model)
  COALESCE(inv.current_inventory_level, 0) as current_inventory_level,
  COALESCE(inv.available_inventory, 0) as available_inventory,
  COALESCE(inv.reserved_inventory, 0) as reserved_inventory,
  
  -- Business Rules (from your inventory model)
  COALESCE(inv.reorder_point, 21) as reorder_point,
  COALESCE(inv.reorder_quantity, 30) as reorder_quantity,
  COALESCE(inv.max_stock_level, 75) as max_stock_level,
  COALESCE(inv.min_stock_level, 3) as min_stock_level,
  COALESCE(inv.lead_time_days, 42) as lead_time_days,
  COALESCE(inv.safety_stock_days, 14) as safety_stock_days,
  
  -- Cost and Profitability (from your inventory model)
  COALESCE(inv.unit_cost_gbp, pp.shopify_revenue * 0.6) as unit_cost_gbp,
  COALESCE(inv.selling_price_gbp, pp.shopify_avg_selling_price) as selling_price_gbp,
  COALESCE(inv.profit_margin_percentage, 40.0) as profit_margin_percentage,
  COALESCE(inv.profit_per_unit_gbp, pp.shopify_avg_selling_price * 0.4) as profit_per_unit_gbp,
  COALESCE(inv.inventory_value_gbp, 0.0) as inventory_value_gbp,
  
  -- Inventory Analytics (from your inventory model)
  COALESCE(inv.average_daily_sales, pp.shopify_units_sold / 30.0) as average_daily_sales,
  COALESCE(inv.days_of_stock_remaining, 999) as days_of_stock_remaining,
  COALESCE(inv.reorder_urgency, 'UNKNOWN') as reorder_urgency,
  COALESCE(inv.overstock_risk, 'UNKNOWN') as overstock_risk,
  COALESCE(inv.abc_classification, 'C') as abc_classification,
  COALESCE(inv.seasonality_factor, 1.0) as seasonality_factor,
  
  -- Data Quality Indicators
  CASE 
    WHEN inv.product_sku IS NOT NULL THEN 'inventory_data_available'
    ELSE 'inventory_data_missing'
  END as inventory_data_status,
  
  CASE 
    WHEN COALESCE(pp.facebook_spend, 0) > 0 OR COALESCE(pp.klaviyo_emails_sent, 0) > 0 THEN 'marketing_data_available'
    ELSE 'marketing_data_missing'
  END as marketing_data_status,
  
  -- ACCURATE Stock GRIP Calculations (using REAL inventory)
  GREATEST(0, 
    ROUND(
      -- 6-week demand with seasonality
      ((pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0)) +
      -- Safety stock buffer
      ((pp.shopify_units_sold / 30.0) * COALESCE(inv.safety_stock_days, 14)) -
      -- REAL available inventory (not estimated!)
      COALESCE(inv.available_inventory, 0),
      0
    )
  ) as recommended_order_quantity,
  
  -- Revenue Risk (based on real stock levels)
  CASE 
    WHEN COALESCE(inv.days_of_stock_remaining, 999) < 42 THEN
      ROUND(
        (42 - COALESCE(inv.days_of_stock_remaining, 999)) * 
        (pp.shopify_units_sold / 30.0) * 
        COALESCE(inv.selling_price_gbp, pp.shopify_avg_selling_price),
        2
      )
    ELSE 0
  END as revenue_at_risk_gbp,
  
  CURRENT_TIMESTAMP() as export_timestamp

FROM product_performance_base pp
LEFT JOIN inventory_with_analytics inv ON pp.product_sku = inv.product_sku

-- Only include products with sales activity or current inventory
WHERE pp.shopify_units_sold > 0 
   OR COALESCE(inv.current_inventory_level, 0) > 0

ORDER BY 
  -- Priority: Urgent reorders first
  CASE 
    WHEN COALESCE(inv.reorder_urgency, 'LOW') = 'URGENT' THEN 1
    WHEN COALESCE(inv.reorder_urgency, 'LOW') = 'HIGH' THEN 2
    WHEN COALESCE(inv.reorder_urgency, 'LOW') = 'MEDIUM' THEN 3
    ELSE 4
  END,
  -- Secondary: Revenue impact
  pp.shopify_revenue DESC,
  -- Tertiary: Days until stockout
  COALESCE(inv.days_of_stock_remaining, 999) ASC;

-- =====================================================
-- EXPORT CONFIGURATION FOR PHASE 2 MARKETING INTEGRATION
-- =====================================================
-- File Name: stock_grip_unified_sales_inventory_marketing.csv
-- Update Frequency: Daily
-- Contains: Sales + Real inventory + Enhanced marketing attribution
-- Phase 2 Support: Facebook 7d ROAS + Klaviyo 3d efficiency
-- Marketing Intelligence: Channel-specific optimization ready
-- =====================================================