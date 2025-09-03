# Klaviyo Email Data Model Specification for Weld

## Overview
This document specifies the Klaviyo email marketing data models for implementation in Weld, designed to capture comprehensive email campaign performance and customer engagement data for marketing attribution and customer lifecycle optimization in the Stock GRIP system.

## Model 1: Klaviyo Email Campaign Performance

### Purpose
Captures detailed email campaign and automated flow performance metrics including engagement rates, revenue attribution, and customer segmentation for email marketing optimization and inventory demand forecasting.

### Data Source
- **Primary Source**: Klaviyo API (Campaigns & Flows)
- **Export Format**: CSV
- **Update Frequency**: Daily
- **Data Retention**: 2 years
- **Attribution Window**: 7-day post-click, 1-day post-open

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `date` | Date | Yes | Campaign send date | YYYY-MM-DD format |
| `campaign_id` | String | No | Klaviyo campaign identifier | Numeric string, null for flows |
| `campaign_name` | String | No | Campaign name | Max 255 characters |
| `flow_id` | String | No | Klaviyo flow identifier | Numeric string, null for campaigns |
| `flow_name` | String | No | Flow name | Max 255 characters |
| `message_type` | String | Yes | Email type | Values: campaign, flow |
| `recipients` | Integer | No | Total recipients | Min: 0, Default: 0 |
| `delivered` | Integer | No | Successfully delivered | Min: 0, Default: 0 |
| `opens` | Integer | No | Total opens | Min: 0, Default: 0 |
| `unique_opens` | Integer | No | Unique opens | Min: 0, Default: 0 |
| `clicks` | Integer | No | Total clicks | Min: 0, Default: 0 |
| `unique_clicks` | Integer | No | Unique clicks | Min: 0, Default: 0 |
| `unsubscribes` | Integer | No | Unsubscribe count | Min: 0, Default: 0 |
| `spam_complaints` | Integer | No | Spam complaints | Min: 0, Default: 0 |
| `bounces` | Integer | No | Bounce count | Min: 0, Default: 0 |
| `attributed_revenue` | Float | No | Revenue attributed to email | Currency: GBP, Min: 0.00 |
| `attributed_orders` | Integer | No | Orders attributed to email | Min: 0, Default: 0 |
| `segment_name` | String | No | Target segment name | Max 100 characters |
| `segment_size` | Integer | No | Segment size at send time | Min: 0 |
| `featured_products` | Text | No | Products featured (JSON) | JSON array of product objects |

### Calculated Fields (Weld Transformations)

```sql
-- Email Performance Metrics
CASE
  WHEN recipients > 0 THEN (delivered::FLOAT / recipients::FLOAT) * 100
  ELSE 0
END as delivery_rate_percentage,

CASE
  WHEN delivered > 0 THEN (unique_opens::FLOAT / delivered::FLOAT) * 100
  ELSE 0
END as open_rate_percentage,

CASE
  WHEN unique_opens > 0 THEN (unique_clicks::FLOAT / unique_opens::FLOAT) * 100
  ELSE 0
END as click_to_open_rate_percentage,

CASE
  WHEN delivered > 0 THEN (unique_clicks::FLOAT / delivered::FLOAT) * 100
  ELSE 0
END as click_rate_percentage,

CASE
  WHEN delivered > 0 THEN (unsubscribes::FLOAT / delivered::FLOAT) * 100
  ELSE 0
END as unsubscribe_rate_percentage,

-- Revenue Metrics
CASE
  WHEN recipients > 0 THEN attributed_revenue / recipients
  ELSE 0
END as revenue_per_recipient_gbp,

CASE
  WHEN unique_clicks > 0 THEN attributed_revenue / unique_clicks
  ELSE 0
END as revenue_per_click_gbp,

CASE
  WHEN attributed_orders > 0 THEN attributed_revenue / attributed_orders
  ELSE 0
END as average_order_value_gbp,

-- Engagement Quality Scoring
CASE
  WHEN open_rate_percentage >= 25 AND click_rate_percentage >= 3 THEN 'high_engagement'
  WHEN open_rate_percentage >= 20 AND click_rate_percentage >= 2 THEN 'medium_engagement'
  WHEN open_rate_percentage >= 15 AND click_rate_percentage >= 1 THEN 'low_engagement'
  ELSE 'poor_engagement'
END as engagement_quality,

-- Campaign Performance Categories
CASE
  WHEN revenue_per_recipient_gbp >= 1.0 THEN 'high_value'
  WHEN revenue_per_recipient_gbp >= 0.5 THEN 'medium_value'
  WHEN revenue_per_recipient_gbp >= 0.1 THEN 'low_value'
  ELSE 'minimal_value'
END as revenue_performance,

-- Time-based Analysis
EXTRACT(DOW FROM date) as day_of_week,
EXTRACT(HOUR FROM date) as send_hour,
CASE
  WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN 'weekend'
  ELSE 'weekday'
END as day_type
```

