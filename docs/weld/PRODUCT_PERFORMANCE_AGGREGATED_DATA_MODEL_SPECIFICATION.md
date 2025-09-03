# Product Performance Aggregated Data Model Specification for Weld

## Overview
This document specifies the unified product performance aggregation data model for implementation in Weld, designed to consolidate product metrics across Shopify sales, Facebook advertising, and Klaviyo email marketing for comprehensive product-level analytics and inventory optimization in the Stock GRIP system.

## Model: Product Performance Aggregated

### Purpose
Creates a unified, daily aggregated view of product performance across all marketing and sales channels to enable product-level ROI analysis, demand forecasting, and marketing-driven inventory optimization decisions.

### Data Source
- **Primary Sources**: Shopify Orders/Line Items, Facebook Ads, Klaviyo Campaigns, Marketing Attribution
- **Export Format**: CSV
- **Update Frequency**: Daily
- **Data Retention**: 2 years
- **Aggregation Level**: Product + Date

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `date` | Date | Yes | Aggregation date | YYYY-MM-DD format |
| `product_id` | String | Yes | Internal product identifier | Must exist in products table |
| `product_name` | String | No | Product name | Max 255 characters |
| `product_category` | String | No | Product category | Max 100 characters |
| `product_sku` | String | No | Stock keeping unit | Max 50 characters |
| `shopify_units_sold` | Integer | No | Units sold via Shopify | Min: 0, Default: 0 |
| `shopify_revenue` | Float | No | Shopify sales revenue | Currency: GBP, Min: 0.00 |
| `shopify_orders` | Integer | No | Number of orders containing product | Min: 0, Default: 0 |
| `shopify_avg_selling_price` | Float | No | Average selling price | Currency: GBP, Min: 0.00 |
| `facebook_spend` | Float | No | Facebook ad spend attributed | Currency: GBP, Min: 0.00 |
| `facebook_impressions` | Integer | No | Facebook ad impressions | Min: 0, Default: 0 |
| `facebook_clicks` | Integer | No | Facebook ad clicks | Min: 0, Default: 0 |
| `facebook_attributed_revenue` | Float | No | Facebook attributed revenue | Currency: GBP, Min: 0.00 |
| `facebook_attributed_units` | Integer | No | Facebook attributed units | Min: 0, Default: 0 |
| `klaviyo_emails_sent` | Integer | No | Emails featuring product | Min: 0, Default: 0 |
| `klaviyo_emails_opened` | Integer | No | Opens for emails featuring product | Min: 0, Default: 0 |
| `klaviyo_emails_clicked` | Integer | No | Clicks for emails featuring product | Min: 0, Default: 0 |
| `klaviyo_attributed_revenue` | Float | No | Email attributed revenue | Currency: GBP, Min: 0.00 |
| `klaviyo_attributed_units` | Integer | No | Email attributed units | Min: 0, Default: 0 |
| `total_marketing_spend` | Float | No | Total marketing spend | Currency: GBP, Min: 0.00 |
| `total_attributed_revenue` | Float | No | Total attributed revenue | Currency: GBP, Min: 0.00 |
| `total_attributed_units` | Integer | No | Total attributed units | Min: 0, Default: 0 |
| `organic_revenue` | Float | No | Non-attributed revenue | Currency: GBP, Min: 0.00 |
| `organic_units` | Integer | No | Non-attributed units | Min: 0, Default: 0 |
| `inventory_level` | Integer | No | Current inventory level | Min: 0 |
| `inventory_cost` | Float | No | Inventory holding cost | Currency: GBP, Min: 0.00 |
| `profit_margin` | Float | No | Product profit margin | Range: 0.0-1.0 |

### Calculated Performance Metrics (Weld)

