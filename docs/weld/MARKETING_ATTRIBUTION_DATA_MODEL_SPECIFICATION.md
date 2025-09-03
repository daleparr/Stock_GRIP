# Marketing Attribution Data Model Specification for Weld

## Overview
This document specifies the unified marketing attribution data model for implementation in Weld, designed to capture multi-touch customer journeys across Shopify, Facebook, and Klaviyo channels for comprehensive marketing ROI analysis and attribution-driven inventory optimization in the Stock GRIP system.

## Model: Integrated Marketing Attribution

### Purpose
Creates a unified view of customer touchpoints across all marketing channels to enable accurate attribution modeling, customer journey analysis, and marketing-driven demand forecasting for inventory optimization.

### Data Source
- **Primary Sources**: Shopify Orders, Facebook Ads, Klaviyo Campaigns
- **Export Format**: CSV
- **Update Frequency**: Daily
- **Data Retention**: 2 years
- **Attribution Models**: First-touch, Last-touch, Multi-touch, Time-decay

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `date` | Date | Yes | Attribution date | YYYY-MM-DD format |
| `shopify_order_id` | String | No | Associated Shopify order | Must exist in shopify_orders |
| `customer_email` | String | No | Customer identifier | Valid email format |
| `customer_id` | String | No | Unified customer ID | Cross-platform identifier |
| `first_touch_channel` | String | No | First interaction channel | Values: facebook, email, organic, direct, referral |
| `first_touch_campaign` | String | No | First touch campaign name | Max 255 characters |
| `first_touch_timestamp` | DateTime | No | First interaction time | ISO 8601 format |
| `last_touch_channel` | String | No | Last interaction channel | Values: facebook, email, organic, direct, referral |
| `last_touch_campaign` | String | No | Last touch campaign name | Max 255 characters |
| `last_touch_timestamp` | DateTime | No | Last interaction time | ISO 8601 format |
| `facebook_campaign_id` | String | No | Facebook campaign ID | Must exist in facebook_ads_data |
| `facebook_attribution_window` | String | No | FB attribution window | Values: 1d_view, 7d_click, 28d_click |
| `facebook_attributed_revenue` | Float | No | Facebook attributed revenue | Currency: GBP, Min: 0.00 |
| `klaviyo_campaign_id` | String | No | Klaviyo campaign ID | Must exist in klaviyo_email_data |
| `klaviyo_flow_id` | String | No | Klaviyo flow ID | Must exist in klaviyo_email_data |
| `klaviyo_attributed_revenue` | Float | No | Email attributed revenue | Currency: GBP, Min: 0.00 |
| `total_attributed_revenue` | Float | Yes | Total order revenue | Currency: GBP, Min: 0.00 |
| `attribution_model` | String | Yes | Attribution model used | Values: first_touch, last_touch, linear, time_decay |
| `attribution_weight` | Float | No | Attribution weight (0-1) | Range: 0.0-1.0, Default: 1.0 |
| `touchpoint_count` | Integer | No | Total touchpoints in journey | Min: 1 |
| `journey_duration_hours` | Integer | No | Journey length in hours | Min: 0 |
| `touchpoint_sequence` | Text | No | Journey sequence (JSON) | JSON array of touchpoint objects |
| `conversion_type` | String | No | Type of conversion | Values: purchase, signup, add_to_cart |
| `device_type` | String | No | Primary device used | Values: desktop, mobile, tablet |
| `traffic_source` | String | No | Original traffic source | Values: paid, organic, direct, referral |

### Multi-Touch Attribution Logic (Weld)

