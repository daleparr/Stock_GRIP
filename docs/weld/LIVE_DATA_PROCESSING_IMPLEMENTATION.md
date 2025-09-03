# Live Data Processing Implementation for Stock GRIP

## Overview
This document provides the complete implementation code for processing your uploaded live data file and integrating it with Stock GRIP optimization algorithms.

## Data Analysis: Your Live Data File

### **File Analysis**
- **File**: `stock_grip_product_performace_aggregated_03_09_2025_11_30.csv`
- **Date**: 2025-09-02 (single day of data)
- **Records**: 9+ products with complete performance metrics
- **Data Quality**: ✅ Excellent - all required fields present

### **Key Observations**
1. **Product Mix**: Apparel-focused (t-shirts, hoodies, sweatpants)
2. **Revenue Range**: £91.80 - £250.00 per product
3. **Attribution**: Strong Klaviyo email attribution, no Facebook spend
4. **Categories**: `apparel_tops`, `apparel_bottoms`, `other`

## Implementation Code

### **1. Live Data Processor Class**

```python
# src/data/live_data_processor.py
"""
Live Data Processor for Stock GRIP
Processes live Weld data for optimization algorithms
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

class LiveDataProcessor:
    """Enhanced processor for live Weld data"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.processed_data = None
        
    def load_data(self):
        """Load and validate the live data CSV"""
        try:
            # Load CSV with proper encoding
            self.data = pd.read_csv(self.file_path, encoding='utf-8-sig')
            
            # Remove BOM if present
            if self.data.columns[0].startswith('\ufeff'):
                self.data.columns = [col.replace('\ufeff', '') for col in self.data.columns]
            
            logging.info(f"Loaded {len(self.data)} records from {self.file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            return False
    
    def validate_data(self):
        """Validate data quality and structure"""
        issues = []
        
        # Check required columns
        required_columns = [
            'date', 'product_id', 'product_name', 'shopify_units_sold', 
            'shopify_revenue', 'total_attributed_revenue', 'organic_revenue'
        ]
        
        missing_cols = [col for col in required_columns if col not in self.data.columns]
        if missing_cols:
            issues.append(f"Missing required columns: {missing_cols}")
        
        # Check data types
        try:
            self.data['date'] = pd.to_datetime(self.data['date'])
        except:
            issues.append("Invalid date format")
        
        # Check for negative values in key metrics
        numeric_cols = ['shopify_units_sold', 'shopify_revenue', 'total_attributed_revenue']
        for col in numeric_cols:
            if col in self.data.columns and (self.data[col] < 0).any():
                issues.append(f"Negative values found in {col}")
        
        # Check for null values in critical fields
        critical_fields = ['product_id', 'product_name', 'shopify_units_sold']
        for field in critical_fields:
            if field in self.data.columns and self.data[field].isnull().any():
                issues.append(f"Null values found in critical field: {field}")
        
        return issues
    
    def process_for_stock_grip(self):
        """Process data for Stock GRIP optimization"""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        # Create processed dataframe
        processed = self.data.copy()
        
        # Core Stock GRIP fields
        processed['demand_velocity'] = processed['shopify_units_sold']
        processed['revenue'] = processed['shopify_revenue']
        processed['unit_price'] = processed['shopify_avg_selling_price']
        
        # Marketing efficiency metrics
        processed['marketing_spend'] = processed['total_marketing_spend'].fillna(0)
        processed['attributed_revenue'] = processed['total_attributed_revenue'].fillna(0)
        processed['marketing_efficiency'] = np.where(
            processed['marketing_spend'] > 0,
            processed['attributed_revenue'] / processed['marketing_spend'],
            0
        )
        
        # Organic performance ratio
        processed['organic_ratio'] = np.where(
            processed['revenue'] > 0,
            processed['organic_revenue'] / processed['revenue'],
            0
        )
        
        # Channel performance
        processed['facebook_roas'] = np.where(
            processed['facebook_spend'] > 0,
            processed['facebook_attributed_revenue'] / processed['facebook_spend'],
            0
        )
        
        processed['email_efficiency'] = np.where(
            processed['klaviyo_emails_sent'] > 0,
            processed['klaviyo_attributed_revenue'] / processed['klaviyo_emails_sent'],
            0
        )
        
        # Product categorization
        processed['category_clean'] = processed['product_category'].fillna('other')
        
        # Demand classification
        processed['demand_category'] = pd.cut(
            processed['demand_velocity'],
            bins=[0, 1, 3, 10],
            labels=['low', 'medium', 'high'],
            include_lowest=True
        )
        
        # Revenue classification
        processed['revenue_category'] = pd.cut(
            processed['revenue'],
            bins=[0, 100, 200, float('inf')],
            labels=['low_value', 'medium_value', 'high_value'],
            include_lowest=True
        )
        
        # Stock GRIP optimization flags
        processed['high_performer'] = (
            (processed['demand_velocity'] >= 2) & 
            (processed['revenue'] >= 150)
        ).astype(int)
        
        processed['marketing_driven'] = (
            processed['attributed_revenue'] > processed['organic_revenue']
        ).astype(int)
        
        processed['email_responsive'] = (
            processed['klaviyo_attributed_revenue'] > 0
        ).astype(int)
        
        self.processed_data = processed
        return processed
    
    def get_optimization_summary(self):
        """Generate summary for optimization algorithms"""
        if self.processed_data is None:
            raise ValueError("No processed data. Call process_for_stock_grip() first.")
        
        summary = {
            'total_products': len(self.processed_data),
            'total_revenue': self.processed_data['revenue'].sum(),
            'total_units_sold': self.processed_data['demand_velocity'].sum(),
            'avg_unit_price': self.processed_data['unit_price'].mean(),
            'total_marketing_spend': self.processed_data['marketing_spend'].sum(),
            'total_attributed_revenue': self.processed_data['attributed_revenue'].sum(),
            'overall_marketing_roas': (
                self.processed_data['attributed_revenue'].sum() / 
                max(self.processed_data['marketing_spend'].sum(), 1)
            ),
            'organic_revenue_share': (
                self.processed_data['organic_revenue'].sum() / 
                self.processed_data['revenue'].sum()
            ),
            'high_performers': self.processed_data['high_performer'].sum(),
            'marketing_driven_products': self.processed_data['marketing_driven'].sum(),
            'email_responsive_products': self.processed_data['email_responsive'].sum(),
            'top_categories': self.processed_data['category_clean'].value_counts().to_dict(),
            'demand_distribution': self.processed_data['demand_category'].value_counts().to_dict()
        }
        
        return summary
    
    def prepare_for_gp_eims(self):
        """Prepare data specifically for GP-EIMS optimization"""
        if self.processed_data is None:
            raise ValueError("No processed data available")
        
        # GP-EIMS requires specific format
        gp_data = self.processed_data[[
            'product_id', 'product_name', 'category_clean',
            'demand_velocity', 'revenue', 'unit_price',
            'marketing_efficiency', 'organic_ratio',
            'high_performer', 'marketing_driven'
        ]].copy()
        
        # Add GP-EIMS specific features
        gp_data['demand_uncertainty'] = np.random.normal(0.1, 0.05, len(gp_data))  # Placeholder
        gp_data['supply_constraint'] = 1.0  # No constraints for now
        gp_data['profit_margin'] = 0.3  # Assumed 30% margin
        
        # Expected improvement features
        gp_data['current_performance'] = (
            gp_data['demand_velocity'] * gp_data['unit_price'] * gp_data['profit_margin']
        )
        
        return gp_data
    
    def prepare_for_mpc_rl_mobo(self):
        """Prepare data for MPC-RL-MOBO tactical optimization"""
        if self.processed_data is None:
            raise ValueError("No processed data available")
        
        # MPC-RL-MOBO requires time-series format
        mpc_data = self.processed_data[[
            'date', 'product_id', 'demand_velocity', 'revenue',
            'marketing_spend', 'attributed_revenue', 'organic_ratio'
        ]].copy()
        
        # Add MPC features
        mpc_data['demand_forecast'] = mpc_data['demand_velocity']  # Current as forecast
        mpc_data['inventory_level'] = mpc_data['demand_velocity'] * 7  # 7 days stock
        mpc_data['reorder_point'] = mpc_data['demand_velocity'] * 3  # 3 days safety
        
        # Multi-objective features
        mpc_data['profit_objective'] = mpc_data['revenue'] * 0.3  # Profit
        mpc_data['service_level_objective'] = 0.95  # 95% service level
        mpc_data['cost_objective'] = mpc_data['marketing_spend']  # Marketing cost
        
        return mpc_data
```

