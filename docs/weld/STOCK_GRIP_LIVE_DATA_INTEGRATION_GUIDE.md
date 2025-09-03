# Stock GRIP Live Data Integration Guide

## Overview
This guide provides step-by-step instructions for exporting your Weld data models as CSV files and integrating them with the Stock GRIP Streamlit application for live data testing.

## Phase 1: Priority CSV Exports for Stock GRIP Testing

Based on your available Weld models, here's the recommended export priority for Stock GRIP integration:

### **Export Priority 1: Product Performance Aggregated** ✅ **CRITICAL**
**Model**: `Product_Performance_Aggregated`
**Purpose**: Core inventory optimization data for Stock GRIP
**Stock GRIP Integration**: Direct feed to GP-EIMS and MPC-RL-MOBO algorithms

**Export Configuration**:
```sql
-- Export from Product_Performance_Aggregated model
SELECT 
  date,
  product_id,
  product_name,
  product_category,
  product_sku,
  
  -- Core demand signals for Stock GRIP
  shopify_units_sold as units_sold,
  shopify_revenue as revenue_gbp,
  shopify_orders as order_count,
  shopify_avg_selling_price as unit_price_gbp,
  
  -- Marketing influence indicators
  total_marketing_spend as marketing_spend_gbp,
  total_attributed_revenue as attributed_revenue_gbp,
  total_attributed_units as attributed_units,
  
  -- Organic performance
  organic_revenue as organic_revenue_gbp,
  organic_units as organic_units,
  
  -- Channel performance
  facebook_spend as fb_spend_gbp,
  facebook_attributed_revenue as fb_revenue_gbp,
  klaviyo_attributed_revenue as email_revenue_gbp
FROM Product_Performance_Aggregated
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY date DESC, revenue_gbp DESC
```

**File Name**: `product_performance_live_data.csv`

### **Export Priority 2: Marketing Attribution Model** ✅ **HIGH VALUE**
**Model**: `Marketing_Attribution_Model`
**Purpose**: Customer journey and attribution analysis
**Stock GRIP Integration**: Demand forecasting with marketing influence

**Export Configuration**:
```sql
-- Export from Marketing_Attribution_Model
SELECT 
  date,
  shopify_order_id,
  customer_email,
  total_attributed_revenue as order_value_gbp,
  
  -- Attribution channels
  first_touch_channel,
  last_touch_channel,
  
  -- Channel attribution
  facebook_attributed_revenue as fb_attributed_gbp,
  klaviyo_attributed_revenue as email_attributed_gbp,
  
  -- Journey characteristics
  touchpoint_count,
  journey_duration_hours,
  
  -- Customer classification
  CASE 
    WHEN customer_email IN (
      SELECT customer_email 
      FROM Marketing_Attribution_Model 
      GROUP BY customer_email 
      HAVING COUNT(DISTINCT shopify_order_id) = 1
    ) THEN 'new_customer'
    WHEN customer_email IN (
      SELECT customer_email 
      FROM Marketing_Attribution_Model 
      GROUP BY customer_email 
      HAVING COUNT(DISTINCT shopify_order_id) BETWEEN 2 AND 5
    ) THEN 'returning_customer'
    ELSE 'loyal_customer'
  END as customer_segment
FROM Marketing_Attribution_Model
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY date DESC, total_attributed_revenue DESC
```

**File Name**: `marketing_attribution_live_data.csv`

### **Export Priority 3: Shopify Line Items** ✅ **SUPPORTING DATA**
**Model**: `Shopify_Line_item`
**Purpose**: Detailed product-level sales data
**Stock GRIP Integration**: Granular demand patterns

