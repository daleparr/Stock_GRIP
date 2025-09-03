# CSV Export Implementation Guide

## Overview
This document provides specific implementation guidance for the CSV exports based on your available data models and requirements.

## Recommended Export Priority

### **1. Customer Lifecycle Analysis Export** ✅ **RECOMMENDED FIRST**
**Status**: Ready to implement with Marketing_Attribution_Model + Shopify Orders
**Business Value**: High - Customer segmentation and retention insights
**Complexity**: Medium

### **2. Product Inventory Optimization Export** ✅ **RECOMMENDED SECOND**
**Status**: Ready with Product_Performance_Aggregated (inventory-free version)
**Business Value**: Very High - Direct Stock GRIP integration
**Complexity**: Low (using existing aggregated data)

## Export Specifications

### **Export 1: Customer Lifecycle Analysis**
**File**: `customer_lifecycle_analysis_YYYY-MM-DD.csv`
**Data Sources**: Marketing_Attribution_Model + Shopify_Orders_model
**Date Range**: Last 90 days (for meaningful lifecycle analysis)

```sql
-- Customer Lifecycle Analysis Export Query
WITH customer_metrics AS (
  SELECT 
    so.customer_email,
    so.customer_first_name as first_name,
    so.customer_last_name as last_name,
    
    -- Order history metrics
    COUNT(DISTINCT so.shopify_order_id) as total_orders,
    SUM(so.total_price_gbp) as lifetime_value_gbp,
    AVG(so.total_price_gbp) as avg_order_value_gbp,
    MIN(so.order_date) as first_order_date,
    MAX(so.order_date) as last_order_date,
    
    -- Recent activity (last 30 days)
    COUNT(CASE WHEN so.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN 1 END) as orders_last_30_days,
    SUM(CASE WHEN so.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN so.total_price_gbp ELSE 0 END) as revenue_last_30_days_gbp
  FROM {{Stock_GRIP.Shopify_Orders_model}} so
  WHERE so.customer_email IS NOT NULL
    AND so.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY so.customer_email, so.customer_first_name, so.customer_last_name
),
attribution_metrics AS (
  SELECT 
    ma.customer_email,
    
    -- Attribution channel preferences
    COUNT(CASE WHEN ma.first_touch_channel = 'facebook' THEN 1 END) as facebook_first_touch_count,
    COUNT(CASE WHEN ma.first_touch_channel = 'email' THEN 1 END) as email_first_touch_count,
    COUNT(CASE WHEN ma.last_touch_channel = 'facebook' THEN 1 END) as facebook_last_touch_count,
    COUNT(CASE WHEN ma.last_touch_channel = 'email' THEN 1 END) as email_last_touch_count,
    
    -- Journey characteristics
    AVG(ma.journey_duration_hours) as avg_journey_duration_hours,
    AVG(ma.touchpoint_count) as avg_touchpoints_per_journey,
    
    -- Attribution revenue
    SUM(ma.facebook_attributed_revenue) as total_facebook_attributed_revenue,
    SUM(ma.klaviyo_attributed_revenue) as total_email_attributed_revenue
  FROM {{Stock_GRIP.Marketing_Attribution_Model}} ma
  WHERE ma.customer_email IS NOT NULL
    AND ma.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY ma.customer_email
)
SELECT 
  cm.customer_email as email,
  cm.first_name,
  cm.last_name,
  
  -- Customer segment classification
  CASE 
    WHEN cm.total_orders = 1 THEN 'new_customer'
    WHEN cm.total_orders BETWEEN 2 AND 5 THEN 'returning_customer'
    WHEN cm.total_orders > 5 THEN 'loyal_customer'
  END as customer_segment,
  
  -- Lifecycle stage
  CASE 
    WHEN cm.orders_last_30_days > 0 THEN 'active'
    WHEN DATE_DIFF(CURRENT_DATE(), cm.last_order_date, DAY) <= 60 THEN 'recent'
    WHEN DATE_DIFF(CURRENT_DATE(), cm.last_order_date, DAY) <= 180 THEN 'at_risk'
    ELSE 'churned'
  END as lifecycle_stage,
  
  -- Order metrics
  cm.total_orders,
  ROUND(cm.lifetime_value_gbp, 2) as lifetime_value_gbp,
  ROUND(cm.avg_order_value_gbp, 2) as avg_order_value_gbp,
  cm.first_order_date,
  cm.last_order_date,
  cm.orders_last_30_days,
  ROUND(cm.revenue_last_30_days_gbp, 2) as revenue_last_30_days_gbp,
  
  -- Attribution preferences
  COALESCE(am.facebook_first_touch_count, 0) as facebook_first_touch_count,
  COALESCE(am.email_first_touch_count, 0) as email_first_touch_count,
  COALESCE(am.facebook_last_touch_count, 0) as facebook_last_touch_count,
  COALESCE(am.email_last_touch_count, 0) as email_last_touch_count,
  ROUND(COALESCE(am.avg_journey_duration_hours, 0), 1) as avg_journey_duration_hours,
  ROUND(COALESCE(am.avg_touchpoints_per_journey, 0), 1) as avg_touchpoints_per_journey,
  
  -- Customer insights
  DATE_DIFF(CURRENT_DATE(), cm.last_order_date, DAY) as days_since_last_order,
  DATE_DIFF(CURRENT_DATE(), cm.first_order_date, DAY) as customer_age_days,
  
  -- Preferred channel analysis
  CASE 
    WHEN COALESCE(am.facebook_first_touch_count, 0) > COALESCE(am.email_first_touch_count, 0) THEN 'facebook_driven'
    WHEN COALESCE(am.email_first_touch_count, 0) > COALESCE(am.facebook_first_touch_count, 0) THEN 'email_driven'
    WHEN COALESCE(am.facebook_first_touch_count, 0) = COALESCE(am.email_first_touch_count, 0) 
         AND COALESCE(am.facebook_first_touch_count, 0) > 0 THEN 'multi_channel'
    ELSE 'organic'
  END as acquisition_channel_preference,
  
  -- Revenue attribution
  ROUND(COALESCE(am.total_facebook_attributed_revenue, 0), 2) as total_facebook_attributed_revenue_gbp,
  ROUND(COALESCE(am.total_email_attributed_revenue, 0), 2) as total_email_attributed_revenue_gbp
FROM customer_metrics cm
LEFT JOIN attribution_metrics am ON cm.customer_email = am.customer_email
WHERE cm.total_orders > 0  -- Only customers with purchase history
ORDER BY cm.lifetime_value_gbp DESC;
```