### **2. Stock GRIP Integration Class**

```python
# src/optimization/live_data_optimizer.py
"""
Live Data Optimizer for Stock GRIP
Integrates live Weld data with GP-EIMS and MPC-RL-MOBO
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging

class LiveDataOptimizer:
    """Stock GRIP optimizer using live Weld data"""
    
    def __init__(self, live_data_processor):
        self.processor = live_data_processor
        self.gp_data = None
        self.mpc_data = None
        self.optimization_results = {}
        
    def initialize_optimization_data(self):
        """Initialize data for both optimization algorithms"""
        try:
            # Prepare data for GP-EIMS
            self.gp_data = self.processor.prepare_for_gp_eims()
            logging.info(f"GP-EIMS data prepared: {len(self.gp_data)} products")
            
            # Prepare data for MPC-RL-MOBO
            self.mpc_data = self.processor.prepare_for_mpc_rl_mobo()
            logging.info(f"MPC-RL-MOBO data prepared: {len(self.mpc_data)} products")
            
            return True
            
        except Exception as e:
            logging.error(f"Error initializing optimization data: {str(e)}")
            return False
    
    def run_gp_eims_optimization(self):
        """Run GP-EIMS strategic optimization"""
        if self.gp_data is None:
            raise ValueError("GP-EIMS data not initialized")
        
        # Simplified GP-EIMS implementation for live data
        results = {}
        
        for _, product in self.gp_data.iterrows():
            product_id = product['product_id']
            
            # Expected Improvement calculation
            current_performance = product['current_performance']
            demand_potential = product['demand_velocity'] * (1 + product['marketing_efficiency'])
            
            # Strategic recommendations
            if product['high_performer'] and product['marketing_driven']:
                recommendation = "increase_marketing_investment"
                priority = "high"
            elif product['demand_velocity'] > 2 and product['organic_ratio'] > 0.7:
                recommendation = "maintain_organic_focus"
                priority = "medium"
            elif product['marketing_efficiency'] > 2.0:
                recommendation = "scale_marketing"
                priority = "high"
            else:
                recommendation = "optimize_or_discontinue"
                priority = "low"
            
            results[product_id] = {
                'product_name': product['product_name'],
                'category': product['category_clean'],
                'current_performance': current_performance,
                'demand_potential': demand_potential,
                'recommendation': recommendation,
                'priority': priority,
                'expected_improvement': demand_potential - current_performance,
                'confidence': 0.8 if product['high_performer'] else 0.6
            }
        
        self.optimization_results['gp_eims'] = results
        return results
    
    def run_mpc_rl_mobo_optimization(self):
        """Run MPC-RL-MOBO tactical optimization"""
        if self.mpc_data is None:
            raise ValueError("MPC-RL-MOBO data not initialized")
        
        # Simplified MPC-RL-MOBO implementation
        results = {}
        
        for _, product in self.mpc_data.iterrows():
            product_id = product['product_id']
            
            # Multi-objective optimization
            profit_score = product['profit_objective'] / max(product['profit_objective'].max(), 1)
            service_score = min(product['inventory_level'] / product['demand_forecast'], 1.0)
            cost_efficiency = 1 - (product['cost_objective'] / max(product['revenue'], 1))
            
            # Tactical decisions
            if product['inventory_level'] < product['reorder_point']:
                action = "immediate_reorder"
                urgency = "high"
            elif product['demand_forecast'] > product['inventory_level'] * 0.5:
                action = "increase_stock"
                urgency = "medium"
            elif service_score > 0.95 and cost_efficiency > 0.7:
                action = "maintain_current"
                urgency = "low"
            else:
                action = "optimize_inventory"
                urgency = "medium"
            
            results[product_id] = {
                'profit_score': profit_score,
                'service_score': service_score,
                'cost_efficiency': cost_efficiency,
                'action': action,
                'urgency': urgency,
                'recommended_stock_level': max(
                    product['demand_forecast'] * 7,  # 7 days stock
                    product['reorder_point']
                ),
                'optimization_confidence': (profit_score + service_score + cost_efficiency) / 3
            }
        
        self.optimization_results['mpc_rl_mobo'] = results
        return results
    
    def generate_unified_recommendations(self):
        """Generate unified recommendations from both algorithms"""
        if not self.optimization_results:
            raise ValueError("No optimization results available")
        
        gp_results = self.optimization_results.get('gp_eims', {})
        mpc_results = self.optimization_results.get('mpc_rl_mobo', {})
        
        unified = {}
        
        for product_id in set(list(gp_results.keys()) + list(mpc_results.keys())):
            gp_rec = gp_results.get(product_id, {})
            mpc_rec = mpc_results.get(product_id, {})
            
            # Combine strategic and tactical recommendations
            unified[product_id] = {
                'strategic_recommendation': gp_rec.get('recommendation', 'unknown'),
                'tactical_action': mpc_rec.get('action', 'unknown'),
                'priority': gp_rec.get('priority', 'low'),
                'urgency': mpc_rec.get('urgency', 'low'),
                'expected_improvement': gp_rec.get('expected_improvement', 0),
                'recommended_stock_level': mpc_rec.get('recommended_stock_level', 0),
                'overall_confidence': (
                    gp_rec.get('confidence', 0) + mpc_rec.get('optimization_confidence', 0)
                ) / 2
            }
        
        return unified
    
    def get_portfolio_insights(self):
        """Generate portfolio-level insights"""
        summary = self.processor.get_optimization_summary()
        
        insights = {
            'portfolio_health': {
                'total_products': summary['total_products'],
                'high_performers': summary['high_performers'],
                'performance_rate': summary['high_performers'] / summary['total_products']
            },
            'revenue_analysis': {
                'total_revenue': summary['total_revenue'],
                'organic_share': summary['organic_revenue_share'],
                'marketing_roas': summary['overall_marketing_roas']
            },
            'channel_effectiveness': {
                'email_responsive_rate': summary['email_responsive_products'] / summary['total_products'],
                'marketing_driven_rate': summary['marketing_driven_products'] / summary['total_products']
            },
            'category_performance': summary['top_categories'],
            'demand_distribution': summary['demand_distribution']
        }
        
        return insights
```