```sql
-- Marketing Performance Calculations
CASE 
  WHEN total_marketing_spend > 0 THEN total_attributed_revenue / total_marketing_spend 
  ELSE NULL 
END as marketing_roas,

CASE 
  WHEN total_attributed_units > 0 THEN total_marketing_spend / total_attributed_units 
  ELSE NULL 
END as cost_per_acquisition_gbp,

CASE 
  WHEN facebook_spend > 0 THEN facebook_attributed_revenue / facebook_spend 
  ELSE NULL 
END as facebook_roas,

CASE 
  WHEN klaviyo_emails_sent > 0 THEN klaviyo_attributed_revenue / klaviyo_emails_sent 
  ELSE 0 
END as revenue_per_email_gbp,

-- Sales Performance Metrics
shopify_revenue + total_attributed_revenue as total_product_revenue,
shopify_units_sold + total_attributed_units as total_units_sold,

CASE 
  WHEN shopify_orders > 0 THEN shopify_units_sold::FLOAT / shopify_orders 
  ELSE 0 
END as units_per_order,

-- Channel Mix Analysis
CASE 
  WHEN total_product_revenue > 0 THEN 
    (shopify_revenue / total_product_revenue) * 100 
  ELSE 0 
END as organic_revenue_percentage,

CASE 
  WHEN total_product_revenue > 0 THEN 
    (facebook_attributed_revenue / total_product_revenue) * 100 
  ELSE 0 
END as facebook_revenue_percentage,

CASE 
  WHEN total_product_revenue > 0 THEN 
    (klaviyo_attributed_revenue / total_product_revenue) * 100 
  ELSE 0 
END as email_revenue_percentage,

-- Inventory Performance
CASE 
  WHEN inventory_level > 0 THEN total_units_sold::FLOAT / inventory_level 
  ELSE NULL 
END as inventory_turnover_rate,

CASE 
  WHEN total_units_sold > 0 THEN inventory_cost / total_units_sold 
  ELSE inventory_cost 
END as cost_per_unit_sold,

-- Profitability Analysis
(total_product_revenue * profit_margin) - total_marketing_spend as net_profit_gbp,

CASE 
  WHEN total_product_revenue > 0 THEN 
    ((total_product_revenue * profit_margin) - total_marketing_spend) / total_product_revenue 
  ELSE 0 
END as net_profit_margin,

-- Demand Velocity Indicators
total_units_sold as daily_demand_velocity,
shopify_orders as daily_order_frequency,

-- Performance Categories
CASE 
  WHEN marketing_roas >= 4.0 THEN 'high_performance'
  WHEN marketing_roas >= 2.0 THEN 'medium_performance'
  WHEN marketing_roas >= 1.0 THEN 'low_performance'
  WHEN marketing_roas > 0 THEN 'break_even'
  ELSE 'loss_making'
END as marketing_performance_category,

CASE 
  WHEN total_units_sold >= 10 THEN 'high_velocity'
  WHEN total_units_sold >= 5 THEN 'medium_velocity'
  WHEN total_units_sold >= 1 THEN 'low_velocity'
  ELSE 'no_sales'
END as sales_velocity_category
```

### Advanced Product Analytics

#### 1. Product Performance Ranking
```sql
-- Daily product performance ranking
WITH product_rankings AS (
  SELECT 
    date,
    product_id,
    product_name,
    total_product_revenue,
    total_units_sold,
    marketing_roas,
    net_profit_gbp,
    -- Revenue ranking
    ROW_NUMBER() OVER (PARTITION BY date ORDER BY total_product_revenue DESC) as revenue_rank,
    -- Units ranking
    ROW_NUMBER() OVER (PARTITION BY date ORDER BY total_units_sold DESC) as units_rank,
    -- ROAS ranking
    ROW_NUMBER() OVER (PARTITION BY date ORDER BY marketing_roas DESC NULLS LAST) as roas_rank,
    -- Profit ranking
    ROW_NUMBER() OVER (PARTITION BY date ORDER BY net_profit_gbp DESC) as profit_rank,
    -- Composite performance score
    (total_product_revenue * 0.3) + 
    (total_units_sold * shopify_avg_selling_price * 0.3) + 
    (COALESCE(marketing_roas, 0) * total_marketing_spend * 0.2) + 
    (net_profit_gbp * 0.2) as performance_score
  FROM product_performance_aggregated
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT 
  product_id,
  product_name,
  AVG(revenue_rank) as avg_revenue_rank,
  AVG(units_rank) as avg_units_rank,
  AVG(roas_rank) as avg_roas_rank,
  AVG(profit_rank) as avg_profit_rank,
  AVG(performance_score) as avg_performance_score,
  SUM(total_product_revenue) as total_30day_revenue,
  SUM(total_units_sold) as total_30day_units,
  AVG(marketing_roas) as avg_marketing_roas
FROM product_rankings
GROUP BY product_id, product_name
ORDER BY avg_performance_score DESC
LIMIT 50
```

