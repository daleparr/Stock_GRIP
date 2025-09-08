-- =====================================================
-- INVENTORY MANAGEMENT MODEL FOR WELD
-- Standalone model for current inventory levels, reorder points, and profit margins
-- =====================================================

-- Replace 'your_shopify_inventory_table' with your actual Shopify inventory table name
-- Replace 'your_product_costs_table' with your product cost/pricing table name

WITH inventory_base AS (
  SELECT 
    -- Product Identification (must match Product Performance model)
    p.sku as product_sku,
    p.id as product_id,
    p.title as product_name,
    p.product_type as category,
    
    -- Current Inventory Status (from Shopify Inventory API)
    COALESCE(inv.available, 0) as current_inventory_level,
    COALESCE(inv.committed, 0) as reserved_inventory,
    COALESCE(inv.available, 0) - COALESCE(inv.committed, 0) as available_inventory,
    
    -- Cost and Pricing Data
    COALESCE(costs.unit_cost, 0.0) as unit_cost_gbp,
    COALESCE(p.price, 0.0) as selling_price_gbp,
    
    -- Supplier Information
    COALESCE(costs.supplier_name, 'Unknown') as supplier_name,
    costs.last_purchase_date as last_reorder_date,
    
    -- Product Metadata
    p.created_at as product_created_date,
    p.updated_at as last_updated
    
  FROM shopify_products p
  LEFT JOIN shopify_inventory_levels inv ON p.id = inv.product_id
  LEFT JOIN your_product_costs_table costs ON p.sku = costs.product_sku
  WHERE p.status = 'active'
    AND p.sku IS NOT NULL
),

-- Calculate business rules and performance metrics
inventory_enhanced AS (
  SELECT *,
    -- Profitability Calculations
    ROUND(((selling_price_gbp - unit_cost_gbp) / NULLIF(selling_price_gbp, 0)) * 100, 2) as profit_margin_percentage,
    ROUND(selling_price_gbp - unit_cost_gbp, 2) as profit_per_unit_gbp,
    ROUND(current_inventory_level * unit_cost_gbp, 2) as inventory_value_gbp,
    
    -- Business Rules (Customize these based on your business)
    CASE 
      WHEN category = 'apparel_tops' THEN 14      -- 2 weeks for fast-moving items
      WHEN category = 'apparel_bottoms' THEN 21   -- 3 weeks for medium-moving
      WHEN category = 'accessories' THEN 28       -- 4 weeks for slow-moving
      ELSE 21                                     -- Default 3 weeks
    END as reorder_point,
    
    CASE 
      WHEN category = 'apparel_tops' THEN 50      -- Standard reorder quantity
      WHEN category = 'apparel_bottoms' THEN 30
      WHEN category = 'accessories' THEN 20
      ELSE 30
    END as reorder_quantity,
    
    CASE 
      WHEN category = 'apparel_tops' THEN 100     -- Maximum stock level
      WHEN category = 'apparel_bottoms' THEN 75
      WHEN category = 'accessories' THEN 50
      ELSE 75
    END as max_stock_level,
    
    CASE 
      WHEN category = 'apparel_tops' THEN 5       -- Minimum stock level
      WHEN category = 'apparel_bottoms' THEN 3
      WHEN category = 'accessories' THEN 2
      ELSE 3
    END as min_stock_level,
    
    -- Fixed Business Parameters
    42 as lead_time_days,        -- 6 weeks as specified
    14 as safety_stock_days,     -- 2 weeks safety buffer
    
    -- Seasonality Factor (adjust by month)
    CASE 
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (11, 12, 1) THEN 1.3  -- Holiday season
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (6, 7, 8) THEN 1.1    -- Summer
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (9, 10) THEN 1.2       -- Back to school
      ELSE 1.0                                                          -- Normal
    END as seasonality_factor
    
  FROM inventory_base
),

-- Add performance analytics
inventory_with_analytics AS (
  SELECT *,
    -- Days of stock remaining (if you have sales data)
    CASE 
      WHEN average_daily_sales > 0 THEN 
        ROUND(available_inventory / average_daily_sales, 1)
      ELSE 999
    END as days_of_stock_remaining,
    
    -- Reorder urgency
    CASE 
      WHEN available_inventory <= reorder_point THEN 'URGENT'
      WHEN available_inventory <= (reorder_point * 1.5) THEN 'HIGH'
      WHEN available_inventory <= (reorder_point * 2.0) THEN 'MEDIUM'
      ELSE 'LOW'
    END as reorder_urgency,
    
    -- Overstock risk
    CASE 
      WHEN available_inventory > max_stock_level THEN 'HIGH'
      WHEN available_inventory > (max_stock_level * 0.8) THEN 'MEDIUM'
      ELSE 'LOW'
    END as overstock_risk,
    
    -- ABC Classification (if you have revenue data)
    CASE 
      WHEN monthly_revenue_rank <= 20 THEN 'A'    -- Top 20% by revenue
      WHEN monthly_revenue_rank <= 50 THEN 'B'    -- Next 30% by revenue
      ELSE 'C'                                    -- Bottom 50% by revenue
    END as abc_classification
    
  FROM inventory_enhanced
)

-- Final output
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
  days_of_stock_remaining,
  reorder_urgency,
  overstock_risk,
  seasonality_factor,
  abc_classification,
  last_updated
FROM inventory_with_analytics
ORDER BY reorder_urgency DESC, days_of_stock_remaining ASC;

-- =====================================================
-- EXPORT CONFIGURATION
-- =====================================================
-- File Name: inventory_management_current.csv
-- Update Frequency: Daily
-- Join Key: product_sku (matches Product Performance model)
-- =====================================================