### Advanced Weld Transformations

#### 1. Campaign Performance Comparison
```sql
-- Campaign vs Flow performance analysis
WITH performance_summary AS (
  SELECT
    message_type,
    COUNT(*) as total_sends,
    AVG(open_rate_percentage) as avg_open_rate,
    AVG(click_rate_percentage) as avg_click_rate,
    AVG(revenue_per_recipient_gbp) as avg_revenue_per_recipient,
    SUM(attributed_revenue) as total_attributed_revenue
  FROM klaviyo_email_data
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY message_type
)
SELECT
  message_type,
  total_sends,
  ROUND(avg_open_rate, 2) as avg_open_rate,
  ROUND(avg_click_rate, 2) as avg_click_rate,
  ROUND(avg_revenue_per_recipient, 2) as avg_revenue_per_recipient,
  total_attributed_revenue
FROM performance_summary
```

#### 2. Product Performance from Email Marketing
```sql
-- Extract product performance from featured_products JSON
WITH product_attribution AS (
  SELECT
    date,
    COALESCE(campaign_id, flow_id) as email_id,
    COALESCE(campaign_name, flow_name) as email_name,
    message_type,
    JSON_EXTRACT_PATH_TEXT(featured_products, 'product_id') as product_id,
    JSON_EXTRACT_PATH_TEXT(featured_products, 'featured_position') as position,
    attributed_revenue / NULLIF(JSON_ARRAY_LENGTH(featured_products), 0) as allocated_revenue,
    unique_clicks / NULLIF(JSON_ARRAY_LENGTH(featured_products), 0) as allocated_clicks
  FROM klaviyo_email_data
  WHERE featured_products IS NOT NULL
    AND JSON_ARRAY_LENGTH(featured_products) > 0
)
SELECT
  product_id,
  COUNT(*) as email_mentions,
  SUM(allocated_revenue) as total_email_attributed_revenue,
  SUM(allocated_clicks) as total_email_clicks,
  AVG(CAST(position AS INTEGER)) as avg_featured_position
FROM product_attribution
GROUP BY product_id
ORDER BY total_email_attributed_revenue DESC
```

#### 3. Customer Lifecycle Email Analysis
```sql
-- Email performance by customer lifecycle stage
SELECT
  segment_name,
  message_type,
  COUNT(*) as email_count,
  AVG(open_rate_percentage) as avg_open_rate,
  AVG(click_rate_percentage) as avg_click_rate,
  AVG(revenue_per_recipient_gbp) as avg_revenue_per_recipient,
  SUM(attributed_revenue) as total_revenue,
  SUM(recipients) as total_recipients
FROM klaviyo_email_data
WHERE segment_name IS NOT NULL
  AND date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY segment_name, message_type
HAVING total_recipients > 100  -- Minimum audience size
ORDER BY avg_revenue_per_recipient DESC
```

### Key Performance Indicators (KPIs)