#### 2. Channel Effectiveness by Product
```sql
-- Channel performance analysis by product
WITH channel_effectiveness AS (
  SELECT 
    product_id,
    product_name,
    product_category,
    -- Facebook channel metrics
    SUM(facebook_spend) as total_facebook_spend,
    SUM(facebook_attributed_revenue) as total_facebook_revenue,
    SUM(facebook_attributed_units) as total_facebook_units,
    AVG(facebook_roas) as avg_facebook_roas,
    
    -- Email channel metrics
    SUM(klaviyo_emails_sent) as total_emails_sent,
    SUM(klaviyo_attributed_revenue) as total_email_revenue,
    SUM(klaviyo_attributed_units) as total_email_units,
    AVG(revenue_per_email_gbp) as avg_revenue_per_email,
    
    -- Organic performance
    SUM(organic_revenue) as total_organic_revenue,
    SUM(organic_units) as total_organic_units,
    
    -- Overall metrics
    SUM(total_product_revenue) as total_revenue,
    SUM(total_units_sold) as total_units
  FROM product_performance_aggregated
  WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  GROUP BY product_id, product_name, product_category
)
SELECT 
  product_id,
  product_name,
  product_category,
  total_revenue,
  total_units,
  
  -- Channel revenue distribution
  ROUND((total_facebook_revenue / NULLIF(total_revenue, 0)) * 100, 2) as facebook_revenue_share,
  ROUND((total_email_revenue / NULLIF(total_revenue, 0)) * 100, 2) as email_revenue_share,
  ROUND((total_organic_revenue / NULLIF(total_revenue, 0)) * 100, 2) as organic_revenue_share,
  
  -- Channel efficiency
  ROUND(avg_facebook_roas, 2) as facebook_roas,
  ROUND(avg_revenue_per_email, 2) as email_efficiency,
  
  -- Best performing channel
  CASE 
    WHEN avg_facebook_roas >= 3.0 AND total_facebook_revenue > total_email_revenue THEN 'facebook'
    WHEN avg_revenue_per_email >= 0.5 AND total_email_revenue > total_facebook_revenue THEN 'email'
    WHEN total_organic_revenue > GREATEST(total_facebook_revenue, total_email_revenue) THEN 'organic'
    ELSE 'mixed'
  END as best_channel
FROM channel_effectiveness
WHERE total_revenue > 100  -- Minimum revenue threshold
ORDER BY total_revenue DESC
```

#### 3. Inventory Optimization Insights
```sql
-- Inventory optimization recommendations
WITH inventory_analysis AS (
  SELECT 
    product_id,
    product_name,
    -- Recent performance (last 30 days)
    AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days' THEN daily_demand_velocity ELSE NULL END) as recent_avg_daily_demand,
    AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days' THEN marketing_roas ELSE NULL END) as recent_avg_roas,
    AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days' THEN net_profit_margin ELSE NULL END) as recent_avg_profit_margin,
    
    -- Historical performance (30-90 days ago)
    AVG(CASE WHEN date BETWEEN CURRENT_DATE - INTERVAL '90 days' AND CURRENT_DATE - INTERVAL '30 days' 
             THEN daily_demand_velocity ELSE NULL END) as historical_avg_daily_demand,
    AVG(CASE WHEN date BETWEEN CURRENT_DATE - INTERVAL '90 days' AND CURRENT_DATE - INTERVAL '30 days' 
             THEN marketing_roas ELSE NULL END) as historical_avg_roas,
    
    -- Current inventory metrics
    MAX(CASE WHEN date = CURRENT_DATE - INTERVAL '1 day' THEN inventory_level ELSE NULL END) as current_inventory,
    MAX(CASE WHEN date = CURRENT_DATE - INTERVAL '1 day' THEN inventory_turnover_rate ELSE NULL END) as current_turnover_rate,
    
    -- Trend analysis
    STDDEV(daily_demand_velocity) as demand_volatility,
    COUNT(CASE WHEN daily_demand_velocity > 0 THEN 1 END) as days_with_sales
  FROM product_performance_aggregated
  WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  GROUP BY product_id, product_name
)
SELECT 
  product_id,
  product_name,
  current_inventory,
  recent_avg_daily_demand,
  historical_avg_daily_demand,
  demand_volatility,
  recent_avg_roas,
  recent_avg_profit_margin,
  
  -- Demand trend
  CASE 
    WHEN recent_avg_daily_demand > historical_avg_daily_demand * 1.2 THEN 'increasing'
    WHEN recent_avg_daily_demand < historical_avg_daily_demand * 0.8 THEN 'decreasing'
    ELSE 'stable'
  END as demand_trend,
  
  -- Inventory recommendation
  CASE 
    WHEN current_inventory / NULLIF(recent_avg_daily_demand, 0) < 7 AND recent_avg_roas > 2.0 THEN 'increase_stock'
    WHEN current_inventory / NULLIF(recent_avg_daily_demand, 0) > 30 AND recent_avg_roas < 1.5 THEN 'reduce_stock'
    WHEN demand_volatility > recent_avg_daily_demand * 0.5 THEN 'monitor_closely'
    ELSE 'maintain_current'
  END as inventory_recommendation,
  
  -- Days of inventory remaining
  ROUND(current_inventory / NULLIF(recent_avg_daily_demand, 0), 1) as days_of_inventory,
  
  -- Marketing recommendation
  CASE 
    WHEN recent_avg_roas > 3.0 AND recent_avg_daily_demand > 0 THEN 'increase_marketing'
    WHEN recent_avg_roas < 1.5 THEN 'reduce_marketing'
    WHEN recent_avg_roas BETWEEN 1.5 AND 3.0 THEN 'optimize_marketing'
    ELSE 'no_marketing_data'
  END as marketing_recommendation
FROM inventory_analysis
WHERE days_with_sales >= 5  -- Products with meaningful sales history
ORDER BY recent_avg_daily_demand DESC
```

