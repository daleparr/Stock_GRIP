# Stock GRIP Codebase Migration Plan: From Dummy Data to Live Data

## Overview
This document outlines the systematic migration from dummy/synthetic data to live Weld data integration, identifying what needs to be updated, removed, or enhanced in the existing codebase.

## Current Codebase Analysis

### **Files That Need Updates/Removal**

#### **1. Dummy Data Generation (REMOVE/REPLACE)**
- **File**: `src/data/data_generator.py`
- **Status**: ❌ **REMOVE** - No longer needed with live data
- **Reason**: Generates synthetic FMCG data that's replaced by real Weld data
- **Action**: Replace with live data processor

#### **2. Synthetic Data Pipeline (UPDATE)**
- **File**: `src/data/pipeline.py`
- **Status**: ⚠️ **UPDATE** - Modify for live data
- **Current**: Processes synthetic product/inventory/demand data
- **New**: Process live Shopify/Facebook/Klaviyo data
- **Action**: Enhance with live data validation and processing

#### **3. Main Application (UPDATE)**
- **File**: `app.py`
- **Status**: ⚠️ **UPDATE** - Add live data integration
- **Current**: Uses dummy data for demonstrations
- **New**: Integrate live data processing and optimization
- **Action**: Add live data upload and processing pages

### **Files That Stay (ENHANCE)**

#### **1. Core Models (ENHANCE)**
- **File**: `src/data/models.py`
- **Status**: ✅ **KEEP & ENHANCE**
- **Action**: Add live data models alongside existing ones

#### **2. Optimization Algorithms (ENHANCE)**
- **Files**: `src/optimization/gp_eims.py`, `src/optimization/mpc_rl_mobo.py`
- **Status**: ✅ **KEEP & ENHANCE**
- **Action**: Adapt to work with live data features

#### **3. Configuration (UPDATE)**
- **Files**: `config/settings.py`, `config/localization.py`
- **Status**: ✅ **KEEP & UPDATE**
- **Action**: Add live data configuration settings

## Migration Strategy

### **Phase 1: Remove Dummy Data Dependencies**

#### **Step 1.1: Identify Dummy Data Usage**
```python
# Files using synthetic data generation:
# 1. src/data/data_generator.py - REMOVE
# 2. test_stock_grip.py - UPDATE (use live data for tests)
# 3. app.py - UPDATE (remove synthetic data demos)
```

#### **Step 1.2: Create Live Data Alternatives**
```python
# Replace data_generator.py with:
# 1. src/data/live_data_processor.py - NEW
# 2. src/data/weld_data_loader.py - NEW
# 3. src/optimization/live_data_optimizer.py - NEW
```

### **Phase 2: Update Core Pipeline**

#### **Step 2.1: Enhance Data Pipeline**
```python
# src/data/pipeline.py - MODIFICATIONS NEEDED:

class DataPipeline:
    def __init__(self, session: Session, data_source='live'):  # ADD data_source parameter
        self.session = session
        self.data_source = data_source  # 'live' or 'synthetic'
        
    def load_data(self):
        if self.data_source == 'live':
            return self.load_live_data()  # NEW METHOD
        else:
            return self.load_synthetic_data()  # EXISTING METHOD
    
    def load_live_data(self):  # NEW METHOD
        """Load data from Weld CSV exports"""
        from .live_data_processor import LiveDataProcessor
        processor = LiveDataProcessor()
        return processor.load_and_process()
```

#### **Step 2.2: Update Data Validation**
```python
# src/data/pipeline.py - DataValidator class updates:

class DataValidator:
    def validate_live_data(self, df):  # NEW METHOD
        """Validate live Weld data"""
        issues = {
            "missing_data": [],
            "invalid_values": [],
            "data_quality": []
        }
        
        # Validate live data specific requirements
        required_columns = ['date', 'product_id', 'shopify_units_sold', 'shopify_revenue']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            issues["missing_data"].extend(missing_cols)
        
        return issues
```

### **Phase 3: Update Application Interface**

#### **Step 3.1: Modify Main App**
```python
# app.py - MAJOR UPDATES NEEDED:

# REMOVE these sections:
# - Synthetic data generation demos
# - Dummy product displays
# - Fake optimization results

# ADD these sections:
# - Live data upload interface
# - Real optimization results
# - Actual performance metrics

def main():
    st.sidebar.title("Stock GRIP Navigation")
    
    # UPDATE navigation options
    page = st.sidebar.selectbox(
        "Choose a page",
        [
            "🏠 Home",
            "📊 Live Data Upload",      # NEW
            "🔴 Live Data Analysis",    # NEW
            "🎯 Live Optimization",     # UPDATED
            "📈 Performance Analytics", # UPDATED
            "⚙️ System Settings"       # EXISTING
        ]
    )
    
    # REMOVE old synthetic data pages
    # ADD new live data pages
```

#### **Step 3.2: Create New Live Data Pages**
```python
# app.py - NEW FUNCTIONS TO ADD:

def live_data_upload_page():
    """Upload and validate live Weld data"""
    # File upload interface
    # Data validation display
    # Processing status

def live_data_analysis_page():
    """Analyze uploaded live data"""
    # Data quality metrics
    # Performance insights
    # Optimization readiness

def live_optimization_page():
    """Run optimization with live data"""
    # GP-EIMS results
    # MPC-RL-MOBO recommendations
    # Unified insights
```

### **Phase 4: Update Testing Framework**

#### **Step 4.1: Modify Test Files**
```python
# test_stock_grip.py - UPDATES NEEDED:

class TestStockGRIPLive:  # NEW TEST CLASS
    def setUp(self):
        # Use live data samples instead of synthetic
        self.live_data_path = "data/live_data/test_sample.csv"
        
    def test_live_data_processing(self):
        """Test live data processing pipeline"""
        # Test with actual Weld data structure
        
    def test_live_optimization(self):
        """Test optimization with live data"""
        # Validate optimization results with real data
```

