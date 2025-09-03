# Facebook Ads Data Model Specification for Weld

## Overview
This document specifies the Facebook Ads data model for implementation in Weld, designed to capture comprehensive advertising performance data for marketing attribution and ROI analysis in the Stock GRIP inventory optimization system.

## Model: Facebook Ads Performance Data

### Purpose
Captures detailed Facebook advertising performance metrics including campaign structure, audience targeting, conversion tracking, and cost analysis for marketing-driven inventory optimization.

### Data Source
- **Primary Source**: Facebook Ads Manager API / Facebook Business Manager
- **Export Format**: CSV
- **Update Frequency**: Daily (recommended) or Real-time
- **Data Retention**: 2 years
- **Attribution Window**: 7-day click, 1-day view (configurable)

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `date` | Date | Yes | Reporting date | YYYY-MM-DD format |
| `campaign_id` | String | Yes | Facebook campaign identifier | Numeric string, unique per campaign |
| `campaign_name` | String | Yes | Campaign name | Max 255 characters |
| `adset_id` | String | Yes | Ad set identifier | Numeric string |
| `adset_name` | String | Yes | Ad set name | Max 255 characters |
| `ad_id` | String | Yes | Individual ad identifier | Numeric string |
| `ad_name` | String | Yes | Ad creative name | Max 255 characters |
| `impressions` | Integer | No | Total ad impressions | Min: 0, Default: 0 |
| `clicks` | Integer | No | Total ad clicks | Min: 0, Default: 0 |
| `spend` | Float | No | Total ad spend | Currency: GBP, Min: 0.00 |
| `reach` | Integer | No | Unique users reached | Min: 0, Default: 0 |
| `frequency` | Float | No | Average impressions per user | Min: 0.0, Default: 0.0 |
| `purchases` | Integer | No | Conversion: Purchases | Min: 0, Default: 0 |
| `purchase_value` | Float | No | Revenue from purchases | Currency: GBP, Min: 0.00 |
| `add_to_cart` | Integer | No | Conversion: Add to Cart | Min: 0, Default: 0 |
| `view_content` | Integer | No | Conversion: View Content | Min: 0, Default: 0 |
| `initiate_checkout` | Integer | No | Conversion: Initiate Checkout | Min: 0, Default: 0 |
| `age_range` | String | No | Target age range | Format: "18-24", "25-34", etc. |
| `gender` | String | No | Target gender | Values: male, female, all |
| `country` | String | No | Target country | ISO 3166-1 alpha-2 code |
| `interests` | Text | No | Target interests (JSON) | JSON array of interest strings |
| `attributed_products` | Text | No | Products driven by ad (JSON) | JSON array of product objects |

### Calculated Fields (Weld Transformations)

```sql
-- Performance Metrics
CASE 
  WHEN impressions > 0 THEN (clicks::FLOAT / impressions::FLOAT) * 100 
  ELSE 0 
END as ctr_percentage,

CASE 
  WHEN clicks > 0 THEN spend / clicks 
  ELSE 0 
END as cpc_gbp,

CASE 
  WHEN impressions > 0 THEN (spend / impressions) * 1000 
  ELSE 0 
END as cpm_gbp,

CASE 
  WHEN spend > 0 THEN purchase_value / spend 
  ELSE 0 
END as roas_ratio,

-- Conversion Funnel Analysis
CASE 
  WHEN impressions > 0 THEN (view_content::FLOAT / impressions::FLOAT) * 100 
  ELSE 0 
END as view_content_rate,

CASE 
  WHEN view_content > 0 THEN (add_to_cart::FLOAT / view_content::FLOAT) * 100 
  ELSE 0 
END as add_to_cart_conversion_rate,

CASE 
  WHEN add_to_cart > 0 THEN (initiate_checkout::FLOAT / add_to_cart::FLOAT) * 100 
  ELSE 0 
END as checkout_conversion_rate,

CASE 
  WHEN initiate_checkout > 0 THEN (purchases::FLOAT / initiate_checkout::FLOAT) * 100 
  ELSE 0 
END as purchase_conversion_rate,

-- Campaign Performance Categories
CASE 
  WHEN roas_ratio >= 4.0 THEN 'high_performance'
  WHEN roas_ratio >= 2.0 THEN 'medium_performance'
  WHEN roas_ratio >= 1.0 THEN 'low_performance'
  WHEN roas_ratio > 0 THEN 'break_even'
  ELSE 'loss_making'
END as performance_category,

-- Audience Quality Indicators
CASE 
  WHEN ctr_percentage >= 2.0 THEN 'high_engagement'
  WHEN ctr_percentage >= 1.0 THEN 'medium_engagement'
  WHEN ctr_percentage >= 0.5 THEN 'low_engagement'
  ELSE 'poor_engagement'
END as engagement_quality,

-- Cost Efficiency Analysis
CASE 
  WHEN purchases > 0 THEN spend / purchases 
  ELSE NULL 
END as cost_per_acquisition_gbp,

-- Time-based Analysis
EXTRACT(DOW FROM date) as day_of_week,
EXTRACT(WEEK FROM date) as week_of_year,
EXTRACT(MONTH FROM date) as month_of_year
```