### Key Performance Indicators (KPIs)

#### Product-Level KPIs
1. **Marketing ROAS**: `AVG(total_attributed_revenue / total_marketing_spend)`
2. **Revenue per Product**: `SUM(total_product_revenue) / COUNT(DISTINCT product_id)`
3. **Units Velocity**: `AVG(total_units_sold)`
4. **Profit Margin**: `AVG(net_profit_margin)`

#### Channel Performance KPIs
1. **Facebook Product ROAS**: `AVG(facebook_attributed_revenue / facebook_spend)`
2. **Email Revenue per Send**: `AVG(klaviyo_attributed_revenue / klaviyo_emails_sent)`
3. **Organic Conversion Rate**: `SUM(organic_units) / SUM(total_units_sold)`
4. **Channel Mix Efficiency**: `Weighted average ROAS by channel`

#### Inventory Optimization KPIs
1. **Inventory Turnover**: `AVG(inventory_turnover_rate)`
2. **Days of Inventory**: `AVG(inventory_level / daily_demand_velocity)`
3. **Stockout Risk**: `COUNT(products WHERE days_of_inventory < 7)`
4. **Overstock Risk**: `COUNT(products WHERE days_of_inventory > 60)`

### Data Quality Validation

```sql
-- Product performance data quality checks
WITH quality_metrics AS (
  SELECT 
    date,
    COUNT(*) as total_products,
    COUNT(CASE WHEN total_product_revenue < 0 THEN 1 END) as negative_revenue_products,
    COUNT(CASE WHEN total_units_sold < 0 THEN 1 END) as negative_units_products,
    COUNT(CASE WHEN marketing_roas > 50 THEN 1 END) as unrealistic_roas_products,
    COUNT(CASE WHEN inventory_level < 0 THEN 1 END) as negative_inventory_products,
    COUNT(CASE WHEN total_marketing_spend > total_attributed_revenue * 10 THEN 1 END) as high_spend_low_return,
    AVG(total_product_revenue) as avg_product_revenue,
    AVG(marketing_roas) as avg_marketing_roas,
    STDDEV(total_product_revenue) as revenue_std_dev
  FROM product_performance_aggregated
  GROUP BY date
)
SELECT 
  date,
  total_products,
  negative_revenue_products,
  negative_units_products,
  unrealistic_roas_products,
  negative_inventory_products,
  high_spend_low_return,
  ROUND(avg_product_revenue, 2) as avg_product_revenue,
  ROUND(avg_marketing_roas, 2) as avg_marketing_roas,
  ROUND(revenue_std_dev, 2) as revenue_volatility
FROM quality_metrics
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC
```

### Integration with Stock GRIP

#### Demand Forecasting Integration
```sql
-- Product demand signals for Stock GRIP optimization
SELECT 
  product_id,
  -- Recent demand patterns
  AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days' THEN daily_demand_velocity END) as recent_7day_demand,
  AVG(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days' THEN daily_demand_velocity END) as recent_30day_demand,
  
  -- Marketing influence on demand
  CORR(total_marketing_spend, daily_demand_velocity) as marketing_demand_correlation,
  AVG(marketing_roas) as avg_marketing_efficiency,
  
  -- Seasonality indicators
  AVG(CASE WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN daily_demand_velocity END) as weekend_demand,
  AVG(CASE WHEN EXTRACT(DOW FROM date) BETWEEN 1 AND 5 THEN daily_demand_velocity END) as weekday_demand,
  
  -- Inventory optimization inputs
  STDDEV(daily_demand_velocity) as demand_volatility,
  MAX(daily_demand_velocity) as peak_demand,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY daily_demand_velocity) as demand_95th_percentile,
  
  -- Profitability constraints
  AVG(net_profit_margin) as avg_profit_margin,
  MIN(net_profit_margin) as min_profit_margin
FROM product_performance_aggregated
WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  AND total_units_sold > 0
GROUP BY product_id
ORDER BY recent_30day_demand DESC
```