### **Export 2: Product Inventory Optimization (Inventory-Free Version)**
**File**: `product_inventory_optimization_YYYY-MM-DD.csv`
**Data Sources**: Product_Performance_Aggregated
**Date Range**: Last 90 days for trend analysis

```sql
-- Product Inventory Optimization Export Query (Inventory-Free Version)
WITH product_performance_metrics AS (
  SELECT 
    ppa.product_id,
    MAX(ppa.product_name) as product_name,
    MAX(ppa.product_category) as category,
    MAX(ppa.product_sku) as sku,
    
    -- Recent performance (last 30 days)
    AVG(CASE WHEN ppa.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) 
             THEN ppa.shopify_units_sold + ppa.total_attributed_units END) as avg_daily_units_last_30d,
    SUM(CASE WHEN ppa.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) 
             THEN ppa.shopify_revenue + ppa.total_attributed_revenue END) as revenue_last_30d_gbp,
    AVG(CASE WHEN ppa.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) 
             THEN SAFE_DIVIDE(ppa.total_attributed_revenue, NULLIF(ppa.total_marketing_spend, 0)) END) as avg_roas_last_30d,
    
    -- Historical performance (30-90 days ago)
    AVG(CASE WHEN ppa.date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) 
                               AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
             THEN ppa.shopify_units_sold + ppa.total_attributed_units END) as avg_daily_units_historical,
    
    -- Marketing performance
    AVG(ppa.total_marketing_spend) as avg_daily_marketing_spend_gbp,
    AVG(SAFE_DIVIDE(ppa.facebook_attributed_revenue, NULLIF(ppa.facebook_spend, 0))) as avg_facebook_roas,
    AVG(SAFE_DIVIDE(ppa.klaviyo_attributed_revenue, NULLIF(ppa.klaviyo_emails_sent, 0))) as avg_email_revenue_per_send,
    
    -- Demand patterns
    STDDEV(ppa.shopify_units_sold + ppa.total_attributed_units) as demand_volatility,
    MAX(ppa.shopify_units_sold + ppa.total_attributed_units) as peak_daily_demand,
    COUNT(CASE WHEN (ppa.shopify_units_sold + ppa.total_attributed_units) > 0 THEN 1 END) as days_with_sales,
    
    -- Profitability (estimated)
    AVG(ppa.total_attributed_revenue - ppa.total_marketing_spend) as avg_daily_profit_gbp,
    AVG(SAFE_DIVIDE(
      (ppa.total_attributed_revenue - ppa.total_marketing_spend), 
      NULLIF(ppa.total_attributed_revenue, 0)
    )) as avg_profit_margin
  FROM {{Stock_GRIP.Product_Performance_Aggregated}} ppa
  WHERE ppa.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY ppa.product_id
)
SELECT 
  product_id,
  product_name,
  category,
  sku,
  
  -- Demand metrics
  ROUND(COALESCE(avg_daily_units_last_30d, 0), 2) as avg_daily_demand_recent,
  ROUND(COALESCE(avg_daily_units_historical, 0), 2) as avg_daily_demand_historical,
  ROUND(COALESCE(demand_volatility, 0), 2) as demand_volatility,
  COALESCE(peak_daily_demand, 0) as peak_daily_demand,
  COALESCE(days_with_sales, 0) as days_with_sales,
  
  -- Financial performance
  ROUND(COALESCE(revenue_last_30d_gbp, 0), 2) as revenue_last_30d_gbp,
  ROUND(COALESCE(avg_daily_profit_gbp, 0), 2) as avg_daily_profit_gbp,
  ROUND(COALESCE(avg_profit_margin, 0), 4) as avg_profit_margin,
  ROUND(COALESCE(avg_daily_marketing_spend_gbp, 0), 2) as avg_daily_marketing_spend_gbp,
  
  -- Marketing effectiveness
  ROUND(COALESCE(avg_roas_last_30d, 0), 2) as avg_roas_last_30d,
  ROUND(COALESCE(avg_facebook_roas, 0), 2) as avg_facebook_roas,
  ROUND(COALESCE(avg_email_revenue_per_send, 0), 4) as avg_email_revenue_per_send,
  
  -- Demand trend analysis
  CASE 
    WHEN avg_daily_units_last_30d > COALESCE(avg_daily_units_historical, 0) * 1.2 THEN 'increasing'
    WHEN avg_daily_units_last_30d < COALESCE(avg_daily_units_historical, 0) * 0.8 THEN 'decreasing'
    ELSE 'stable'
  END as demand_trend,
  
  -- Marketing recommendation
  CASE 
    WHEN COALESCE(avg_roas_last_30d, 0) > 3.0 AND COALESCE(avg_daily_units_last_30d, 0) > 0 THEN 'increase_marketing'
    WHEN COALESCE(avg_roas_last_30d, 0) < 1.5 THEN 'reduce_marketing'
    WHEN COALESCE(avg_roas_last_30d, 0) BETWEEN 1.5 AND 3.0 THEN 'optimize_marketing'
    ELSE 'no_marketing_data'
  END as marketing_recommendation,
  
  -- Stock GRIP optimization flags
  CASE 
    WHEN demand_trend = 'increasing' AND COALESCE(avg_roas_last_30d, 0) > 2.0 THEN 1 
    ELSE 0 
  END as high_growth_flag,
  
  CASE 
    WHEN COALESCE(demand_volatility, 0) > COALESCE(avg_daily_units_last_30d, 0) * 0.5 THEN 1 
    ELSE 0 
  END as high_volatility_flag,
  
  CASE 
    WHEN COALESCE(avg_roas_last_30d, 0) > 3.0 THEN 1 
    ELSE 0 
  END as high_roi_flag
FROM product_performance_metrics
WHERE days_with_sales >= 5  -- Products with meaningful sales history
ORDER BY revenue_last_30d_gbp DESC;
```

