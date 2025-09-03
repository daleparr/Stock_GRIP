# Shopify Data Model Specification for Weld

## Overview
This document specifies the Shopify data models for implementation in Weld, designed to capture comprehensive e-commerce order and product data for the Stock GRIP inventory optimization system.

## Model 1: Shopify Orders

### Purpose
Captures complete order-level information from Shopify including customer data, financial details, and fulfillment status.

### Data Source
- **Primary Source**: Shopify Orders API
- **Export Format**: CSV
- **Update Frequency**: Daily
- **Data Retention**: 2 years

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `shopify_order_id` | String | Yes | Unique Shopify order identifier | Must be unique, format: numeric string |
| `order_number` | String | Yes | Human-readable order number | Format: #1001, #1002, etc. |
| `created_at` | DateTime | Yes | Order creation timestamp | ISO 8601 format |
| `updated_at` | DateTime | Yes | Last order update timestamp | ISO 8601 format |
| `processed_at` | DateTime | No | Order processing timestamp | ISO 8601 format or null |
| `cancelled_at` | DateTime | No | Order cancellation timestamp | ISO 8601 format or null |
| `customer_id` | String | No | Shopify customer identifier | Numeric string or null |
| `customer_email` | String | No | Customer email address | Valid email format |
| `customer_phone` | String | No | Customer phone number | E.164 format preferred |
| `customer_first_name` | String | No | Customer first name | Max 50 characters |
| `customer_last_name` | String | No | Customer last name | Max 50 characters |
| `customer_orders_count` | Integer | No | Total orders by customer | Default: 1, Min: 1 |
| `customer_total_spent` | Float | No | Customer lifetime value | Currency: GBP, Min: 0.00 |
| `total_price` | Float | Yes | Order total including tax | Currency: GBP, Min: 0.00 |
| `subtotal_price` | Float | Yes | Order subtotal before tax | Currency: GBP, Min: 0.00 |
| `total_tax` | Float | No | Total tax amount | Currency: GBP, Default: 0.00 |
| `total_discounts` | Float | No | Total discount amount | Currency: GBP, Default: 0.00 |
| `shipping_cost` | Float | No | Shipping cost | Currency: GBP, Default: 0.00 |
| `financial_status` | String | Yes | Payment status | Values: paid, pending, refunded, voided |
| `fulfillment_status` | String | No | Shipping status | Values: fulfilled, partial, unfulfilled, null |
| `shipping_country` | String | No | Shipping country code | ISO 3166-1 alpha-2 |
| `shipping_city` | String | No | Shipping city | Max 100 characters |
| `shipping_postcode` | String | No | Shipping postal code | UK postcode format |
| `referring_site` | String | No | Traffic source URL | Valid URL or null |
| `landing_site` | String | No | Landing page URL | Valid URL or null |
| `source_name` | String | No | Order source | Values: web, pos, mobile_app, api |

### Weld Transformation Logic

```sql
-- Data Quality Checks
CASE 
  WHEN total_price < 0 THEN NULL 
  ELSE total_price 
END as total_price_clean,

-- Currency Standardization (ensure GBP)
ROUND(total_price, 2) as total_price_gbp,

-- Date Standardization
DATE(created_at) as order_date,
EXTRACT(HOUR FROM created_at) as order_hour,
EXTRACT(DOW FROM created_at) as order_day_of_week,

-- Customer Segmentation
CASE 
  WHEN customer_orders_count = 1 THEN 'new_customer'
  WHEN customer_orders_count BETWEEN 2 AND 5 THEN 'returning_customer'
  WHEN customer_orders_count > 5 THEN 'loyal_customer'
  ELSE 'unknown'
END as customer_segment,

-- Order Value Categorization
CASE 
  WHEN total_price < 25 THEN 'low_value'
  WHEN total_price BETWEEN 25 AND 100 THEN 'medium_value'
  WHEN total_price > 100 THEN 'high_value'
END as order_value_category
```

### Key Metrics for Aggregation

1. **Daily Revenue**: `SUM(total_price) GROUP BY DATE(created_at)`
2. **Average Order Value**: `AVG(total_price)`
3. **Customer Acquisition**: `COUNT(DISTINCT customer_email WHERE customer_orders_count = 1)`
4. **Order Conversion Rate**: `COUNT(*) WHERE financial_status = 'paid' / COUNT(*)`

---

## Model 2: Shopify Line Items

### Purpose
Captures individual product-level data within each order for detailed inventory and product performance analysis.

