"""
Live Data Processor for Stock GRIP
Processes live Weld data for optimization algorithms
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any
import os

class LiveDataProcessor:
    """Enhanced processor for live Weld data"""
    
    def __init__(self, file_path: str = None):
        self.file_path = file_path
        self.data = None
        self.processed_data = None
        self.logger = logging.getLogger(__name__)
        
    def load_data(self, file_path: str = None) -> bool:
        """Load and validate the live data CSV"""
        if file_path:
            self.file_path = file_path
            
        if not self.file_path:
            self.logger.error("No file path provided")
            return False
            
        try:
            # Load CSV with proper encoding
            self.data = pd.read_csv(self.file_path, encoding='utf-8-sig')
            
            # Remove BOM if present
            if self.data.columns[0].startswith('\ufeff'):
                self.data.columns = [col.replace('\ufeff', '') for col in self.data.columns]
            
            self.logger.info(f"Loaded {len(self.data)} records from {self.file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            return False
    
    def validate_data(self) -> List[str]:
        """Validate data quality and structure"""
        if self.data is None:
            return ["No data loaded"]
            
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
    
    def process_for_stock_grip(self) -> pd.DataFrame:
        """Process data for Stock GRIP optimization"""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        # Create processed dataframe
        processed = self.data.copy()
        
        # Core Stock GRIP fields
        processed['demand_velocity'] = processed['shopify_units_sold']
        processed['revenue'] = processed['shopify_revenue']
        processed['unit_price'] = processed.get('shopify_avg_selling_price', 
                                               processed['shopify_revenue'] / processed['shopify_units_sold'].replace(0, 1))
        
        # Marketing efficiency metrics
        processed['marketing_spend'] = processed.get('total_marketing_spend', 0).fillna(0)
        processed['attributed_revenue'] = processed.get('total_attributed_revenue', 0).fillna(0)
        processed['marketing_efficiency'] = np.where(
            processed['marketing_spend'] > 0,
            processed['attributed_revenue'] / processed['marketing_spend'],
            0
        )
        
        # Organic performance ratio
        processed['organic_ratio'] = np.where(
            processed['revenue'] > 0,
            processed.get('organic_revenue', 0) / processed['revenue'],
            0
        )
        
        # Safe Facebook ROAS calculation
        facebook_spend = processed.get('facebook_spend', pd.Series([0] * len(processed)))
        if isinstance(facebook_spend, pd.Series):
            facebook_spend = facebook_spend.fillna(0)
        else:
            facebook_spend = pd.Series([0] * len(processed))
            
        processed['facebook_roas'] = np.where(
            facebook_spend > 0,
            processed.get('facebook_attributed_revenue', 0) / facebook_spend,
            0
        )
        
        # Safe email efficiency calculation
        klaviyo_emails = processed.get('klaviyo_emails_sent', pd.Series([0] * len(processed)))
        if isinstance(klaviyo_emails, pd.Series):
            klaviyo_emails = klaviyo_emails.fillna(0)
        else:
            klaviyo_emails = pd.Series([0] * len(processed))
            
        processed['email_efficiency'] = np.where(
            klaviyo_emails > 0,
            processed.get('klaviyo_attributed_revenue', 0) / klaviyo_emails,
            0
        )
        
        # Product categorization
        processed['category_clean'] = processed.get('product_category', 'other').fillna('other')
        
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
            processed['attributed_revenue'] > processed.get('organic_revenue', 0)
        ).astype(int)
        
        processed['email_responsive'] = (
            processed.get('klaviyo_attributed_revenue', 0) > 0
        ).astype(int)
        
        self.processed_data = processed
        return processed
    
    def get_optimization_summary(self) -> Dict[str, Any]:
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
                self.processed_data.get('organic_revenue', pd.Series([0])).sum() / 
                max(self.processed_data['revenue'].sum(), 1)
            ),
            'high_performers': self.processed_data['high_performer'].sum(),
            'marketing_driven_products': self.processed_data['marketing_driven'].sum(),
            'email_responsive_products': self.processed_data['email_responsive'].sum(),
            'top_categories': self.processed_data['category_clean'].value_counts().to_dict(),
            'demand_distribution': self.processed_data['demand_category'].value_counts().to_dict()
        }
        
        return summary
    
    def prepare_for_gp_eims(self) -> pd.DataFrame:
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
    
    def prepare_for_mpc_rl_mobo(self) -> pd.DataFrame:
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

    @staticmethod
    def load_live_data_from_directory(data_dir: str = "data/live_data") -> Optional['LiveDataProcessor']:
        """Load the most recent live data file from directory"""
        if not os.path.exists(data_dir):
            return None
            
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        if not csv_files:
            return None
            
        # Get most recent file
        latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)
        
        processor = LiveDataProcessor(file_path)
        if processor.load_data():
            return processor
        return None