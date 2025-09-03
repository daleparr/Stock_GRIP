-- SQL Data Transformations for Shopify, Facebook & Klaviyo Integration
-- Stock GRIP Live Data Processing

-- =====================================================
-- 1. SHOPIFY DATA TRANSFORMATIONS
-- =====================================================

-- Transform Shopify orders into standardized sales data
CREATE VIEW shopify_sales_transformed AS
SELECT 
    so.created_at as date,
    sli.product_id,
    'shopify' as channel,
    sli.quantity as quantity_sold,
    (sli.price * sli.quantity - sli.total_discount) as revenue,
    CASE 
        WHEN so.customer_total_spent > 1000 THEN 'premium'
        WHEN so.customer_total_spent > 500 THEN 'regular'
        ELSE 'budget'
    END as customer_segment,
    COALESCE(so.source_name, 'web') as fulfillment_method,
    so.shopify_order_id as source_order_id,
    so.customer_email,
    so.shipping_country,
    so.financial_status,
    so.total_discounts / NULLIF(so.total_price, 0) as discount_rate
FROM shopify_orders so
JOIN shopify_line_items sli ON so.shopify_order_id = sli.shopify_order_id
WHERE so.financial_status = 'paid'
  AND so.cancelled_at IS NULL;

-- Aggregate daily Shopify sales by product
CREATE VIEW shopify_daily_sales AS
SELECT 
    DATE(date) as sale_date,
    product_id,
    SUM(quantity_sold) as total_quantity,
    SUM(revenue) as total_revenue,
    COUNT(DISTINCT source_order_id) as order_count,
    COUNT(DISTINCT customer_email) as unique_customers,
    AVG(revenue / quantity_sold) as avg_unit_price,
    SUM(CASE WHEN customer_segment = 'premium' THEN revenue ELSE 0 END) as premium_revenue,
    AVG(discount_rate) as avg_discount_rate
FROM shopify_sales_transformed
GROUP BY DATE(date), product_id;

-- Customer lifetime value calculation
CREATE VIEW shopify_customer_ltv AS
SELECT 
    customer_email,
    COUNT(DISTINCT source_order_id) as total_orders,
    SUM(revenue) as total_spent,
    AVG(revenue) as avg_order_value,
    MIN(date) as first_order_date,
    MAX(date) as last_order_date,
    JULIANDAY(MAX(date)) - JULIANDAY(MIN(date)) as customer_lifespan_days,
    SUM(revenue) / NULLIF(COUNT(DISTINCT source_order_id), 0) as ltv_per_order
FROM shopify_sales_transformed
GROUP BY customer_email;

-- =====================================================
-- 2. FACEBOOK ADS DATA TRANSFORMATIONS
-- =====================================================

-- Daily Facebook ad performance by product attribution
CREATE VIEW facebook_product_performance AS
SELECT 
    date,
    JSON_EXTRACT(attributed_products, '$[*].product_id') as product_id,
    campaign_name,
    SUM(spend) as total_spend,
    SUM(impressions) as total_impressions,
    SUM(clicks) as total_clicks,
    SUM(purchases) as total_purchases,
    SUM(purchase_value) as total_purchase_value,
    AVG(ctr) as avg_ctr,
    AVG(cpc) as avg_cpc,
    AVG(roas) as avg_roas,
    SUM(spend) / NULLIF(SUM(purchases), 0) as cost_per_purchase
FROM facebook_ads_data
WHERE attributed_products IS NOT NULL
GROUP BY date, JSON_EXTRACT(attributed_products, '$[*].product_id'), campaign_name;

-- Facebook campaign effectiveness analysis
CREATE VIEW facebook_campaign_analysis AS
SELECT 
    campaign_id,
    campaign_name,
    DATE(date) as campaign_date,
    SUM(spend) as daily_spend,
    SUM(impressions) as daily_impressions,
    SUM(clicks) as daily_clicks,
    SUM(purchases) as daily_purchases,
    SUM(purchase_value) as daily_revenue,
    
    -- Performance metrics
    SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0) as ctr_percent,
    SUM(spend) / NULLIF(SUM(clicks), 0) as cpc,
    SUM(purchase_value) / NULLIF(SUM(spend), 0) as roas,
    SUM(purchases) * 100.0 / NULLIF(SUM(clicks), 0) as conversion_rate,
    
    -- Audience insights
    age_range,
    gender,
    country
FROM facebook_ads_data
GROUP BY campaign_id, campaign_name, DATE(date), age_range, gender, country;

-- =====================================================
-- 3. KLAVIYO EMAIL DATA TRANSFORMATIONS
-- =====================================================

