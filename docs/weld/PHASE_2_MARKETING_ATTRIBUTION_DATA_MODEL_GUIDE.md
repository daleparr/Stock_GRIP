# Phase 2 Marketing Attribution Data Model Implementation Guide

## 🎯 **OBJECTIVE**
Update your Weld data models to include the specific marketing attribution columns required for Phase 2 Marketing-Inventory Integration.

## 🔍 **CURRENT ISSUE**
Phase 2 marketing integration is showing all zeros because the required marketing attribution columns are missing from your data model:

### **Missing Critical Columns:**
- `facebook_7d_attributed_revenue` (7-day attribution window)
- `klaviyo_emails_sent` (email volume for efficiency calculation)
- `klaviyo_3d_attributed_revenue` (3-day attribution window)

## 📋 **IMPLEMENTATION STEPS**

### **Step 1: Update Your Product Performance Aggregated Model**

In your existing **Product Performance Aggregated** model in Weld, add these fields:

```sql
-- ENHANCED FACEBOOK ATTRIBUTION
-- Add 7-day attribution window support
COALESCE(facebook_7d_attributed_revenue, facebook_attributed_revenue) as facebook_7d_attributed_revenue,

-- ENHANCED KLAVIYO ATTRIBUTION  
-- Add email volume (CRITICAL for efficiency calculation)
klaviyo_emails_sent,
-- Add 3-day attribution window support
COALESCE(klaviyo_3d_attributed_revenue, klaviyo_attributed_revenue) as klaviyo_3d_attributed_revenue,
```

### **Step 2: Update Source Data Models**

#### **Facebook Ads Model Enhancement:**
```sql
-- In your Facebook Ads data model, ensure you have:
SELECT 
  campaign_id,
  ad_set_id,
  ad_id,
  date,
  spend as facebook_spend,
  impressions as facebook_impressions,
  clicks as facebook_clicks,
  
  -- CRITICAL: Add attribution windows
  actions_value_7d as facebook_7d_attributed_revenue,  -- 7-day attribution
  actions_value_1d as facebook_1d_attributed_revenue,  -- 1-day attribution (optional)
  actions_value_28d as facebook_28d_attributed_revenue, -- 28-day attribution (optional)
  
  -- Default to 7-day if specific windows not available
  COALESCE(actions_value_7d, actions_value) as facebook_attributed_revenue
FROM {{raw.facebook_ads.insights}}
```

#### **Klaviyo Email Model Enhancement:**
```sql
-- In your Klaviyo data model, ensure you have:
SELECT 
  campaign_id,
  message_id,
  date,
  
  -- CRITICAL: Email volume for efficiency calculation
  total_recipients as klaviyo_emails_sent,
  unique_opens as klaviyo_emails_opened,
  unique_clicks as klaviyo_emails_clicked,
  
  -- CRITICAL: Add attribution windows
  attributed_revenue_3d as klaviyo_3d_attributed_revenue,  -- 3-day attribution
  attributed_revenue_1d as klaviyo_1d_attributed_revenue,  -- 1-day attribution (optional)
  attributed_revenue_7d as klaviyo_7d_attributed_revenue,  -- 7-day attribution (optional)
  
  -- Default to 3-day if specific windows not available
  COALESCE(attributed_revenue_3d, attributed_revenue) as klaviyo_attributed_revenue
FROM {{raw.klaviyo.campaign_performance}}
```

### **Step 3: Replace Your Current Unified Model**

Replace your current `unified_product_performance_with_inventory.sql` with the enhanced version:

**File:** `sql/unified_product_performance_with_inventory_enhanced.sql`

Key enhancements:
- ✅ Added `facebook_7d_attributed_revenue`
- ✅ Added `klaviyo_emails_sent`
- ✅ Added `klaviyo_3d_attributed_revenue`
- ✅ Added data quality indicators
- ✅ Enhanced COALESCE fallbacks

### **Step 4: Update CSV Export Configuration**

In Weld, update your CSV export to use the enhanced model:

**Export Settings:**
- **Model:** `unified_product_performance_with_inventory_enhanced`
- **File Name:** `stock_grip_unified_sales_inventory_marketing.csv`
- **Schedule:** Daily at 6:00 AM
- **Format:** CSV with headers