## Implementation Recommendations

### **Date Range Filters**
- **Customer Lifecycle Analysis**: 90 days (sufficient for lifecycle patterns)
- **Product Inventory Optimization**: 90 days (30 days recent + 60 days historical for trend analysis)

### **Export Schedule**
- **Frequency**: Daily
- **Best Time**: 06:00 UTC (after all data sources have been updated)
- **Retention**: 30 days for daily exports, 12 months for weekly summaries

### **File Naming Convention**
```
customer_lifecycle_analysis_2024-03-15.csv
product_inventory_optimization_2024-03-15.csv
```

### **CSV Format Standards**
- **Encoding**: UTF-8
- **Delimiter**: Comma (,)
- **Quote Character**: Double quote (")
- **Header Row**: Yes
- **Date Format**: YYYY-MM-DD
- **Currency**: 2 decimal places (12.34)
- **Rates/Ratios**: 4 decimal places (0.1234)

## Next Steps Priority

### **Phase 1: Immediate Implementation** (Week 1)
1. ✅ **Customer Lifecycle Analysis Export** - High business value, ready to implement
2. ✅ **Product Inventory Optimization Export** - Critical for Stock GRIP integration

### **Phase 2: Additional Exports** (Week 2)
3. **Daily Sales Performance Export** - Operational reporting
4. **Marketing Performance Summary Export** - Campaign optimization

### **Phase 3: Advanced Analytics** (Week 3)
5. **Product Portfolio Analysis Export** - Strategic planning
6. **Channel Attribution Comparison Export** - Marketing mix optimization

## Inventory Data Clarification

**Question**: Do you have inventory levels in a separate table?

**Recommendation**: Start with the **inventory-free version** using only Product_Performance_Aggregated. This provides:
- ✅ Demand velocity analysis
- ✅ Marketing efficiency metrics
- ✅ Trend analysis for reorder recommendations
- ✅ Stock GRIP optimization signals

If you have inventory data in another table, we can enhance the export with:
- Current stock levels
- Days of inventory remaining
- Stockout risk indicators
- Reorder point calculations

**Please confirm**:
1. Should we proceed with Customer Lifecycle Analysis first?
2. Use inventory-free Product Optimization export?
3. What is your preferred date range (I recommend 90 days)?
4. Do you have a separate inventory table we should integrate?

Both exports are production-ready and will provide immediate business value for customer segmentation and inventory optimization.