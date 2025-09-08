# Inventory Management Data Model Specification for Weld

## Overview
This document specifies a standalone inventory management data model for implementation in Weld, designed to provide real-time inventory levels, reorder points, and profit margins that will be joined with the Product Performance Aggregated model for accurate Stock GRIP inventory optimization.

## Model: Inventory Management

### Purpose
Creates a comprehensive inventory control dataset that provides actual stock levels, business rules, and profitability data required for accurate 6-week lead time inventory optimization and reorder decision-making.

### Data Sources
- **Primary**: Shopify Inventory API
- **Secondary**: Manual inventory management system
- **Profit Data**: Product cost/pricing tables
- **Business Rules**: Inventory management policies

### Export Format
- **Format**: CSV
- **Update Frequency**: Daily (or real-time if possible)
- **Data Retention**: Current state + 90 days history
- **Aggregation Level**: Product SKU (one record per SKU)

## Schema Definition

| Field Name | Data Type | Required | Description | Business Rules |
|------------|-----------|----------|-------------|----------------|
| `product_sku` | String | Yes | Stock keeping unit identifier | Must match Product Performance SKU |
| `product_id` | String | Yes | Internal product identifier | Must match Shopify product ID |
| `product_name` | String | Yes | Product name | For validation/reference |
| `current_inventory_level` | Integer | Yes | Current stock on hand | Min: 0, Real-time if possible |
| `reserved_inventory` | Integer | No | Stock allocated to orders | Min: 0, Default: 0 |
| `available_inventory` | Integer | Yes | Available for sale | current_inventory - reserved |
| `reorder_point` | Integer | Yes | When to trigger reorder | Business rule based |
| `reorder_quantity` | Integer | Yes | Standard reorder amount | Business rule based |
| `max_stock_level` | Integer | Yes | Maximum stock to hold | Prevent overstock |
| `min_stock_level` | Integer | Yes | Minimum stock to maintain | Safety stock level |
| `lead_time_days` | Integer | Yes | Supplier lead time | 6 weeks = 42 days default |
| `safety_stock_days` | Integer | Yes | Safety stock in days | Business rule: 7-14 days |
| `unit_cost_gbp` | Float | Yes | Cost per unit | Currency: GBP |
| `selling_price_gbp` | Float | Yes | Current selling price | Currency: GBP |
| `profit_margin_percentage` | Float | Yes | Profit margin % | (selling_price - unit_cost) / selling_price * 100 |
| `profit_per_unit_gbp` | Float | Yes | Profit per unit | selling_price - unit_cost |
| `inventory_value_gbp` | Float | Yes | Total inventory value | current_inventory * unit_cost |
| `category` | String | No | Product category | For grouping analysis |
| `supplier_name` | String | No | Primary supplier | For lead time analysis |
| `last_reorder_date` | Date | No | Last reorder date | Track reorder frequency |
| `last_stockout_date` | Date | No | Last stockout date | Risk analysis |
| `average_monthly_sales` | Float | No | 3-month average sales | For demand planning |
| `sales_velocity_trend` | String | No | Trend direction | 'increasing', 'stable', 'decreasing' |
| `seasonality_factor` | Float | No | Seasonal adjustment | 0.5-2.0, Default: 1.0 |
| `abc_classification` | String | No | ABC analysis category | 'A', 'B', 'C' based on revenue |
| `last_updated` | Timestamp | Yes | Data freshness | When record was last updated |

## SQL Implementation for Weld