-- Email campaign performance by product
CREATE VIEW klaviyo_product_performance AS
SELECT 
    date,
    JSON_EXTRACT(featured_products, '$[*].product_id') as product_id,
    campaign_name,
    flow_name,
    message_type,
    SUM(recipients) as total_recipients,
    SUM(opens) as total_opens,
    SUM(clicks) as total_clicks,
    SUM(attributed_revenue) as total_attributed_revenue,
    SUM(attributed_orders) as total_attributed_orders,
    
    -- Performance metrics
    AVG(open_rate) as avg_open_rate,
    AVG(click_rate) as avg_click_rate,
    SUM(attributed_revenue) / NULLIF(SUM(recipients), 0) as revenue_per_recipient,
    SUM(attributed_revenue) / NULLIF(SUM(opens), 0) as revenue_per_open
FROM klaviyo_email_data
WHERE featured_products IS NOT NULL
GROUP BY date, JSON_EXTRACT(featured_products, '$[*].product_id'), campaign_name, flow_name, message_type;

-- Customer email engagement scoring
CREATE VIEW klaviyo_customer_engagement AS
SELECT 
    kc.email,
    kc.customer_segment,
    kc.lifecycle_stage,
    kc.total_orders,
    kc.total_spent,
    kc.email_engagement_score,
    
    -- Recent email activity (last 30 days)
    COUNT(ked.id) as emails_received_30d,
    SUM(ked.opens) as total_opens_30d,
    SUM(ked.clicks) as total_clicks_30d,
    SUM(ked.attributed_revenue) as email_attributed_revenue_30d,
    
    -- Engagement rates
    SUM(ked.opens) * 100.0 / NULLIF(COUNT(ked.id), 0) as open_rate_30d,
    SUM(ked.clicks) * 100.0 / NULLIF(SUM(ked.opens), 0) as click_through_rate_30d
FROM klaviyo_customers kc
LEFT JOIN klaviyo_email_data ked ON kc.email = ked.segment_name -- Simplified join
WHERE ked.date >= DATE('now', '-30 days') OR ked.date IS NULL
GROUP BY kc.email, kc.customer_segment, kc.lifecycle_stage, kc.total_orders, kc.total_spent, kc.email_engagement_score;

-- =====================================================
-- 4. INTEGRATED MARKETING ATTRIBUTION
-- =====================================================

-- Multi-touch attribution analysis
CREATE VIEW marketing_attribution_analysis AS
SELECT 
    DATE(ma.date) as attribution_date,
    so.product_id,
    ma.first_touch_channel,
    ma.last_touch_channel,
    
    -- Revenue attribution
    SUM(ma.attributed_revenue) as total_attributed_revenue,
    COUNT(DISTINCT ma.shopify_order_id) as attributed_orders,
    
    -- Channel performance
    SUM(CASE WHEN ma.first_touch_channel = 'facebook' THEN ma.attributed_revenue ELSE 0 END) as facebook_first_touch_revenue,
    SUM(CASE WHEN ma.last_touch_channel = 'facebook' THEN ma.attributed_revenue ELSE 0 END) as facebook_last_touch_revenue,
    SUM(CASE WHEN ma.first_touch_channel = 'email' THEN ma.attributed_revenue ELSE 0 END) as email_first_touch_revenue,
    SUM(CASE WHEN ma.last_touch_channel = 'email' THEN ma.attributed_revenue ELSE 0 END) as email_last_touch_revenue,
    
    -- Customer journey insights
    AVG(JSON_ARRAY_LENGTH(ma.touchpoint_sequence)) as avg_touchpoints,
    COUNT(DISTINCT ma.customer_email) as unique_customers
FROM marketing_attribution ma
JOIN shopify_line_items sli ON ma.shopify_order_id = sli.shopify_order_id
JOIN shopify_orders so ON ma.shopify_order_id = so.shopify_order_id
GROUP BY DATE(ma.date), so.product_id, ma.first_touch_channel, ma.last_touch_channel;

-- =====================================================
-- 5. UNIFIED PRODUCT PERFORMANCE VIEW
-- =====================================================