```sql
-- Time-Decay Attribution Model
WITH customer_journeys AS (
  SELECT 
    customer_email,
    shopify_order_id,
    total_attributed_revenue,
    touchpoint_sequence,
    journey_duration_hours,
    JSON_ARRAY_LENGTH(touchpoint_sequence) as touchpoint_count
  FROM marketing_attribution
  WHERE touchpoint_sequence IS NOT NULL
),
touchpoint_weights AS (
  SELECT 
    customer_email,
    shopify_order_id,
    total_attributed_revenue,
    touchpoint_count,
    -- Time-decay attribution: more recent touchpoints get higher weight
    CASE 
      WHEN touchpoint_count = 1 THEN 1.0
      WHEN touchpoint_count = 2 THEN 
        CASE WHEN touchpoint_position = 1 THEN 0.3 ELSE 0.7 END
      WHEN touchpoint_count = 3 THEN 
        CASE 
          WHEN touchpoint_position = 1 THEN 0.2 
          WHEN touchpoint_position = 2 THEN 0.3 
          ELSE 0.5 
        END
      ELSE 
        -- For longer journeys, exponential decay
        POWER(2, touchpoint_position - touchpoint_count) / 
        (POWER(2, 1 - touchpoint_count) + POWER(2, 2 - touchpoint_count) + ... + 1)
    END as attribution_weight,
    JSON_EXTRACT_PATH_TEXT(touchpoint_sequence, CONCAT('$[', touchpoint_position - 1, '].channel')) as channel,
    JSON_EXTRACT_PATH_TEXT(touchpoint_sequence, CONCAT('$[', touchpoint_position - 1, '].campaign_id')) as campaign_id,
    JSON_EXTRACT_PATH_TEXT(touchpoint_sequence, CONCAT('$[', touchpoint_position - 1, '].timestamp')) as touchpoint_timestamp
  FROM customer_journeys,
       LATERAL (SELECT generate_series(1, touchpoint_count) as touchpoint_position)
)
SELECT 
  channel,
  campaign_id,
  COUNT(DISTINCT customer_email) as attributed_customers,
  SUM(total_attributed_revenue * attribution_weight) as weighted_attributed_revenue,
  AVG(attribution_weight) as avg_attribution_weight,
  SUM(total_attributed_revenue) as total_revenue_influenced
FROM touchpoint_weights
GROUP BY channel, campaign_id
ORDER BY weighted_attributed_revenue DESC
```

### Advanced Attribution Analysis

#### 1. Channel Performance Comparison
```sql
-- Cross-channel attribution analysis
WITH channel_attribution AS (
  SELECT 
    first_touch_channel,
    last_touch_channel,
    COUNT(*) as conversion_count,
    SUM(total_attributed_revenue) as total_revenue,
    AVG(journey_duration_hours) as avg_journey_duration,
    AVG(touchpoint_count) as avg_touchpoints
  FROM marketing_attribution
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    AND total_attributed_revenue > 0
  GROUP BY first_touch_channel, last_touch_channel
)
SELECT 
  first_touch_channel,
  last_touch_channel,
  conversion_count,
  ROUND(total_revenue, 2) as total_revenue_gbp,
  ROUND(total_revenue / conversion_count, 2) as revenue_per_conversion,
  ROUND(avg_journey_duration, 1) as avg_journey_hours,
  ROUND(avg_touchpoints, 1) as avg_touchpoints,
  -- Channel combination effectiveness
  CASE 
    WHEN first_touch_channel = last_touch_channel THEN 'single_channel'
    WHEN first_touch_channel = 'facebook' AND last_touch_channel = 'email' THEN 'facebook_to_email'
    WHEN first_touch_channel = 'email' AND last_touch_channel = 'facebook' THEN 'email_to_facebook'
    ELSE 'multi_channel'
  END as journey_type
FROM channel_attribution
ORDER BY total_revenue DESC
```

#### 2. Customer Journey Mapping
```sql
-- Detailed customer journey analysis
WITH journey_analysis AS (
  SELECT 
    customer_email,
    shopify_order_id,
    total_attributed_revenue,
    touchpoint_count,
    journey_duration_hours,
    -- Extract journey pattern
    ARRAY_TO_STRING(
      ARRAY(
        SELECT JSON_EXTRACT_PATH_TEXT(touchpoint_sequence, CONCAT('$[', i, '].channel'))
        FROM generate_series(0, JSON_ARRAY_LENGTH(touchpoint_sequence) - 1) as i
      ), 
      ' -> '
    ) as journey_pattern,
    -- Calculate journey velocity
    CASE 
      WHEN journey_duration_hours > 0 THEN touchpoint_count::FLOAT / journey_duration_hours
      ELSE NULL 
    END as journey_velocity
  FROM marketing_attribution
  WHERE touchpoint_sequence IS NOT NULL
    AND date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT 
  journey_pattern,
  COUNT(*) as journey_frequency,
  AVG(total_attributed_revenue) as avg_revenue,
  AVG(touchpoint_count) as avg_touchpoints,
  AVG(journey_duration_hours) as avg_duration_hours,
  AVG(journey_velocity) as avg_velocity,
  SUM(total_attributed_revenue) as total_revenue
FROM journey_analysis
GROUP BY journey_pattern
HAVING COUNT(*) >= 5  -- Minimum frequency threshold
ORDER BY total_revenue DESC
LIMIT 20
```

