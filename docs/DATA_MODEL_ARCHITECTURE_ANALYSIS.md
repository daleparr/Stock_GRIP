# Stock GRIP Data Model Architecture Analysis

## Overview
This document analyzes the data modeling approach used in the Stock GRIP system, examining the schema design, relationships, and architectural patterns for inventory optimization.

## Current Data Model Architecture

### **Schema Type: Hybrid Dimensional + Operational**

The Stock GRIP system uses a **hybrid approach** combining elements of:
1. **Dimensional Modeling** (for analytics)
2. **Operational Schema** (for real-time processing)
3. **Denormalized Aggregation** (for performance)

## Data Model Structure

### **1. Core Entity Relationship Model**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    PRODUCTS     │    │   INVENTORY     │    │     DEMAND      │
│                 │    │                 │    │                 │
│ PK: product_id  │◄──►│ FK: product_id  │    │ FK: product_id  │
│    product_sku  │    │    stock_level  │    │    quantity     │
│    name         │    │    available    │    │    date         │
│    category     │    │    reserved     │    │    fulfilled    │
│    unit_cost    │    │    timestamp    │    │    is_forecast  │
│    price        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ OPTIMIZATION    │    │ INVENTORY       │    │ PERFORMANCE     │
│ PARAMETERS      │    │ ACTIONS         │    │ METRICS         │
│                 │    │                 │    │                 │
│ FK: product_id  │    │ FK: product_id  │    │ FK: product_id  │
│    gp_params    │    │    action_type  │    │    metric_type  │
│    mpc_params   │    │    quantity     │    │    value        │
│    constraints  │    │    cost         │    │    timestamp    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **2. Primary Keys and Foreign Keys**

#### **Primary Keys:**
- **Products**: `product_id` (String) - Shopify product ID
- **Inventory**: `id` (Integer, Auto-increment) - Surrogate key
- **Demand**: `id` (Integer, Auto-increment) - Surrogate key
- **OptimizationParameters**: `id` (Integer, Auto-increment) - Surrogate key
- **InventoryActions**: `id` (Integer, Auto-increment) - Surrogate key
- **PerformanceMetrics**: `id` (Integer, Auto-increment) - Surrogate key

#### **Foreign Keys:**
- **Inventory.product_id** → **Products.product_id**
- **Demand.product_id** → **Products.product_id**
- **OptimizationParameters.product_id** → **Products.product_id**
- **InventoryActions.product_id** → **Products.product_id**
- **PerformanceMetrics.product_id** → **Products.product_id**

#### **Business Keys:**
- **product_sku** - Natural business identifier (e.g., "1984-2025-137-05")
- **date** - Time dimension for temporal analysis

### **3. Dimensional Analysis**

#### **Fact Tables (Metrics/Events):**
- **Demand** - Sales transactions and forecasts
- **InventoryActions** - Reorder events and costs
- **PerformanceMetrics** - KPI measurements over time

#### **Dimension Tables (Master Data):**
- **Products** - Product master data
- **Time** - Implicit date dimension in fact tables

#### **Bridge Tables (Configuration):**
- **OptimizationParameters** - Algorithm configuration per product

### **4. Current Weld Integration Model**

#### **Denormalized Aggregation Approach:**
```sql
-- Product Performance Aggregated (Current)
SELECT 
  date,                    -- Time dimension
  product_id,              -- Product dimension (PK)
  product_sku,             -- Business key
  shopify_units_sold,      -- Fact: Sales quantity
  shopify_revenue,         -- Fact: Sales revenue
  facebook_spend,          -- Fact: Marketing cost
  klaviyo_attributed_revenue, -- Fact: Email revenue
  -- ... other aggregated facts
FROM denormalized_daily_aggregation
```

#### **Enhanced with Inventory (Proposed):**
```sql
-- Unified Model (Sales + Inventory)
SELECT 
  -- Dimensions
  date,
  product_id,              -- Primary key
  product_sku,             -- Business key
  
  -- Sales Facts
  shopify_units_sold,
  shopify_revenue,
  
  -- Inventory Facts
  current_inventory_level, -- Real inventory
  available_inventory,
  
  -- Business Rules (Semi-static dimensions)
  reorder_point,
  max_stock_level,
  profit_margin_percentage
FROM product_performance pp
LEFT JOIN inventory_management inv ON pp.product_sku = inv.product_sku
```

## Schema Design Analysis

### **Strengths:**
1. **Simple Relationships** - Clear FK relationships
2. **Flexible Aggregation** - Supports various time periods
3. **Real-time Capable** - Can handle live data updates
4. **Business Key Support** - Uses SKU for business identification

### **Considerations:**
1. **Denormalization** - Weld model is heavily denormalized for performance
2. **Data Duplication** - Same product data repeated across dates
3. **Schema Evolution** - Adding inventory requires model changes

### **Recommended Approach:**

#### **For Weld (Analytics):**
- **Denormalized Star Schema** - Current approach is correct
- **Date + Product grain** - Daily aggregation per product
- **Pre-calculated metrics** - Performance optimization

#### **For Stock GRIP (Operational):**
- **Normalized Operational Schema** - Current SQLAlchemy models
- **Real-time processing** - Live inventory updates
- **Relationship integrity** - FK constraints maintained

## Data Flow Architecture

### **Current Flow:**
```
Shopify API → Weld → CSV Export → Stock GRIP → SQLAlchemy → Dashboard
```

### **Enhanced Flow (With Inventory):**
```
Shopify Products API ─┐
                      ├→ Weld → Unified CSV → Stock GRIP → Dashboard
Shopify Inventory API ─┘
```

## Key Design Decisions

### **1. Grain Definition:**
- **Weld**: Daily aggregation per product (`date + product_sku`)
- **Stock GRIP**: Event-based with relationships (`product_id` as FK)

### **2. Key Strategy:**
- **Natural Key**: `product_sku` (business identifier)
- **Surrogate Key**: `product_id` (system identifier)
- **Composite Key**: `date + product_sku` (for time series)

### **3. Normalization Level:**
- **Weld Models**: 1NF (denormalized for analytics)
- **Stock GRIP Database**: 3NF (normalized for operations)

## Recommendations

### **For Your Unified CSV:**
1. **Use `product_sku` as primary business key**
2. **Include `date` for temporal analysis**
3. **Maintain referential integrity** between sales and inventory data
4. **Pre-calculate derived metrics** in Weld for performance

### **For Stock GRIP Processing:**
1. **Map `product_sku` to `product_id`** for FK relationships
2. **Validate data integrity** during CSV import
3. **Handle missing inventory data** gracefully
4. **Maintain audit trail** of data transformations

This hybrid approach provides both analytical flexibility (Weld) and operational integrity (Stock GRIP) for accurate inventory optimization.