#### Primary Email Metrics
1. **Open Rate**: `AVG(unique_opens / delivered * 100)`
2. **Click Rate**: `AVG(unique_clicks / delivered * 100)`
3. **Revenue per Recipient**: `AVG(attributed_revenue / recipients)`
4. **Email ROI**: `SUM(attributed_revenue) / SUM(email_costs)`

#### Secondary Metrics
1. **Click-to-Open Rate**: `AVG(unique_clicks / unique_opens * 100)`
2. **Unsubscribe Rate**: `AVG(unsubscribes / delivered * 100)`
3. **List Growth Rate**: `(new_subscribers - unsubscribes) / total_subscribers * 100`
4. **Engagement Score**: `(open_rate * 0.3) + (click_rate * 0.7)`

---

## Model 2: Klaviyo Customer Profile Data

### Purpose
Captures comprehensive customer profile information including engagement history, purchase behavior, and lifecycle stage for personalized marketing and inventory planning.

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `klaviyo_person_id` | String | Yes | Unique Klaviyo customer ID | Must be unique |
| `email` | String | Yes | Customer email address | Valid email format |
| `phone_number` | String | No | Customer phone number | E.164 format |
| `first_name` | String | No | Customer first name | Max 50 characters |
| `last_name` | String | No | Customer last name | Max 50 characters |
| `total_orders` | Integer | No | Lifetime order count | Min: 0, Default: 0 |
| `total_spent` | Float | No | Lifetime value | Currency: GBP, Min: 0.00 |
| `average_order_value` | Float | No | Average order value | Currency: GBP, Min: 0.00 |
| `last_order_date` | Date | No | Most recent order date | YYYY-MM-DD format |
| `first_order_date` | Date | No | First order date | YYYY-MM-DD format |
| `email_engagement_score` | Float | No | Email engagement score | Range: 0.0-1.0 |
| `last_email_open` | DateTime | No | Last email open timestamp | ISO 8601 format |
| `last_email_click` | DateTime | No | Last email click timestamp | ISO 8601 format |
| `customer_segment` | String | No | Customer segment | Values: VIP, regular, at_risk, new |
| `lifecycle_stage` | String | No | Lifecycle stage | Values: new, active, at_risk, churned |
| `email_subscribed` | Boolean | No | Email subscription status | Default: true |
| `sms_subscribed` | Boolean | No | SMS subscription status | Default: false |
| `preferred_categories` | Text | No | Preferred product categories (JSON) | JSON array |
| `country` | String | No | Customer country | ISO 3166-1 alpha-2 |
| `region` | String | No | Customer region/state | Max 100 characters |
| `city` | String | No | Customer city | Max 100 characters |
| `custom_properties` | Text | No | Additional properties (JSON) | Valid JSON object |

### Customer Segmentation Logic (Weld)

```sql
-- Advanced customer segmentation
WITH customer_metrics AS (
  SELECT
    klaviyo_person_id,
    email,
    total_spent,
    total_orders,
    average_order_value,
    CURRENT_DATE - last_order_date as days_since_last_order,
    CURRENT_DATE - first_order_date as customer_age_days,
    email_engagement_score,
    CASE
      WHEN last_email_open >= CURRENT_DATE - INTERVAL '30 days' THEN 'active'
      WHEN last_email_open >= CURRENT_DATE - INTERVAL '90 days' THEN 'declining'
      ELSE 'inactive'
    END as email_engagement_status
  FROM klaviyo_customers
)
SELECT
  *,
  -- RFM Segmentation
  CASE
    WHEN days_since_last_order <= 30 AND total_spent >= 500 AND total_orders >= 5 THEN 'champions'
    WHEN days_since_last_order <= 60 AND total_spent >= 300 AND total_orders >= 3 THEN 'loyal_customers'
    WHEN days_since_last_order <= 30 AND total_orders = 1 THEN 'new_customers'
    WHEN days_since_last_order BETWEEN 61 AND 120 AND total_spent >= 200 THEN 'potential_loyalists'
    WHEN days_since_last_order BETWEEN 121 AND 180 THEN 'at_risk'
    WHEN days_since_last_order > 180 THEN 'cannot_lose_them'
    ELSE 'others'
  END as rfm_segment,
  
  -- Customer Lifetime Value Prediction
  CASE
    WHEN customer_age_days > 0 THEN
      (total_spent / customer_age_days) * 365  -- Annualized CLV
    ELSE 0
  END as predicted_annual_clv,
  
  -- Churn Risk Score
  CASE
    WHEN days_since_last_order > 180 AND email_engagement_status = 'inactive' THEN 0.9
    WHEN days_since_last_order > 120 AND email_engagement_status = 'declining' THEN 0.7
    WHEN days_since_last_order > 90 AND email_engagement_status = 'active' THEN 0.4
    WHEN days_since_last_order > 60 THEN 0.2
    ELSE 0.1
  END as churn_risk_score
FROM customer_metrics
```