### Advanced Weld Transformations

#### 1. Campaign Performance Aggregation
```sql
-- Daily Campaign Summary
SELECT 
  date,
  campaign_id,
  campaign_name,
  SUM(spend) as total_spend_gbp,
  SUM(impressions) as total_impressions,
  SUM(clicks) as total_clicks,
  SUM(purchases) as total_purchases,
  SUM(purchase_value) as total_revenue_gbp,
  AVG(ctr_percentage) as avg_ctr,
  AVG(roas_ratio) as avg_roas
FROM facebook_ads_data
GROUP BY date, campaign_id, campaign_name
```

#### 2. Product Attribution Analysis
```sql
-- Extract product performance from attributed_products JSON
SELECT 
  date,
  campaign_id,
  JSON_EXTRACT_PATH_TEXT(attributed_products, 'product_id') as product_id,
  JSON_EXTRACT_PATH_TEXT(attributed_products, 'attributed_revenue') as product_revenue,
  JSON_EXTRACT_PATH_TEXT(attributed_products, 'attributed_units') as product_units,
  spend / NULLIF(JSON_ARRAY_LENGTH(attributed_products), 0) as allocated_spend
FROM facebook_ads_data
WHERE attributed_products IS NOT NULL
```

#### 3. Audience Performance Analysis
```sql
-- Audience segment performance
SELECT 
  age_range,
  gender,
  country,
  COUNT(*) as ad_count,
  SUM(spend) as total_spend,
  SUM(purchase_value) as total_revenue,
  AVG(roas_ratio) as avg_roas,
  AVG(ctr_percentage) as avg_ctr
FROM facebook_ads_data
WHERE spend > 0
GROUP BY age_range, gender, country
HAVING SUM(spend) > 100  -- Minimum spend threshold
ORDER BY avg_roas DESC
```

### Key Performance Indicators (KPIs)

#### Primary Metrics
1. **Return on Ad Spend (ROAS)**: `SUM(purchase_value) / SUM(spend)`
2. **Cost Per Acquisition (CPA)**: `SUM(spend) / SUM(purchases)`
3. **Click-Through Rate (CTR)**: `SUM(clicks) / SUM(impressions) * 100`
4. **Conversion Rate**: `SUM(purchases) / SUM(clicks) * 100`

#### Secondary Metrics
1. **Cost Per Click (CPC)**: `SUM(spend) / SUM(clicks)`
2. **Cost Per Mille (CPM)**: `SUM(spend) / SUM(impressions) * 1000`
3. **Frequency**: `SUM(impressions) / SUM(reach)`
4. **Reach Rate**: `SUM(reach) / target_audience_size`

### Data Quality Validation