#### **Step 4.2: Create Live Data Test Samples**
```python
# Create test data files:
# - data/live_data/test_product_performance.csv
# - data/live_data/test_marketing_attribution.csv
# - data/live_data/test_shopify_line_items.csv
```

## Detailed Migration Steps

### **Step 1: Remove Dummy Data Generator**

```bash
# 1. Backup current data_generator.py
mv src/data/data_generator.py src/data/data_generator_backup.py

# 2. Create new live data processor
# (Use implementation from LIVE_DATA_PROCESSING_IMPLEMENTATION.md)
```

### **Step 2: Update Pipeline for Live Data**

```python
# src/data/pipeline.py - ADD these methods:

class DataPipeline:
    def process_live_weld_data(self, file_path):
        """Process live Weld CSV data"""
        from .live_data_processor import LiveDataProcessor
        
        processor = LiveDataProcessor(file_path)
        if processor.load_data():
            processed_data = processor.process_for_stock_grip()
            return processed_data
        return None
    
    def validate_live_data_quality(self, df):
        """Validate live data meets Stock GRIP requirements"""
        validator = DataValidator(self.session)
        return validator.validate_live_data(df)
```

### **Step 3: Update Main Application**

```python
# app.py - REPLACE synthetic data sections with:

# OLD (REMOVE):
if st.button("Generate Synthetic Data"):
    generator = FMCGDataGenerator(DATABASE_URL)
    generator.generate_products(50)

# NEW (ADD):
if st.button("Process Live Data"):
    processor = LiveDataProcessor(uploaded_file)
    results = processor.process_for_stock_grip()
    st.success(f"Processed {len(results)} products")
```

### **Step 4: Update Configuration**

```python
# config/settings.py - ADD live data settings:

# Live Data Configuration
LIVE_DATA_CONFIG = {
    'data_directory': 'data/live_data/',
    'supported_formats': ['csv'],
    'max_file_size_mb': 100,
    'required_columns': {
        'product_performance': [
            'date', 'product_id', 'product_name', 
            'shopify_units_sold', 'shopify_revenue'
        ],
        'marketing_attribution': [
            'date', 'shopify_order_id', 'customer_email',
            'total_attributed_revenue'
        ]
    }
}

# Update existing config
DASHBOARD_CONFIG.update({
    'data_source': 'live',  # 'live' or 'synthetic'
    'live_data_refresh_interval': 3600,  # 1 hour
    'show_synthetic_options': False
})
```

## Migration Checklist

### **Phase 1: Preparation** ✅
- [ ] Backup existing codebase
- [ ] Create migration branch in git
- [ ] Document current functionality
- [ ] Test current system works

### **Phase 2: Core Updates** ⚠️
- [ ] Create `src/data/live_data_processor.py`
- [ ] Create `src/optimization/live_data_optimizer.py`
- [ ] Update `src/data/pipeline.py` for live data
- [ ] Update `config/settings.py` with live data config

### **Phase 3: Application Updates** ⚠️
- [ ] Remove synthetic data generation from `app.py`
- [ ] Add live data upload interface
- [ ] Add live data analysis page
- [ ] Update optimization pages for live data

### **Phase 4: Testing** ⚠️
- [ ] Update `test_stock_grip.py` for live data
- [ ] Create live data test samples
- [ ] Test end-to-end live data flow
- [ ] Validate optimization results

### **Phase 5: Cleanup** ⚠️
- [ ] Remove `src/data/data_generator.py`
- [ ] Remove synthetic data references
- [ ] Update documentation
- [ ] Clean up unused imports

## Risk Mitigation

### **Backward Compatibility**
```python
# Keep synthetic data option for development/testing
class DataPipeline:
    def __init__(self, session: Session, data_source='live'):
        self.data_source = data_source
        
    def load_data(self):
        if self.data_source == 'live':
            return self.load_live_data()
        elif self.data_source == 'synthetic':
            return self.load_synthetic_data()  # Keep for testing
```

### **Gradual Migration**
```python
# Feature flag for live data
ENABLE_LIVE_DATA = True

if ENABLE_LIVE_DATA:
    # Use live data processing
    pass
else:
    # Fall back to synthetic data
    pass
```

### **Data Validation**
```python
# Comprehensive validation before removing synthetic data
def validate_live_data_completeness():
    """Ensure live data provides all required features"""
    required_features = [
        'demand_velocity', 'revenue', 'marketing_efficiency',
        'organic_ratio', 'product_categories'
    ]
    # Validate all features are available in live data
```

## Expected Benefits After Migration

### **Immediate Benefits**
- ✅ **Real business insights** instead of synthetic patterns
- ✅ **Actual optimization results** for real products
- ✅ **Live performance tracking** with real metrics
- ✅ **Authentic user experience** with real data

### **Long-term Benefits**
- ✅ **Production-ready system** with real data pipeline
- ✅ **Scalable architecture** for continuous data updates
- ✅ **Business value delivery** with actionable insights
- ✅ **Customer confidence** in optimization recommendations

## Timeline

### **Week 1: Core Migration**
- Remove dummy data dependencies
- Implement live data processor
- Update pipeline for live data

### **Week 2: Application Updates**
- Update Streamlit interface
- Add live data upload/analysis
- Test end-to-end functionality

### **Week 3: Testing & Cleanup**
- Comprehensive testing with live data
- Remove synthetic data code
- Documentation updates

**The migration transforms Stock GRIP from a demo system to a production-ready, live data-driven inventory optimization platform.**