#### 3. Attribution Model Comparison
```sql
-- Compare different attribution models
WITH attribution_comparison AS (
  SELECT 
    shopify_order_id,
    customer_email,
    total_attributed_revenue,
    
    -- First-touch attribution
    CASE 
      WHEN first_touch_channel = 'facebook' THEN total_attributed_revenue 
      ELSE 0 
    END as first_touch_facebook_revenue,
    CASE 
      WHEN first_touch_channel = 'email' THEN total_attributed_revenue 
      ELSE 0 
    END as first_touch_email_revenue,
    
    -- Last-touch attribution
    CASE 
      WHEN last_touch_channel = 'facebook' THEN total_attributed_revenue 
      ELSE 0 
    END as last_touch_facebook_revenue,
    CASE 
      WHEN last_touch_channel = 'email' THEN total_attributed_revenue 
      ELSE 0 
    END as last_touch_email_revenue,
    
    -- Linear attribution (equal weight to all touchpoints)
    facebook_attributed_revenue as linear_facebook_revenue,
    klaviyo_attributed_revenue as linear_email_revenue
    
  FROM marketing_attribution
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT 
  'first_touch' as attribution_model,
  SUM(first_touch_facebook_revenue) as facebook_attributed_revenue,
  SUM(first_touch_email_revenue) as email_attributed_revenue,
  SUM(first_touch_facebook_revenue + first_touch_email_revenue) as total_attributed_revenue

UNION ALL

SELECT 
  'last_touch' as attribution_model,
  SUM(last_touch_facebook_revenue) as facebook_attributed_revenue,
  SUM(last_touch_email_revenue) as email_attributed_revenue,
  SUM(last_touch_facebook_revenue + last_touch_email_revenue) as total_attributed_revenue

UNION ALL

SELECT 
  'linear' as attribution_model,
  SUM(linear_facebook_revenue) as facebook_attributed_revenue,
  SUM(linear_email_revenue) as email_attributed_revenue,
  SUM(linear_facebook_revenue + linear_email_revenue) as total_attributed_revenue
```

### Key Performance Indicators (KPIs)

#### Attribution Metrics
1. **Channel Attribution Revenue**: `SUM(attributed_revenue) GROUP BY channel`
2. **Attribution Accuracy**: `SUM(attributed_revenue) / SUM(total_order_revenue)`
3. **Journey Complexity**: `AVG(touchpoint_count)`
4. **Time to Conversion**: `AVG(journey_duration_hours)`

#### Cross-Channel Metrics
1. **Channel Assist Rate**: `COUNT(multi_touch_journeys) / COUNT(total_journeys)`
2. **Channel Conversion Rate**: `COUNT(conversions) / COUNT(touchpoints) BY channel`
3. **Revenue per Touchpoint**: `SUM(attributed_revenue) / SUM(touchpoint_count)`
4. **Customer Journey Value**: `AVG(total_attributed_revenue) BY journey_pattern`

### Data Quality Validation

```sql
-- Attribution data quality checks
WITH quality_checks AS (
  SELECT 
    date,
    COUNT(*) as total_attributions,
    COUNT(CASE WHEN customer_email IS NULL THEN 1 END) as missing_customer_email,
    COUNT(CASE WHEN total_attributed_revenue <= 0 THEN 1 END) as zero_revenue_attributions,
    COUNT(CASE WHEN attribution_weight > 1.0 THEN 1 END) as invalid_attribution_weights,
    COUNT(CASE WHEN first_touch_timestamp > last_touch_timestamp THEN 1 END) as invalid_timestamp_sequence,
    COUNT(CASE WHEN touchpoint_count = 0 THEN 1 END) as zero_touchpoint_journeys,
    AVG(journey_duration_hours) as avg_journey_duration,
    COUNT(CASE WHEN journey_duration_hours > 24 * 30 THEN 1 END) as long_journey_outliers
  FROM marketing_attribution
  GROUP BY date
)
SELECT 
  date,
  total_attributions,
  ROUND((missing_customer_email::FLOAT / total_attributions) * 100, 2) as missing_email_percentage,
  ROUND((zero_revenue_attributions::FLOAT / total_attributions) * 100, 2) as zero_revenue_percentage,
  invalid_attribution_weights,
  invalid_timestamp_sequence,
  zero_touchpoint_journeys,
  ROUND(avg_journey_duration, 1) as avg_journey_hours,
  long_journey_outliers
FROM quality_checks
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC
```

### Integration with Stock GRIP

#### Demand Forecasting Integration
```sql
-- Attribution-driven demand signals
WITH product_attribution AS (
  SELECT 
    DATE_TRUNC('day', date) as forecast_date,
    JSON_EXTRACT_PATH_TEXT(touchpoint_sequence, '$.product_id') as product_id,
    first_touch_channel,
    last_touch_channel,
    SUM(total_attributed_revenue) as attributed_revenue,
    COUNT(*) as attribution_events,
    AVG(journey_duration_hours) as avg_journey_duration
  FROM marketing_attribution
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    AND touchpoint_sequence IS NOT NULL
  GROUP BY forecast_date, product_id, first_touch_channel, last_touch_channel
)
SELECT 
  product_id,
  first_touch_channel,
  last_touch_channel,
  SUM(attributed_revenue) as total_attributed_revenue,
  SUM(attribution_events) as total_attribution_events,
  AVG(avg_journey_duration) as avg_customer_journey_hours,
  -- Demand velocity indicator
  SUM(attribution_events) / 30.0 as daily_attribution_rate,
  -- Channel effectiveness score
  SUM(attributed_revenue) / SUM(attribution_events) as revenue_per_attribution
FROM product_attribution
GROUP BY product_id, first_touch_channel, last_touch_channel
ORDER BY total_attributed_revenue DESC
```