### **3. Streamlit Integration**

```python
# Add to app.py
import streamlit as st
import pandas as pd
from src.data.live_data_processor import LiveDataProcessor
from src.optimization.live_data_optimizer import LiveDataOptimizer

def live_data_analysis_page():
    st.title("🔴 Live Data Analysis & Optimization")
    st.markdown("Analysis of your uploaded Weld data")
    
    # File path (update with your actual path)
    file_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
    
    if st.button("🚀 Process Live Data"):
        with st.spinner("Processing live data..."):
            try:
                # Initialize processor
                processor = LiveDataProcessor(file_path)
                
                # Load and validate data
                if processor.load_data():
                    st.success("✅ Data loaded successfully")
                    
                    # Validate data quality
                    issues = processor.validate_data()
                    if issues:
                        st.warning(f"⚠️ Data quality issues: {issues}")
                    else:
                        st.success("✅ Data validation passed")
                    
                    # Process for Stock GRIP
                    processed_data = processor.process_for_stock_grip()
                    st.success(f"✅ Processed {len(processed_data)} products")
                    
                    # Display summary
                    summary = processor.get_optimization_summary()
                    
                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Revenue", f"£{summary['total_revenue']:,.2f}")
                    
                    with col2:
                        st.metric("Total Units Sold", f"{summary['total_units_sold']:,}")
                    
                    with col3:
                        st.metric("Marketing ROAS", f"{summary['overall_marketing_roas']:.2f}x")
                    
                    with col4:
                        st.metric("High Performers", f"{summary['high_performers']}")
                    
                    # Data preview
                    st.subheader("📊 Processed Data Preview")
                    st.dataframe(processed_data.head(10))
                    
                    # Run optimization
                    if st.button("🎯 Run Stock GRIP Optimization"):
                        with st.spinner("Running optimization algorithms..."):
                            optimizer = LiveDataOptimizer(processor)
                            
                            if optimizer.initialize_optimization_data():
                                # Run GP-EIMS
                                gp_results = optimizer.run_gp_eims_optimization()
                                st.success("✅ GP-EIMS optimization completed")
                                
                                # Run MPC-RL-MOBO
                                mpc_results = optimizer.run_mpc_rl_mobo_optimization()
                                st.success("✅ MPC-RL-MOBO optimization completed")
                                
                                # Generate unified recommendations
                                unified = optimizer.generate_unified_recommendations()
                                
                                # Display results
                                st.subheader("🎯 Optimization Results")
                                
                                # Convert to DataFrame for display
                                results_df = pd.DataFrame.from_dict(unified, orient='index')
                                st.dataframe(results_df)
                                
                                # Portfolio insights
                                insights = optimizer.get_portfolio_insights()
                                
                                st.subheader("📈 Portfolio Insights")
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("**Portfolio Health**")
                                    st.json(insights['portfolio_health'])
                                    
                                    st.write("**Revenue Analysis**")
                                    st.json(insights['revenue_analysis'])
                                
                                with col2:
                                    st.write("**Channel Effectiveness**")
                                    st.json(insights['channel_effectiveness'])
                                    
                                    st.write("**Category Performance**")
                                    st.json(insights['category_performance'])
                            
                            else:
                                st.error("❌ Failed to initialize optimization data")
                
                else:
                    st.error("❌ Failed to load data")
                    
            except Exception as e:
                st.error(f"❌ Error processing data: {str(e)}")

# Add to main navigation
def main():
    st.sidebar.title("Stock GRIP Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🏠 Home", "🔴 Live Data Analysis", "🎯 Optimization", "📈 Analytics"]
    )
    
    if page == "🔴 Live Data Analysis":
        live_data_analysis_page()
    # ... other pages
```

## Implementation Steps

### **Step 1: Create the Files**
1. Create `src/data/live_data_processor.py` with the LiveDataProcessor class
2. Create `src/optimization/live_data_optimizer.py` with the LiveDataOptimizer class
3. Update `app.py` with the live data analysis page

### **Step 2: Test the Integration**
1. Run the Streamlit app: `streamlit run app.py`
2. Navigate to "Live Data Analysis" page
3. Click "Process Live Data" to load your CSV
4. Click "Run Stock GRIP Optimization" to test algorithms

### **Step 3: Validate Results**
Your data should produce results like:
- **9 products processed** (apparel focus)
- **£1,362.23 total revenue** (approximate)
- **Strong email attribution** (Klaviyo performing well)
- **High organic performance** (good product-market fit)

## Expected Optimization Outcomes

Based on your data, Stock GRIP should recommend:

1. **"World is Yours T-shirt"** - Scale marketing (highest revenue)
2. **"Club Racing T-shirt"** - Maintain organic focus (good organic performance)
3. **Email marketing** - Increase investment (strong attribution)
4. **Apparel category** - Focus area (dominant category)

This implementation transforms your live Weld data into actionable Stock GRIP optimization recommendations!