### Data Quality Validation

```sql
-- Customer data quality checks
SELECT
  COUNT(*) as total_customers,
  COUNT(CASE WHEN email IS NULL OR email = '' THEN 1 END) as missing_email,
  COUNT(CASE WHEN total_spent < 0 THEN 1 END) as negative_spent,
  COUNT(CASE WHEN total_orders < 0 THEN 1 END) as negative_orders,
  COUNT(CASE WHEN last_order_date > CURRENT_DATE THEN 1 END) as future_order_dates,
  COUNT(CASE WHEN first_order_date > last_order_date THEN 1 END) as invalid_date_sequence,
  AVG(email_engagement_score) as avg_engagement_score,
  COUNT(CASE WHEN email_engagement_score > 1.0 THEN 1 END) as invalid_engagement_scores
FROM klaviyo_customers
```

### Integration Specifications

#### Stock GRIP Integration Points
1. **Customer Segmentation**: Feed RFM segments into demand forecasting models
2. **Churn Prediction**: Use churn risk scores for inventory planning
3. **CLV Optimization**: Integrate predicted CLV into marketing budget allocation
4. **Product Preferences**: Map preferred categories to inventory optimization

#### Join Keys for Weld
- **Primary Key**: `klaviyo_person_id`
- **Email Matching**: `email` (for cross-platform customer matching)
- **Segmentation**: `customer_segment`, `lifecycle_stage`
- **Geographic**: `country`, `region`, `city`

### Export Configuration

#### File Naming Convention
- **Email Performance**: `klaviyo_email_performance_YYYY-MM-DD.csv`
- **Customer Profiles**: `klaviyo_customers_YYYY-MM-DD.csv`
- **Segmentation**: `klaviyo_customer_segments_YYYY-MM-DD.csv`

#### CSV Format Specifications
- **Encoding**: UTF-8
- **Delimiter**: Comma (,)
- **Quote Character**: Double quote (")
- **Header Row**: Yes
- **Date Format**: YYYY-MM-DD
- **DateTime Format**: YYYY-MM-DDTHH:MM:SSZ
- **Decimal Places**: 2 for currency, 4 for scores
- **Boolean Values**: true/false

### Performance Optimization

#### Weld Processing Recommendations
1. **Partitioning**: Partition email data by `date`, customer data by `customer_segment`
2. **Indexing**: Create indexes on `email`, `klaviyo_person_id`, `date`
3. **Incremental Updates**: Use `last_updated` timestamp for customer data
4. **Aggregation**: Pre-calculate customer metrics for faster queries
5. **Memory Management**: Process customer data in batches of 10,000 records

### Monitoring and Alerting

#### Data Quality Alerts
- **Missing Email Data**: > 1% of customers without email
- **Engagement Anomalies**: Average engagement score drops > 20%
- **Revenue Inconsistencies**: Attributed revenue > 150% of Shopify revenue
- **Data Freshness**: Customer data not updated in > 24 hours

#### Business Intelligence Integration
- **Customer Segmentation Dashboard**: Real-time RFM analysis
- **Email Performance Tracking**: Campaign ROI and engagement trends
- **Churn Risk Monitoring**: At-risk customer identification and alerts
- **CLV Optimization**: Customer value-based inventory recommendations