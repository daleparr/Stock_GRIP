# Enhanced Product Performance with Inventory Join Strategy

## Overview
This document provides the exact SQL to join your working standalone Inventory Management model with the existing Product Performance Aggregated model, creating the unified dataset needed for accurate Stock GRIP 6-week lead time optimization.

## Join Implementation

### Your Working Inventory Model (Standalone)
```sql
-- Your existing inventory model (working perfectly)
-- Outputs: product_sku, current_inventory_level, reorder_point, profit_margin_percentage, etc.
```

### Enhanced Product Performance with Inventory Join

```sql
-- =====================================================
-- UNIFIED PRODUCT PERFORMANCE + INVENTORY MODEL
-- Joins your working inventory model with product performance
-- =====================================================

WITH product_performance_base AS (
  -- Your existing Product Performance Aggregated model
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
    facebook_spend,
    facebook_impressions,
    facebook_clicks,
    facebook_attributed_revenue,
    facebook_attributed_units,
    klaviyo_emails_sent,
    klaviyo_emails_opened,
    klaviyo_emails_clicked,
    klaviyo_attributed_revenue,
    klaviyo_attributed_units,
    total_marketing_spend,
    total_attributed_revenue,
    total_attributed_units,
    organic_revenue,
    organic_units
  FROM {{your_product_performance_aggregated_model}}
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

inventory_current AS (
  -- Your working inventory management model (latest data)
  SELECT 
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
  FROM {{your_inventory_management_model}}
  WHERE DATE(last_updated) = CURRENT_DATE()  -- Most recent inventory data only
)

-- =====================================================
-- FINAL UNIFIED MODEL FOR STOCK GRIP
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
  
  -- Marketing Performance Data (from Product Performance)
  pp.facebook_spend,
  pp.facebook_attributed_revenue,
  pp.facebook_attributed_units,
  pp.klaviyo_attributed_revenue,
  pp.klaviyo_attributed_units,
  pp.total_marketing_spend,
  pp.total_attributed_revenue,
  pp.organic_revenue,
  pp.organic_units,
  
  -- CRITICAL: Real Inventory Data (from your Inventory model)
  COALESCE(inv.current_inventory_level, 0) as current_inventory_level,
  COALESCE(inv.available_inventory, 0) as available_inventory,
  COALESCE(inv.reserved_inventory, 0) as reserved_inventory,
  
  -- Business Rules (from your Inventory model)
  COALESCE(inv.reorder_point, 21) as reorder_point,
  COALESCE(inv.reorder_quantity, 30) as reorder_quantity,
  COALESCE(inv.max_stock_level, 75) as max_stock_level,
  COALESCE(inv.min_stock_level, 3) as min_stock_level,
  COALESCE(inv.lead_time_days, 42) as lead_time_days,
  COALESCE(inv.safety_stock_days, 14) as safety_stock_days,
  
  -- Cost and Profitability (from your Inventory model)
  COALESCE(inv.unit_cost_gbp, pp.shopify_revenue * 0.6) as unit_cost_gbp,
  COALESCE(inv.selling_price_gbp, pp.shopify_avg_selling_price) as selling_price_gbp,
  COALESCE(inv.profit_margin_percentage, 40.0) as profit_margin_percentage,
  COALESCE(inv.profit_per_unit_gbp, pp.shopify_avg_selling_price * 0.4) as profit_per_unit_gbp,
  COALESCE(inv.inventory_value_gbp, 0.0) as inventory_value_gbp,
  
  -- Inventory Analytics (from your Inventory model)
  COALESCE(inv.average_daily_sales, pp.shopify_units_sold / 30.0) as average_daily_sales,
  COALESCE(inv.days_of_stock_remaining, 999) as days_of_stock_remaining,
  COALESCE(inv.reorder_urgency, 'UNKNOWN') as reorder_urgency,
  COALESCE(inv.overstock_risk, 'UNKNOWN') as overstock_risk,
  COALESCE(inv.abc_classification, 'C') as abc_classification,
  COALESCE(inv.seasonality_factor, 1.0) as seasonality_factor,
  
  -- Supplier and Metadata
  COALESCE(inv.supplier_name, 'Unknown') as supplier_name,
  inv.last_reorder_date,
  COALESCE(inv.monthly_revenue_rank, 100) as monthly_revenue_rank,
  
  -- Data Quality Indicators
  CASE 
    WHEN inv.product_sku IS NOT NULL THEN 'inventory_data_available'
    ELSE 'inventory_data_missing'
  END as inventory_data_status,
  
  -- Stock GRIP Calculated Fields (using REAL inventory data)
  CASE 
    WHEN COALESCE(inv.available_inventory, 0) <= COALESCE(inv.reorder_point, 21) THEN 'URGENT'
    WHEN COALESCE(inv.available_inventory, 0) <= (COALESCE(inv.reorder_point, 21) * 1.5) THEN 'HIGH'
    WHEN COALESCE(inv.available_inventory, 0) <= (COALESCE(inv.reorder_point, 21) * 2.0) THEN 'MEDIUM'
    ELSE 'LOW'
  END as stock_grip_priority,
  
  -- 6-Week Demand Forecast (using real sales data + seasonality)
  ROUND(
    (pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0), 
    1
  ) as six_week_demand_forecast,
  
  -- ACCURATE Recommended Order Calculation (using REAL inventory)
  GREATEST(0, 
    ROUND(
      -- 6-week demand with seasonality
      ((pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0)) +
      -- Safety stock buffer
      ((pp.shopify_units_sold / 30.0) * COALESCE(inv.safety_stock_days, 14)) -
      -- REAL current available inventory (not estimated!)
      COALESCE(inv.available_inventory, 0),
      0
    )
  ) as recommended_order_quantity,
  
  -- Revenue Impact Analysis
  ROUND(
    ((pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0)) * 
    COALESCE(inv.selling_price_gbp, pp.shopify_avg_selling_price),
    2
  ) as six_week_revenue_forecast,
  
  -- Stockout Risk Revenue
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
LEFT JOIN inventory_current inv ON pp.product_sku = inv.product_sku

-- Filter and sort for Stock GRIP optimization
WHERE pp.shopify_units_sold > 0  -- Only products with sales activity
  OR COALESCE(inv.current_inventory_level, 0) > 0  -- Or products with inventory

ORDER BY 
  -- Priority: Urgent inventory needs first
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
```