```sql
-- Weld Data Quality Checks
SELECT 
  date,
  COUNT(*) as total_records,
  COUNT(CASE WHEN spend < 0 THEN 1 END) as negative_spend_records,
  COUNT(CASE WHEN impressions < clicks THEN 1 END) as invalid_ctr_records,
  COUNT(CASE WHEN purchase_value < 0 THEN 1 END) as negative_revenue_records,
  COUNT(CASE WHEN campaign_id IS NULL THEN 1 END) as missing_campaign_id,
  AVG(CASE WHEN roas_ratio > 10 THEN 1.0 ELSE 0.0 END) as high_roas_outlier_rate
FROM facebook_ads_data
GROUP BY date
HAVING negative_spend_records > 0 
    OR invalid_ctr_records > 0 
    OR negative_revenue_records > 0
    OR missing_campaign_id > 0
```

### Integration Specifications

#### Stock GRIP Integration Points
1. **Product Demand Signals**: Map `attributed_products` to inventory demand forecasting
2. **Marketing ROI**: Feed ROAS data into GP-EIMS optimization for marketing budget allocation
3. **Customer Acquisition Cost**: Integrate CPA into customer lifetime value calculations
4. **Seasonal Patterns**: Use time-series data for demand seasonality modeling

#### Join Keys for Weld
- **Primary Key**: `CONCAT(date, '_', ad_id)`
- **Campaign Grouping**: `campaign_id`
- **Product Attribution**: `JSON_EXTRACT(attributed_products, '$.product_id')`
- **Time Series**: `date`

### Export Configuration

#### File Naming Convention
- **Daily Export**: `facebook_ads_performance_YYYY-MM-DD.csv`
- **Campaign Export**: `facebook_campaigns_YYYY-MM-DD.csv`
- **Product Attribution**: `facebook_product_attribution_YYYY-MM-DD.csv`

#### CSV Format Specifications
- **Encoding**: UTF-8
- **Delimiter**: Comma (,)
- **Quote Character**: Double quote (")
- **Header Row**: Yes
- **Date Format**: YYYY-MM-DD
- **Decimal Places**: 2 for currency, 4 for rates
- **Null Values**: Empty string for optional fields

### Performance Optimization

#### Weld Processing Recommendations
1. **Partitioning**: Partition by `date` for time-series queries
2. **Indexing**: Create indexes on `campaign_id`, `date`, `ad_id`
3. **Aggregation**: Pre-calculate daily campaign summaries
4. **Memory Management**: Process in weekly batches for large accounts
5. **Incremental Loading**: Use `date` field for incremental updates

#### Query Optimization
```sql
-- Optimized daily aggregation query
WITH daily_performance AS (
  SELECT 
    date,
    campaign_id,
    SUM(spend) as daily_spend,
    SUM(purchase_value) as daily_revenue,
    SUM(purchases) as daily_purchases
  FROM facebook_ads_data
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY date, campaign_id
)
SELECT 
  campaign_id,
  AVG(daily_spend) as avg_daily_spend,
  AVG(daily_revenue) as avg_daily_revenue,
  AVG(daily_revenue / NULLIF(daily_spend, 0)) as avg_roas
FROM daily_performance
GROUP BY campaign_id
```

### Attribution Model Configuration

#### Multi-Touch Attribution Setup
```sql
-- Attribution weight calculation for multi-channel analysis
WITH attribution_weights AS (
  SELECT 
    date,
    campaign_id,
    purchase_value,
    CASE 
      WHEN first_touch_channel = 'facebook' THEN 0.4
      WHEN last_touch_channel = 'facebook' THEN 0.4
      ELSE 0.2  -- Assisted conversion
    END as attribution_weight
  FROM marketing_attribution
  WHERE facebook_campaign_id IS NOT NULL
)
SELECT 
  campaign_id,
  SUM(purchase_value * attribution_weight) as attributed_revenue,
  SUM(purchase_value) as total_revenue
FROM attribution_weights
GROUP BY campaign_id
```

### Monitoring and Alerting

#### Data Quality Alerts
- **Missing Data**: No records for previous day
- **Spend Anomalies**: Daily spend > 150% of 7-day average
- **Performance Drops**: ROAS < 50% of 30-day average
- **Data Completeness**: > 5% of records missing required fields

#### Business Intelligence Integration
- **Dashboard Refresh**: Every 4 hours
- **Report Generation**: Daily campaign performance summary
- **Anomaly Detection**: Automated alerts for performance outliers
- **Trend Analysis**: Weekly and monthly performance comparisons