### Data Source
- **Primary Source**: Shopify Orders API (line_items array)
- **Export Format**: CSV
- **Update Frequency**: Daily
- **Data Retention**: 2 years

### Schema Definition

| Field Name | Data Type | Required | Description | Validation Rules |
|------------|-----------|----------|-------------|------------------|
| `shopify_line_item_id` | String | Yes | Unique line item identifier | Must be unique |
| `shopify_order_id` | String | Yes | Parent order identifier | Must exist in orders table |
| `product_id` | String | Yes | Internal product identifier | Maps to Stock GRIP product_id |
| `variant_id` | String | No | Product variant identifier | Shopify variant ID |
| `sku` | String | No | Stock keeping unit | Alphanumeric, max 50 chars |
| `title` | String | Yes | Product title | Max 255 characters |
| `variant_title` | String | No | Variant description | Max 255 characters |
| `vendor` | String | No | Product vendor/brand | Max 100 characters |
| `quantity` | Integer | Yes | Quantity ordered | Min: 1 |
| `price` | Float | Yes | Unit price | Currency: GBP, Min: 0.00 |
| `total_discount` | Float | No | Line item discount | Currency: GBP, Default: 0.00 |
| `weight` | Float | No | Product weight (grams) | Min: 0.0 |
| `requires_shipping` | Boolean | No | Shipping required flag | Default: true |
| `taxable` | Boolean | No | Taxable item flag | Default: true |
| `fulfillment_service` | String | No | Fulfillment method | Values: manual, amazon, shipwire |
| `fulfillment_status` | String | No | Item fulfillment status | Values: fulfilled, partial, null |

### Weld Transformation Logic

```sql
-- Revenue Calculations
quantity * price as line_total_revenue,
(quantity * price) - total_discount as line_net_revenue,

-- Product Performance Metrics
quantity as units_sold,
price as unit_price_gbp,

-- Inventory Velocity Indicators
CASE 
  WHEN quantity > 5 THEN 'high_velocity'
  WHEN quantity BETWEEN 2 AND 5 THEN 'medium_velocity'
  WHEN quantity = 1 THEN 'low_velocity'
END as velocity_category,

-- Product Category Analysis (if available in title)
CASE 
  WHEN LOWER(title) LIKE '%shirt%' OR LOWER(title) LIKE '%top%' THEN 'apparel_tops'
  WHEN LOWER(title) LIKE '%pant%' OR LOWER(title) LIKE '%jean%' THEN 'apparel_bottoms'
  WHEN LOWER(title) LIKE '%shoe%' OR LOWER(title) LIKE '%boot%' THEN 'footwear'
  ELSE 'other'
END as inferred_category
```

### Key Metrics for Aggregation

1. **Product Revenue**: `SUM(quantity * price) GROUP BY product_id`
2. **Units Sold**: `SUM(quantity) GROUP BY product_id`
3. **Average Selling Price**: `AVG(price) GROUP BY product_id`
4. **Product Velocity**: `COUNT(DISTINCT shopify_order_id) GROUP BY product_id`

### Data Quality Checks

```sql
-- Validation Rules for Weld
WHERE quantity > 0 
  AND price >= 0 
  AND shopify_order_id IS NOT NULL 
  AND product_id IS NOT NULL
  AND LENGTH(title) > 0
```

### Export Specifications

**File Naming Convention**: 
- Orders: `shopify_orders_YYYY-MM-DD.csv`
- Line Items: `shopify_line_items_YYYY-MM-DD.csv`

**CSV Format**:
- Encoding: UTF-8
- Delimiter: Comma (,)
- Quote Character: Double quote (")
- Header Row: Yes
- Date Format: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)

### Integration with Stock GRIP

**Primary Keys for Joining**:
- Orders → Line Items: `shopify_order_id`
- Line Items → Products: `product_id`
- Orders → Customers: `customer_email`

**Required Transformations for Stock GRIP**:
1. Map `product_id` to internal Stock GRIP product catalog
2. Convert all monetary values to GBP
3. Aggregate line items to daily product sales
4. Calculate demand velocity metrics
5. Generate customer lifetime value indicators

### Performance Considerations

**Weld Optimization**:
- Index on `shopify_order_id`, `product_id`, `created_at`
- Partition by `DATE(created_at)` for time-series analysis
- Use incremental loading for daily updates
- Implement data deduplication on `shopify_line_item_id`

**Memory Management**:
- Process in daily batches to manage memory usage
- Use streaming for large order volumes
- Implement checkpointing for long-running transformations