**Export Configuration**:
```sql
-- Export from Shopify_Line_item with order context
SELECT 
  DATE(sli.order_created_at) as date,
  sli.product_id,
  sli.title as product_name,
  sli.sku,
  sli.inferred_category as category,
  sli.quantity,
  sli.line_net_revenue as revenue_gbp,
  sli.price as unit_price_gbp,
  
  -- Order context (if available from joins)
  so.customer_email,
  so.order_date,
  so.total_price_gbp as order_total_gbp
FROM Shopify_Line_item sli
LEFT JOIN Shopify_Orders_model so ON sli.shopify_order_id = so.shopify_order_id
WHERE DATE(sli.order_created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY DATE(sli.order_created_at) DESC, sli.line_net_revenue DESC
```

**File Name**: `shopify_line_items_live_data.csv`

## Phase 2: Stock GRIP Streamlit Integration

### **Step 1: Prepare CSV Files**

1. **Export from Weld**:
   - Export each model using the SQL queries above
   - Save as CSV files with UTF-8 encoding
   - Ensure proper date formatting (YYYY-MM-DD)

2. **File Validation**:
   ```bash
   # Check file structure
   head -5 product_performance_live_data.csv
   
   # Verify data quality
   wc -l *.csv  # Check record counts
   ```

### **Step 2: Stock GRIP File Upload Process**

Based on the existing Stock GRIP structure, here's how to integrate your live data:

#### **Option A: Direct File Upload (Recommended for Testing)**

1. **Locate Stock GRIP Data Directory**:
   ```
   Stock_GRIP/
   ├── data/
   │   ├── live_data/          # Create this directory
   │   │   ├── product_performance_live_data.csv
   │   │   ├── marketing_attribution_live_data.csv
   │   │   └── shopify_line_items_live_data.csv
   │   └── csv_schemas/        # Existing schemas
   ```

2. **Upload Files**:
   - Place your exported CSV files in `data/live_data/`
   - Ensure file names match the expected format

#### **Option B: Streamlit File Uploader Integration**

Modify the Stock GRIP Streamlit app to include live data upload:

```python
# Add to app.py or create new live_data_app.py
import streamlit as st
import pandas as pd
from src.data.csv_ingestion import CSVDataProcessor

def live_data_upload_page():
    st.title("📊 Live Data Integration")
    st.markdown("Upload your Weld-exported CSV files for live Stock GRIP testing")
    
    # File uploaders
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Product Performance")
        product_file = st.file_uploader(
            "Upload Product Performance CSV",
            type=['csv'],
            key="product_performance"
        )
    
    with col2:
        st.subheader("Marketing Attribution")
        attribution_file = st.file_uploader(
            "Upload Marketing Attribution CSV",
            type=['csv'],
            key="marketing_attribution"
        )
    
    with col3:
        st.subheader("Shopify Line Items")
        shopify_file = st.file_uploader(
            "Upload Shopify Line Items CSV",
            type=['csv'],
            key="shopify_items"
        )
    
    # Process uploaded files
    if st.button("🚀 Process Live Data"):
        if product_file and attribution_file:
            try:
                # Load and validate data
                product_df = pd.read_csv(product_file)
                attribution_df = pd.read_csv(attribution_file)
                
                # Data quality checks
                st.success(f"✅ Product Performance: {len(product_df)} records loaded")
                st.success(f"✅ Marketing Attribution: {len(attribution_df)} records loaded")
                
                # Store in session state for Stock GRIP processing
                st.session_state['live_product_data'] = product_df
                st.session_state['live_attribution_data'] = attribution_df
                
                # Display preview
                st.subheader("📋 Data Preview")
                st.write("**Product Performance Data:**")
                st.dataframe(product_df.head())
                
                st.write("**Marketing Attribution Data:**")
                st.dataframe(attribution_df.head())
                
            except Exception as e:
                st.error(f"❌ Error processing files: {str(e)}")
        else:
            st.warning("⚠️ Please upload at least Product Performance and Marketing Attribution files")

# Add to main app navigation
def main():
    st.sidebar.title("Stock GRIP Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🏠 Home", "📊 Live Data Upload", "🎯 Optimization", "📈 Analytics"]
    )
    
    if page == "📊 Live Data Upload":
        live_data_upload_page()
    # ... other pages
```

