# Inventory + Product Performance Join Strategy for Weld

## Overview
This document provides the exact SQL implementation to join the standalone Inventory Management model with your existing Product Performance Aggregated model, creating a unified dataset for accurate Stock GRIP inventory optimization.

## Join Implementation

### Step 1: Enhanced Product Performance Model with Inventory

```sql
-- =====================================================
-- ENHANCED PRODUCT PERFORMANCE WITH INVENTORY
-- Join your existing Product Performance with Inventory Management
-- =====================================================

WITH product_performance_base AS (
  -- Your existing Product Performance Aggregated query
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
  FROM Product_Performance_Aggregated
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

inventory_current AS (
  -- Your new Inventory Management model (latest data only)
  SELECT *
  FROM Inventory_Management_Model
  WHERE DATE(last_updated) = CURRENT_DATE()  -- Get most recent inventory data
)

-- =====================================================
-- FINAL JOINED MODEL FOR STOCK GRIP EXPORT
-- =====================================================
SELECT 
  -- Date and Product Identification
  pp.date,
  pp.product_id,
  pp.product_name,
  pp.product_category,
  pp.product_sku,
  
  -- Sales Performance (from Product Performance)
  pp.shopify_units_sold,
  pp.shopify_revenue,
  pp.shopify_orders,
  pp.shopify_avg_selling_price,
  
  -- Marketing Performance (from Product Performance)
  pp.facebook_spend,
  pp.facebook_attributed_revenue,
  pp.facebook_attributed_units,
  pp.klaviyo_attributed_revenue,
  pp.klaviyo_attributed_units,
  pp.total_marketing_spend,
  pp.total_attributed_revenue,
  pp.organic_revenue,
  pp.organic_units,
  
  -- CRITICAL: Real Inventory Data (from Inventory Management)
  COALESCE(inv.current_inventory_level, 0) as current_inventory_level,
  COALESCE(inv.available_inventory, 0) as available_inventory,
  COALESCE(inv.reserved_inventory, 0) as reserved_inventory,
  
  -- Business Rules (from Inventory Management)
  COALESCE(inv.reorder_point, 21) as reorder_point,
  COALESCE(inv.reorder_quantity, 30) as reorder_quantity,
  COALESCE(inv.max_stock_level, 75) as max_stock_level,
  COALESCE(inv.min_stock_level, 3) as min_stock_level,
  COALESCE(inv.lead_time_days, 42) as lead_time_days,
  COALESCE(inv.safety_stock_days, 14) as safety_stock_days,
  
  -- Cost and Profitability (from Inventory Management)
  COALESCE(inv.unit_cost_gbp, pp.shopify_revenue * 0.6) as unit_cost_gbp,  -- Fallback to 60% of revenue
  COALESCE(inv.selling_price_gbp, pp.shopify_avg_selling_price) as selling_price_gbp,
  COALESCE(inv.profit_margin_percentage, 40.0) as profit_margin_percentage,  -- Default 40% margin
  COALESCE(inv.profit_per_unit_gbp, pp.shopify_avg_selling_price * 0.4) as profit_per_unit_gbp,
  COALESCE(inv.inventory_value_gbp, 0.0) as inventory_value_gbp,
  
  -- Inventory Analytics (from Inventory Management)
  COALESCE(inv.days_of_stock_remaining, 999) as days_of_stock_remaining,
  COALESCE(inv.reorder_urgency, 'UNKNOWN') as reorder_urgency,
  COALESCE(inv.overstock_risk, 'UNKNOWN') as overstock_risk,
  COALESCE(inv.abc_classification, 'C') as abc_classification,
  COALESCE(inv.seasonality_factor, 1.0) as seasonality_factor,
  
  -- Supplier Information
  COALESCE(inv.supplier_name, 'Unknown') as supplier_name,
  inv.last_reorder_date,
  
  -- Data Quality Indicators
  CASE 
    WHEN inv.product_sku IS NOT NULL THEN 'inventory_data_available'
    ELSE 'inventory_data_missing'
  END as inventory_data_status,
  
  -- Calculated Fields for Stock GRIP
  CASE 
    WHEN COALESCE(inv.available_inventory, 0) <= COALESCE(inv.reorder_point, 21) THEN 'URGENT'
    WHEN COALESCE(inv.available_inventory, 0) <= (COALESCE(inv.reorder_point, 21) * 1.5) THEN 'HIGH'
    WHEN COALESCE(inv.available_inventory, 0) <= (COALESCE(inv.reorder_point, 21) * 2.0) THEN 'MEDIUM'
    ELSE 'LOW'
  END as stock_grip_priority,
  
  -- 6-Week Demand Calculation (for Stock GRIP)
  ROUND(
    (pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0), 
    1
  ) as six_week_demand_forecast,
  
  -- Recommended Order Calculation (for Stock GRIP)
  GREATEST(0, 
    ROUND(
      ((pp.shopify_units_sold / 30.0) * 42 * COALESCE(inv.seasonality_factor, 1.0)) +  -- 6-week demand
      ((pp.shopify_units_sold / 30.0) * COALESCE(inv.safety_stock_days, 14)) -         -- Safety stock
      COALESCE(inv.available_inventory, 0),                                            -- Current stock
      0
    )
  ) as recommended_order_quantity,
  
  CURRENT_TIMESTAMP() as export_timestamp

FROM product_performance_base pp
LEFT JOIN inventory_current inv ON pp.product_sku = inv.product_sku
ORDER BY 
  CASE 
    WHEN inv.reorder_urgency = 'URGENT' THEN 1
    WHEN inv.reorder_urgency = 'HIGH' THEN 2
    WHEN inv.reorder_urgency = 'MEDIUM' THEN 3
    ELSE 4
  END,
  pp.shopify_revenue DESC;
```

## Export Configuration

### File Name
`stock_grip_unified_product_inventory.csv`

### Update Schedule
- **Frequency**: Daily at 6 AM
- **Trigger**: After inventory sync from Shopify
- **Retention**: 30 days of historical data

### Key Fields for Stock GRIP
```
product_sku,                    -- Actual SKU (e.g., "1984-2025-137-05")
current_inventory_level,        -- Real stock on hand
available_inventory,            -- Available for sale
reorder_point,                  -- When to reorder
recommended_order_quantity,     -- How much to order
six_week_demand_forecast,       -- Expected 6-week sales
profit_margin_percentage,       -- Actual profit margin
stock_grip_priority,           -- URGENT/HIGH/MEDIUM/LOW
inventory_data_status          -- Data quality indicator
```

## Implementation Steps

### 1. Create Inventory Management Model
- Use the SQL from `inventory_management_model.sql`
- Connect to your Shopify inventory API
- Add your product cost/pricing data

### 2. Modify Product Performance Model
- Add the join logic above
- Include inventory fields in export
- Test with small dataset first

### 3. Update Stock GRIP Dashboard
- Modify to use `current_inventory_level` instead of estimates
- Use `recommended_order_quantity` from Weld calculation
- Add validation for `inventory_data_status`

## Expected Results

### Before (Current Issues):
- **159,595 units recommended** (massive overstock)
- **Estimated inventory** (unreliable)
- **24,501 records** (data duplication)

### After (With Real Inventory):
- **Realistic order quantities** (5-50 units typical)
- **Actual current stock** (no guessing)
- **~270 records** (9 products × 30 days)
- **Accurate 6-week optimization**

This approach will eliminate the overstock risk and provide your stakeholder with reliable, data-driven inventory decisions.