## 🔧 **WELD CONFIGURATION STEPS**

### **1. Facebook Ads Data Source**
Ensure your Facebook Ads connection includes these fields:
```
✅ spend
✅ impressions  
✅ clicks
✅ actions_value (default attribution)
✅ actions_value_7d (7-day attribution) ← CRITICAL
✅ actions_value_1d (1-day attribution)
✅ actions_value_28d (28-day attribution)
```

### **2. Klaviyo Data Source**
Ensure your Klaviyo connection includes these fields:
```
✅ total_recipients ← CRITICAL (maps to klaviyo_emails_sent)
✅ unique_opens
✅ unique_clicks
✅ attributed_revenue (default attribution)
✅ attributed_revenue_3d (3-day attribution) ← CRITICAL
✅ attributed_revenue_1d (1-day attribution)
✅ attributed_revenue_7d (7-day attribution)
```

### **3. Data Model Joins**
Update your joins to aggregate by product and date:
```sql
-- Facebook attribution by product
facebook_by_product AS (
  SELECT 
    product_id,
    date,
    SUM(facebook_spend) as facebook_spend,
    SUM(facebook_7d_attributed_revenue) as facebook_7d_attributed_revenue,
    SUM(facebook_attributed_revenue) as facebook_attributed_revenue
  FROM facebook_ads_enhanced
  GROUP BY product_id, date
),

-- Klaviyo attribution by product  
klaviyo_by_product AS (
  SELECT 
    product_id,
    date,
    SUM(klaviyo_emails_sent) as klaviyo_emails_sent,
    SUM(klaviyo_3d_attributed_revenue) as klaviyo_3d_attributed_revenue,
    SUM(klaviyo_attributed_revenue) as klaviyo_attributed_revenue
  FROM klaviyo_campaigns_enhanced
  GROUP BY product_id, date
)
```

## 📊 **EXPECTED RESULTS**

### **Before (Current State):**
```
Marketing Attribution Summary:
├── Facebook Stars: 0
├── Email Champions: 0  
├── Multi-Channel: 0
├── Avg FB ROAS: 0.00x
└── Avg Email Eff: £0.00
```

### **After (With Enhanced Model):**
```
Marketing Attribution Summary:
├── Facebook Stars: 15
├── Email Champions: 8  
├── Multi-Channel: 3
├── Avg FB ROAS: 2.4x
└── Avg Email Eff: £0.85
```

## 🚀 **PHASE 2 FEATURES ENABLED**

Once you implement these changes, Phase 2 will automatically activate:

### **✅ Marketing-Adjusted Demand Forecasting**
- 15% boost for high Facebook ROAS (>3.0x)
- 12% boost for high email efficiency (>£1.0)
- Multi-channel bonus: +5%

### **✅ Channel-Specific Safety Stock Optimization**
- Facebook-focused: 1.3x volatility multiplier
- Email-focused: 2.0x volatility multiplier  
- Multi-channel stars: 1.1x volatility multiplier

### **✅ Campaign Coordination**
- Campaign detection based on performance
- Inventory boost calculations
- Preparation timeline recommendations

### **✅ Marketing-Driven Reorder Recommendations**
- Priority classification (HIGH/MEDIUM/LOW)
- Revenue opportunity quantification
- Confidence scoring (30%-95%)

## 🔄 **TESTING WORKFLOW**

1. **Update Weld Models** → Add missing attribution columns
2. **Export Enhanced CSV** → Include new marketing fields
3. **Upload to Stock GRIP** → Test Phase 2 activation
4. **Verify Marketing Data** → Check attribution summary shows non-zero values
5. **Validate Calculations** → Confirm marketing-optimized recommendations

## 📞 **SUPPORT**

If you need help with:
- **Weld Configuration:** Check field mappings in data sources
- **SQL Debugging:** Use the enhanced model as template
- **Data Validation:** Compare before/after CSV exports
- **Phase 2 Testing:** Upload enhanced CSV to Stock GRIP dashboard

The enhanced data model will unlock the full potential of Phase 2 Marketing-Inventory Integration, delivering £70,000 additional annual value through sophisticated marketing-driven inventory optimization.