### **Step 3: Stock GRIP Data Integration**

#### **Modify CSV Ingestion Pipeline**

Update the existing CSV ingestion to handle live data:

```python
# Add to src/data/csv_ingestion.py
class LiveDataProcessor(CSVDataProcessor):
    """Enhanced processor for live Weld data"""
    
    def process_live_product_performance(self, df):
        """Process Product Performance Aggregated data"""
        # Validate required columns
        required_cols = ['date', 'product_id', 'units_sold', 'revenue_gbp']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Data transformations
        df['date'] = pd.to_datetime(df['date'])
        df['demand_velocity'] = df['units_sold']
        df['revenue'] = df['revenue_gbp']
        
        # Calculate additional metrics for Stock GRIP
        df['marketing_efficiency'] = df['attributed_revenue_gbp'] / df['marketing_spend_gbp'].replace(0, 1)
        df['organic_ratio'] = df['organic_revenue_gbp'] / df['revenue_gbp']
        
        return df
    
    def process_live_attribution_data(self, df):
        """Process Marketing Attribution data"""
        df['date'] = pd.to_datetime(df['date'])
        
        # Customer journey metrics
        df['journey_complexity'] = pd.cut(
            df['touchpoint_count'], 
            bins=[0, 1, 3, 10], 
            labels=['simple', 'moderate', 'complex']
        )
        
        # Attribution confidence
        df['attribution_confidence'] = df.apply(
            lambda row: 0.9 if row['first_touch_channel'] == row['last_touch_channel'] else 0.7,
            axis=1
        )
        
        return df
```

#### **Integration with Stock GRIP Optimization**

```python
# Add to src/optimization/live_data_optimizer.py
class LiveDataOptimizer:
    """Stock GRIP optimizer using live Weld data"""
    
    def __init__(self, product_data, attribution_data):
        self.product_data = product_data
        self.attribution_data = attribution_data
    
    def prepare_optimization_data(self):
        """Prepare live data for GP-EIMS and MPC-RL-MOBO"""
        
        # Aggregate by product and date
        optimization_data = self.product_data.groupby(['product_id', 'date']).agg({
            'units_sold': 'sum',
            'revenue_gbp': 'sum',
            'marketing_spend_gbp': 'sum',
            'marketing_efficiency': 'mean',
            'organic_ratio': 'mean'
        }).reset_index()
        
        # Add demand forecasting features
        optimization_data['demand_trend'] = optimization_data.groupby('product_id')['units_sold'].pct_change()
        optimization_data['revenue_trend'] = optimization_data.groupby('product_id')['revenue_gbp'].pct_change()
        
        # Marketing influence indicators
        attribution_summary = self.attribution_data.groupby(['date']).agg({
            'fb_attributed_gbp': 'sum',
            'email_attributed_gbp': 'sum',
            'journey_duration_hours': 'mean',
            'touchpoint_count': 'mean'
        }).reset_index()
        
        # Merge with product data
        final_data = optimization_data.merge(
            attribution_summary, 
            on='date', 
            how='left'
        )
        
        return final_data
    
    def run_live_optimization(self):
        """Run Stock GRIP optimization with live data"""
        opt_data = self.prepare_optimization_data()
        
        # Initialize GP-EIMS with live data
        from src.optimization.gp_eims import GPEIMSOptimizer
        gp_optimizer = GPEIMSOptimizer(opt_data)
        
        # Run optimization
        results = gp_optimizer.optimize()
        
        return results
```

### **Step 4: Streamlit Dashboard Integration**