### Export Configuration

#### File Naming Convention
- **Daily Attribution**: `marketing_attribution_YYYY-MM-DD.csv`
- **Journey Analysis**: `customer_journeys_YYYY-MM-DD.csv`
- **Channel Performance**: `channel_attribution_YYYY-MM-DD.csv`

#### CSV Format Specifications
- **Encoding**: UTF-8
- **Delimiter**: Comma (,)
- **Quote Character**: Double quote (")
- **Header Row**: Yes
- **Date Format**: YYYY-MM-DD
- **DateTime Format**: YYYY-MM-DDTHH:MM:SSZ
- **Decimal Places**: 2 for currency, 4 for weights
- **JSON Fields**: Properly escaped JSON strings

### Performance Optimization

#### Weld Processing Recommendations
1. **Partitioning**: Partition by `date` for time-series analysis
2. **Indexing**: Create indexes on `customer_email`, `shopify_order_id`, `date`
3. **JSON Processing**: Use efficient JSON extraction functions
4. **Aggregation**: Pre-calculate channel attribution summaries
5. **Memory Management**: Process attribution data in daily batches

#### Query Optimization
```sql
-- Optimized attribution query with proper indexing
CREATE INDEX CONCURRENTLY idx_marketing_attribution_customer_date 
ON marketing_attribution (customer_email, date);

CREATE INDEX CONCURRENTLY idx_marketing_attribution_channels 
ON marketing_attribution (first_touch_channel, last_touch_channel);

CREATE INDEX CONCURRENTLY idx_marketing_attribution_revenue 
ON marketing_attribution (total_attributed_revenue) 
WHERE total_attributed_revenue > 0;
```

### Monitoring and Alerting

#### Data Quality Alerts
- **Attribution Gaps**: > 10% of orders without attribution data
- **Revenue Discrepancies**: Attribution revenue vs. actual revenue variance > 15%
- **Journey Anomalies**: Average journey duration changes > 50%
- **Channel Performance**: Any channel attribution drops > 30% week-over-week

#### Business Intelligence Integration
- **Attribution Dashboard**: Real-time channel performance and ROI
- **Journey Analysis**: Customer path optimization insights
- **Revenue Attribution**: Marketing budget allocation recommendations
- **Predictive Analytics**: Customer journey and conversion probability modeling

### Advanced Use Cases

#### 1. Marketing Budget Optimization
```sql
-- ROI-based budget allocation recommendations
WITH channel_roi AS (
  SELECT 
    first_touch_channel,
    SUM(total_attributed_revenue) as attributed_revenue,
    COUNT(DISTINCT customer_email) as attributed_customers,
    AVG(journey_duration_hours) as avg_journey_duration
  FROM marketing_attribution
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY first_touch_channel
)
SELECT 
  first_touch_channel,
  attributed_revenue,
  attributed_customers,
  ROUND(attributed_revenue / attributed_customers, 2) as revenue_per_customer,
  ROUND(avg_journey_duration, 1) as avg_journey_hours,
  -- Budget allocation recommendation based on ROI
  ROUND(
    (attributed_revenue / SUM(attributed_revenue) OVER ()) * 100, 2
  ) as recommended_budget_percentage
FROM channel_roi
ORDER BY attributed_revenue DESC
```

#### 2. Customer Lifetime Value Attribution
```sql
-- CLV-based attribution weighting
WITH customer_clv AS (
  SELECT 
    customer_email,
    SUM(total_attributed_revenue) as total_clv,
    COUNT(DISTINCT shopify_order_id) as total_orders,
    MIN(date) as first_attribution_date,
    MAX(date) as last_attribution_date
  FROM marketing_attribution
  GROUP BY customer_email
)
SELECT 
  ma.first_touch_channel,
  ma.last_touch_channel,
  COUNT(*) as customer_count,
  AVG(clv.total_clv) as avg_customer_clv,
  SUM(clv.total_clv) as total_channel_clv,
  AVG(clv.total_orders) as avg_orders_per_customer
FROM marketing_attribution ma
JOIN customer_clv clv ON ma.customer_email = clv.customer_email
WHERE ma.date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY ma.first_touch_channel, ma.last_touch_channel
ORDER BY total_channel_clv DESC