-- Comprehensive product performance across all channels
CREATE VIEW unified_product_performance AS
SELECT 
    p.product_id,
    p.name as product_name,
    p.category,
    DATE('now') as analysis_date,
    
    -- Shopify sales data
    COALESCE(sds.total_quantity, 0) as shopify_units_sold,
    COALESCE(sds.total_revenue, 0) as shopify_revenue,
    COALESCE(sds.order_count, 0) as shopify_orders,
    COALESCE(sds.unique_customers, 0) as shopify_customers,
    
    -- Facebook advertising data
    COALESCE(fpp.total_spend, 0) as facebook_spend,
    COALESCE(fpp.total_impressions, 0) as facebook_impressions,
    COALESCE(fpp.total_clicks, 0) as facebook_clicks,
    COALESCE(fpp.total_purchase_value, 0) as facebook_attributed_revenue,
    COALESCE(fpp.avg_roas, 0) as facebook_roas,
    
    -- Klaviyo email data
    COALESCE(kpp.total_recipients, 0) as email_recipients,
    COALESCE(kpp.total_opens, 0) as email_opens,
    COALESCE(kpp.total_clicks, 0) as email_clicks,
    COALESCE(kpp.total_attributed_revenue, 0) as email_attributed_revenue,
    
    -- Calculated performance metrics
    COALESCE(sds.total_revenue, 0) + COALESCE(fpp.total_purchase_value, 0) + COALESCE(kpp.total_attributed_revenue, 0) as total_attributed_revenue,
    COALESCE(fpp.total_spend, 0) as total_marketing_spend,
    (COALESCE(sds.total_revenue, 0) + COALESCE(fpp.total_purchase_value, 0) + COALESCE(kpp.total_attributed_revenue, 0)) / NULLIF(COALESCE(fpp.total_spend, 0), 0) as overall_roas,
    
    -- Demand indicators
    CASE 
        WHEN COALESCE(sds.total_quantity, 0) > 100 THEN 'high'
        WHEN COALESCE(sds.total_quantity, 0) > 50 THEN 'medium'
        ELSE 'low'
    END as demand_level
    
FROM products p
LEFT JOIN shopify_daily_sales sds ON p.product_id = sds.product_id AND sds.sale_date = DATE('now')
LEFT JOIN facebook_product_performance fpp ON p.product_id = fpp.product_id AND fpp.date = DATE('now')
LEFT JOIN klaviyo_product_performance kpp ON p.product_id = kpp.product_id AND kpp.date = DATE('now');

-- =====================================================
-- 6. DATA QUALITY AND MONITORING VIEWS
-- =====================================================

-- Data freshness monitoring
CREATE VIEW data_freshness_monitor AS
SELECT 
    'shopify_orders' as table_name,
    COUNT(*) as total_records,
    MAX(timestamp_created) as last_update,
    COUNT(CASE WHEN DATE(timestamp_created) = DATE('now') THEN 1 END) as today_records
FROM shopify_orders
UNION ALL
SELECT 
    'facebook_ads_data' as table_name,
    COUNT(*) as total_records,
    MAX(timestamp_created) as last_update,
    COUNT(CASE WHEN DATE(timestamp_created) = DATE('now') THEN 1 END) as today_records
FROM facebook_ads_data
UNION ALL
SELECT 
    'klaviyo_email_data' as table_name,
    COUNT(*) as total_records,
    MAX(timestamp_created) as last_update,
    COUNT(CASE WHEN DATE(timestamp_created) = DATE('now') THEN 1 END) as today_records
FROM klaviyo_email_data;

-- Data quality checks
CREATE VIEW data_quality_checks AS
SELECT 
    'shopify_revenue_validation' as check_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN total_price < 0 THEN 1 END) as failed_records,
    'Negative revenue values detected' as issue_description
FROM shopify_orders
WHERE total_price < 0
UNION ALL
SELECT 
    'facebook_spend_validation' as check_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN spend < 0 THEN 1 END) as failed_records,
    'Negative spend values detected' as issue_description
FROM facebook_ads_data
WHERE spend < 0
UNION ALL
SELECT 
    'klaviyo_engagement_validation' as check_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN open_rate > 100 THEN 1 END) as failed_records,
    'Invalid open rates detected' as issue_description
FROM klaviyo_email_data
WHERE open_rate > 100;

-- =====================================================
-- 7. MATERIALIZED AGGREGATION TABLES (for performance)
-- =====================================================

-- Create materialized daily summary table
CREATE TABLE IF NOT EXISTS daily_performance_summary AS
SELECT 
    DATE('now') as summary_date,
    product_id,
    shopify_units_sold,
    shopify_revenue,
    facebook_spend,
    facebook_attributed_revenue,
    email_attributed_revenue,
    total_attributed_revenue,
    overall_roas,
    demand_level,
    datetime('now') as created_at
FROM unified_product_performance;

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_daily_summary_date_product ON daily_performance_summary(summary_date, product_id);
CREATE INDEX IF NOT EXISTS idx_shopify_orders_created ON shopify_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_facebook_ads_date ON facebook_ads_data(date);
CREATE INDEX IF NOT EXISTS idx_klaviyo_email_date ON klaviyo_email_data(date);