### Base Inventory Model
```sql
-- Inventory_Management_Model
-- Connect to your inventory management system or Shopify Inventory API

WITH inventory_base AS (
  SELECT 
    -- Product Identification
    product_sku,
    product_id,
    product_name,
    product_category as category,
    
    -- Current Inventory Status
    current_inventory_quantity as current_inventory_level,
    reserved_quantity as reserved_inventory,
    (current_inventory_quantity - COALESCE(reserved_quantity, 0)) as available_inventory,
    
    -- Business Rules (Configure these based on your business)
    CASE 
      WHEN product_category = 'apparel_tops' THEN 14  -- 2 weeks for fast-moving
      WHEN product_category = 'apparel_bottoms' THEN 21  -- 3 weeks for slower-moving
      WHEN product_category = 'other' THEN 28  -- 4 weeks for accessories
      ELSE 21
    END as reorder_point,
    
    CASE 
      WHEN product_category = 'apparel_tops' THEN 50  -- Standard reorder qty
      WHEN product_category = 'apparel_bottoms' THEN 30
      WHEN product_category = 'other' THEN 20
      ELSE 30
    END as reorder_quantity,
    
    CASE 
      WHEN product_category = 'apparel_tops' THEN 100  -- Max stock
      WHEN product_category = 'apparel_bottoms' THEN 75
      WHEN product_category = 'other' THEN 50
      ELSE 75
    END as max_stock_level,
    
    CASE 
      WHEN product_category = 'apparel_tops' THEN 5  -- Min stock
      WHEN product_category = 'apparel_bottoms' THEN 3
      WHEN product_category = 'other' THEN 2
      ELSE 3
    END as min_stock_level,
    
    -- Lead Time and Safety Stock
    42 as lead_time_days,  -- 6 weeks as specified
    14 as safety_stock_days,  -- 2 weeks safety buffer
    
    -- Cost and Pricing
    unit_cost as unit_cost_gbp,
    selling_price as selling_price_gbp,
    
    -- Calculated Profitability
    ROUND(((selling_price - unit_cost) / selling_price) * 100, 2) as profit_margin_percentage,
    ROUND(selling_price - unit_cost, 2) as profit_per_unit_gbp,
    ROUND(current_inventory_quantity * unit_cost, 2) as inventory_value_gbp,
    
    -- Supplier Information
    primary_supplier as supplier_name,
    last_purchase_order_date as last_reorder_date,
    last_stockout_date,
    
    -- Performance Metrics (from sales history)
    average_monthly_sales_quantity as average_monthly_sales,
    
    CASE 
      WHEN sales_trend_30_days > 1.1 THEN 'increasing'
      WHEN sales_trend_30_days < 0.9 THEN 'decreasing'
      ELSE 'stable'
    END as sales_velocity_trend,
    
    -- Seasonality (configure based on your business)
    CASE 
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (11, 12, 1) THEN 1.3  -- Winter boost
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (6, 7, 8) THEN 1.1   -- Summer boost
      ELSE 1.0
    END as seasonality_factor,
    
    -- ABC Classification based on revenue
    CASE 
      WHEN revenue_rank_percentile >= 80 THEN 'A'  -- Top 20% revenue
      WHEN revenue_rank_percentile >= 50 THEN 'B'  -- Middle 30% revenue
      ELSE 'C'  -- Bottom 50% revenue
    END as abc_classification,
    
    CURRENT_TIMESTAMP() as last_updated
    
  FROM your_inventory_system_table  -- Replace with actual table name
  WHERE is_active = true
    AND product_sku IS NOT NULL
),

-- Add calculated fields
inventory_enhanced AS (
  SELECT *,
    -- Days of stock remaining
    CASE 
      WHEN average_monthly_sales > 0 THEN 
        ROUND(available_inventory / (average_monthly_sales / 30.0), 1)
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
    END as overstock_risk
    
  FROM inventory_base
)

SELECT * FROM inventory_enhanced
ORDER BY reorder_urgency DESC, days_of_stock_remaining ASC
```

## Join Strategy with Product Performance

### In your Product Performance Aggregated model, add:
```sql
-- Join with Inventory Management
LEFT JOIN Inventory_Management_Model inv 
  ON product_performance.product_sku = inv.product_sku

-- Add inventory fields to your export
inv.current_inventory_level,
inv.available_inventory,
inv.reorder_point,
inv.max_stock_level,
inv.profit_margin_percentage,
inv.days_of_stock_remaining,
inv.reorder_urgency,
inv.overstock_risk
```

## Expected Output Schema

Your final joined CSV should include:
```
product_sku, product_name, shopify_units_sold, shopify_revenue,
current_inventory_level, available_inventory, reorder_point, 
max_stock_level, profit_margin_percentage, days_of_stock_remaining,
reorder_urgency, overstock_risk, unit_cost_gbp, selling_price_gbp
```

This will provide the Stock GRIP system with **real inventory data** instead of estimates, eliminating the 159,595 unit overstock risk and enabling accurate 6-week lead time optimization.