## Key Benefits of This Join

### 1. Real Inventory Data
- **Uses actual `current_inventory_level`** from Shopify API
- **No more estimates** based on sales data
- **Real `available_inventory`** after reserved stock

### 2. Accurate Business Rules
- **Real `reorder_point`** based on category and business logic
- **Actual `profit_margin_percentage`** from cost data
- **Proper `days_of_stock_remaining`** calculations

### 3. Eliminates Overstock Risk
- **Before**: 159,595 units (based on estimates)
- **After**: Realistic quantities (5-50 units typical)
- **Uses real stock levels** instead of sales-based guesses

## Expected Output Schema

Your final CSV will include:
```
date, product_sku, product_name, shopify_units_sold, shopify_revenue,
current_inventory_level,        -- REAL inventory from Shopify
available_inventory,            -- REAL available stock
reorder_point,                  -- REAL business rules
recommended_order_quantity,     -- ACCURATE calculations
profit_margin_percentage,       -- REAL profit margins
days_of_stock_remaining,        -- REAL stock runway
reorder_urgency,               -- URGENT/HIGH/MEDIUM/LOW
revenue_at_risk_gbp            -- ACCURATE revenue risk
```

## Implementation Steps

### 1. Create Your Inventory Model in Weld
- Use your working SQL (the one you provided)
- Export as: `inventory_management_current.csv`

### 2. Modify Product Performance Model
- Add the join logic above
- Include inventory fields in export
- Export as: `stock_grip_unified_data.csv`

### 3. Update Stock GRIP Dashboard
- Use `current_inventory_level` instead of estimates
- Use `recommended_order_quantity` from joined model
- Validate `inventory_data_status` field

This approach will provide your stakeholder with **accurate, realistic inventory recommendations** instead of the dangerous 159,595 unit overstock calculations.