```python
# Add live data dashboard to app.py
def live_data_dashboard():
    st.title("🔴 Live Data Dashboard")
    
    if 'live_product_data' in st.session_state:
        product_data = st.session_state['live_product_data']
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_revenue = product_data['revenue_gbp'].sum()
            st.metric("Total Revenue", f"£{total_revenue:,.2f}")
        
        with col2:
            total_units = product_data['units_sold'].sum()
            st.metric("Total Units Sold", f"{total_units:,}")
        
        with col3:
            avg_marketing_efficiency = product_data['marketing_efficiency'].mean()
            st.metric("Avg Marketing ROI", f"{avg_marketing_efficiency:.2f}x")
        
        with col4:
            active_products = product_data['product_id'].nunique()
            st.metric("Active Products", active_products)
        
        # Charts
        st.subheader("📈 Performance Trends")
        
        # Daily revenue trend
        daily_revenue = product_data.groupby('date')['revenue_gbp'].sum().reset_index()
        st.line_chart(daily_revenue.set_index('date'))
        
        # Top products
        st.subheader("🏆 Top Performing Products")
        top_products = product_data.groupby('product_name')['revenue_gbp'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_products)
        
        # Run optimization
        if st.button("🚀 Run Live Optimization"):
            with st.spinner("Running Stock GRIP optimization..."):
                try:
                    optimizer = LiveDataOptimizer(
                        st.session_state['live_product_data'],
                        st.session_state.get('live_attribution_data', pd.DataFrame())
                    )
                    results = optimizer.run_live_optimization()
                    
                    st.success("✅ Optimization completed!")
                    st.json(results)
                    
                except Exception as e:
                    st.error(f"❌ Optimization failed: {str(e)}")
    else:
        st.warning("⚠️ No live data loaded. Please upload data first.")
```

## Phase 3: Testing and Validation

### **Data Quality Checks**

```python
def validate_live_data(df, data_type):
    """Validate uploaded live data"""
    issues = []
    
    # Check for required columns
    if data_type == 'product_performance':
        required = ['date', 'product_id', 'units_sold', 'revenue_gbp']
    elif data_type == 'attribution':
        required = ['date', 'shopify_order_id', 'total_attributed_revenue']
    
    missing = [col for col in required if col not in df.columns]
    if missing:
        issues.append(f"Missing columns: {missing}")
    
    # Check data types
    try:
        df['date'] = pd.to_datetime(df['date'])
    except:
        issues.append("Invalid date format")
    
    # Check for negative values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    negative_cols = [col for col in numeric_cols if (df[col] < 0).any()]
    if negative_cols:
        issues.append(f"Negative values in: {negative_cols}")
    
    return issues
```

### **Performance Monitoring**

```python
def monitor_live_data_performance():
    """Monitor live data processing performance"""
    metrics = {
        'data_freshness': (datetime.now() - last_update).total_seconds() / 3600,  # hours
        'record_count': len(st.session_state.get('live_product_data', [])),
        'processing_time': processing_duration,
        'error_rate': error_count / total_records if total_records > 0 else 0
    }
    
    return metrics
```

## Implementation Checklist

### **Phase 1: CSV Export** ✅
- [ ] Export Product_Performance_Aggregated as CSV
- [ ] Export Marketing_Attribution_Model as CSV  
- [ ] Export Shopify_Line_item as CSV (optional)
- [ ] Validate CSV file formats and data quality

### **Phase 2: Stock GRIP Integration** ✅
- [ ] Create live_data directory in Stock GRIP
- [ ] Add file upload functionality to Streamlit app
- [ ] Implement LiveDataProcessor class
- [ ] Create live data dashboard

### **Phase 3: Testing** ✅
- [ ] Upload test CSV files
- [ ] Validate data processing
- [ ] Run optimization with live data
- [ ] Monitor performance and errors

## Next Steps

1. **Start with Product_Performance_Aggregated export** - This is the most critical for Stock GRIP
2. **Test file upload in Streamlit** - Verify the integration works
3. **Run optimization with live data** - Validate Stock GRIP algorithms work with real data
4. **Monitor and iterate** - Refine based on performance and results

This integration will transform Stock GRIP from a simulation platform into a live, data-driven inventory optimization system using your real Shopify, Facebook, and Klaviyo data.