### Export Configuration

#### File Naming Convention
- **Daily Aggregation**: `product_performance_aggregated_YYYY-MM-DD.csv`
- **Weekly Summary**: `product_performance_weekly_YYYY-WW.csv`
- **Monthly Summary**: `product_performance_monthly_YYYY-MM.csv`

#### CSV Format Specifications
- **Encoding**: UTF-8
- **Delimiter**: Comma (,)
- **Quote Character**: Double quote (")
- **Header Row**: Yes
- **Date Format**: YYYY-MM-DD
- **Decimal Places**: 2 for currency, 4 for rates and ratios
- **Null Values**: Empty string for optional numeric fields

### Performance Optimization

#### Weld Processing Recommendations
1. **Partitioning**: Partition by `date` for time-series analysis
2. **Indexing**: Create indexes on `product_id`, `date`, `total_product_revenue`
3. **Aggregation**: Use materialized views for frequently accessed summaries
4. **Memory Management**: Process in daily batches with product-level parallelization
5. **Incremental Updates**: Use date-based incremental loading

#### Query Optimization
```sql
-- Optimized aggregation query with proper indexing
CREATE INDEX CONCURRENTLY idx_product_performance_product_date 
ON product_performance_aggregated (product_id, date);

CREATE INDEX CONCURRENTLY idx_product_performance_revenue 
ON product_performance_aggregated (total_product_revenue) 
WHERE total_product_revenue > 0;

CREATE INDEX CONCURRENTLY idx_product_performance_category_date 
ON product_performance_aggregated (product_category, date);
```

### Monitoring and Alerting

#### Data Quality Alerts
- **Missing Product Data**: > 5% of active products missing daily data
- **Revenue Anomalies**: Product revenue changes > 200% day-over-day
- **ROAS Outliers**: Products with ROAS > 20 or < 0
- **Inventory Inconsistencies**: Negative inventory levels or impossible turnover rates

#### Business Intelligence Integration
- **Product Performance Dashboard**: Real-time product rankings and trends
- **Inventory Optimization**: Automated reorder recommendations
- **Marketing ROI Analysis**: Channel effectiveness by product
- **Demand Forecasting**: ML-ready feature sets for Stock GRIP optimization

### Advanced Use Cases

#### 1. Product Portfolio Optimization
```sql
-- Product portfolio analysis for strategic decisions
WITH portfolio_analysis AS (
  SELECT 
    product_category,
    COUNT(DISTINCT product_id) as product_count,
    SUM(total_product_revenue) as category_revenue,
    AVG(marketing_roas) as avg_category_roas,
    AVG(net_profit_margin) as avg_category_margin,
    SUM(total_marketing_spend) as category_marketing_spend,
    STDDEV(total_product_revenue) as revenue_volatility
  FROM product_performance_aggregated
  WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  GROUP BY product_category
)
SELECT 
  product_category,
  product_count,
  category_revenue,
  ROUND(avg_category_roas, 2) as avg_roas,
  ROUND(avg_category_margin * 100, 2) as avg_margin_percentage,
  category_marketing_spend,
  ROUND(revenue_volatility, 2) as revenue_volatility,
  ROUND(category_revenue / SUM(category_revenue) OVER () * 100, 2) as revenue_share_percentage,
  -- Portfolio recommendation
  CASE 
    WHEN avg_category_roas > 3.0 AND avg_category_margin > 0.3 THEN 'expand'
    WHEN avg_category_roas < 1.5 OR avg_category_margin < 0.1 THEN 'reduce'
    WHEN revenue_volatility > category_revenue * 0.3 THEN 'stabilize'
    ELSE 'maintain'
  END as portfolio_recommendation
FROM portfolio_analysis
ORDER BY category_revenue DESC
```

#### 2. Seasonal Demand Patterns
```sql
-- Seasonal product performance analysis
SELECT 
  product_id,
  product_name,
  EXTRACT(MONTH FROM date) as month,
  EXTRACT(DOW FROM date) as day_of_week,
  AVG(daily_demand_velocity) as avg_demand,
  AVG(marketing_roas) as avg_roas,
  COUNT(*) as data_points
FROM product_performance_aggregated
WHERE date >= CURRENT_DATE - INTERVAL '365 days'
  AND total_units_sold > 0
GROUP BY product_id, product_name, EXTRACT(MONTH FROM date), EXTRACT(DOW FROM date)
ORDER BY product_id, month, day_of_week