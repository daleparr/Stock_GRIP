"""
Data pipeline and preprocessing modules for Stock_GRIP
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import (
    Product, Inventory, Demand, OptimizationParameters,
    InventoryActions, PerformanceMetrics, get_session
)
from .live_data_processor import LiveDataProcessor
from config.settings import SIMULATION_CONFIG


class DataPipeline:
    """Enhanced data pipeline supporting both synthetic and live data"""
    
    def __init__(self, session: Session, data_source: str = 'live'):
        self.session = session
        self.data_source = data_source  # 'live' or 'synthetic'
        self.logger = logging.getLogger(__name__)
        self.live_processor = None
        
    def load_data(self, file_path: str = None) -> Optional[pd.DataFrame]:
        """Load data based on source type"""
        if self.data_source == 'live':
            return self.load_live_data(file_path)
        else:
            return self.load_synthetic_data()
    
    def load_live_data(self, file_path: str = None) -> Optional[pd.DataFrame]:
        """Load data from Weld CSV exports"""
        try:
            if file_path:
                self.live_processor = LiveDataProcessor(file_path)
            else:
                # Try to load from default directory
                self.live_processor = LiveDataProcessor.load_live_data_from_directory()
                
            if self.live_processor and self.live_processor.load_data():
                processed_data = self.live_processor.process_for_stock_grip()
                self.logger.info(f"Loaded {len(processed_data)} products from live data")
                return processed_data
            else:
                self.logger.error("Failed to load live data")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading live data: {str(e)}")
            return None
    
    def load_synthetic_data(self) -> Optional[pd.DataFrame]:
        """Load synthetic data (fallback for testing)"""
        # This would use the existing synthetic data generation
        # Keep for backward compatibility and testing
        self.logger.info("Loading synthetic data (fallback mode)")
        return None
    
    def validate_live_data_quality(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Validate live data meets Stock GRIP requirements"""
        if self.live_processor:
            issues = self.live_processor.validate_data()
            return {"validation_issues": issues}
        return {"validation_issues": ["No live data processor available"]}
    
    def get_optimization_summary(self) -> Optional[Dict[str, Any]]:
        """Get optimization summary from live data"""
        if self.live_processor:
            return self.live_processor.get_optimization_summary()
        return None


class DataValidator:
    """Validates data quality and consistency"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def validate_live_data(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Validate live Weld data"""
        issues = {
            "missing_data": [],
            "invalid_values": [],
            "data_quality": []
        }
        
        # Validate required columns
        required_columns = [
            'date', 'product_id', 'product_name', 'shopify_units_sold',
            'shopify_revenue', 'total_attributed_revenue'
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            issues["missing_data"].extend(missing_cols)
        
        # Validate data types and values
        try:
            df['date'] = pd.to_datetime(df['date'])
        except:
            issues["invalid_values"].append("Invalid date format")
        
        # Check for negative values
        numeric_cols = ['shopify_units_sold', 'shopify_revenue', 'total_attributed_revenue']
        for col in numeric_cols:
            if col in df.columns and (df[col] < 0).any():
                issues["invalid_values"].append(f"Negative values in {col}")
        
        # Check for null values in critical fields
        critical_fields = ['product_id', 'product_name']
        for field in critical_fields:
            if field in df.columns and df[field].isnull().any():
                issues["data_quality"].append(f"Null values in {field}")
        
        # Data quality checks
        if len(df) == 0:
            issues["data_quality"].append("Empty dataset")
        
        if 'shopify_revenue' in df.columns and 'shopify_units_sold' in df.columns:
            zero_revenue_with_sales = ((df['shopify_revenue'] == 0) & (df['shopify_units_sold'] > 0)).sum()
            if zero_revenue_with_sales > 0:
                issues["data_quality"].append(f"{zero_revenue_with_sales} products with sales but zero revenue")
        
        return issues

    def validate_product_data(self) -> Dict[str, List[str]]:
        """Validate product data integrity"""
        issues = {
            "missing_data": [],
            "invalid_values": [],
            "inconsistencies": []
        }
        
        products = self.session.query(Product).all()
        
        for product in products:
            # Check for missing required fields
            if not product.name or not product.category:
                issues["missing_data"].append(f"{product.product_id}: Missing name or category")
            
            # Check for invalid values
            if product.unit_cost <= 0:
                issues["invalid_values"].append(f"{product.product_id}: Invalid unit cost")
            
            if product.selling_price <= product.unit_cost:
                issues["invalid_values"].append(f"{product.product_id}: Selling price not greater than cost")
            
            if product.lead_time_days < 0:
                issues["invalid_values"].append(f"{product.product_id}: Negative lead time")
            
            if product.min_order_quantity > product.max_order_quantity:
                issues["inconsistencies"].append(f"{product.product_id}: Min order > Max order")
        
        return issues
    
    def validate_inventory_data(self) -> Dict[str, List[str]]:
        """Validate inventory data integrity"""
        issues = {
            "negative_stock": [],
            "inconsistent_calculations": [],
            "missing_products": []
        }
        
        # Get latest inventory for each product
        latest_inventory = self.session.query(Inventory).filter(
            Inventory.timestamp == self.session.query(func.max(Inventory.timestamp)).filter(
                Inventory.product_id == Inventory.product_id
            ).scalar_subquery()
        ).all()
        
        for inv in latest_inventory:
            # Check for negative stock
            if inv.stock_level < 0:
                issues["negative_stock"].append(f"{inv.product_id}: Negative stock level")
            
            # Check calculation consistency
            expected_available = inv.stock_level - inv.reserved_stock
            if abs(inv.available_stock - expected_available) > 0.1:
                issues["inconsistent_calculations"].append(
                    f"{inv.product_id}: Available stock calculation mismatch"
                )
            
            # Check if product exists
            product = self.session.query(Product).filter(Product.product_id == inv.product_id).first()
            if not product:
                issues["missing_products"].append(f"{inv.product_id}: Product not found")
        
        return issues
    
    def validate_demand_data(self) -> Dict[str, List[str]]:
        """Validate demand data integrity"""
        issues = {
            "negative_demand": [],
            "fulfillment_issues": [],
            "missing_products": [],
            "date_issues": []
        }
        
        # Check recent demand data
        recent_demand = self.session.query(Demand).filter(
            Demand.date >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        for demand in recent_demand:
            # Check for negative demand
            if demand.quantity_demanded < 0:
                issues["negative_demand"].append(f"{demand.product_id}: Negative demand")
            
            # Check fulfillment logic
            if demand.quantity_fulfilled > demand.quantity_demanded:
                issues["fulfillment_issues"].append(
                    f"{demand.product_id}: Fulfilled > Demanded on {demand.date}"
                )
            
            # Check if product exists
            product = self.session.query(Product).filter(Product.product_id == demand.product_id).first()
            if not product:
                issues["missing_products"].append(f"{demand.product_id}: Product not found")
            
            # Check date validity
            if demand.date > datetime.utcnow() and not demand.is_forecast:
                issues["date_issues"].append(f"{demand.product_id}: Future date for historical demand")
        
        return issues
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete data validation"""
        validation_results = {
            "timestamp": datetime.utcnow(),
            "product_issues": self.validate_product_data(),
            "inventory_issues": self.validate_inventory_data(),
            "demand_issues": self.validate_demand_data()
        }
        
        # Count total issues
        total_issues = 0
        for category, issues in validation_results.items():
            if isinstance(issues, dict):
                for issue_type, issue_list in issues.items():
                    total_issues += len(issue_list)
        
        validation_results["total_issues"] = total_issues
        validation_results["validation_passed"] = total_issues == 0
        
        return validation_results


class DataPreprocessor:
    """Preprocesses data for optimization algorithms"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def calculate_demand_statistics(self, product_id: str, days: int = 90) -> Dict[str, float]:
        """Calculate demand statistics for a product"""
        # Get historical demand
        demand_records = self.session.query(Demand).filter(
            Demand.product_id == product_id,
            Demand.is_forecast == False,
            Demand.date >= datetime.utcnow() - timedelta(days=days)
        ).order_by(Demand.date.desc()).all()
        
        if not demand_records:
            return {}
        
        demand_values = [d.quantity_demanded for d in demand_records]
        fulfilled_values = [d.quantity_fulfilled for d in demand_records]
        
        stats = {
            "mean_demand": np.mean(demand_values),
            "std_demand": np.std(demand_values),
            "max_demand": np.max(demand_values),
            "min_demand": np.min(demand_values),
            "median_demand": np.median(demand_values),
            "cv_demand": np.std(demand_values) / max(np.mean(demand_values), 1),  # Coefficient of variation
            "mean_fulfilled": np.mean(fulfilled_values),
            "fill_rate": np.mean(fulfilled_values) / max(np.mean(demand_values), 1),
            "total_demand": np.sum(demand_values),
            "total_fulfilled": np.sum(fulfilled_values),
            "demand_trend": self._calculate_trend(demand_values),
            "seasonality_factor": self._calculate_seasonality(demand_records)
        }
        
        return stats
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in demand data"""
        if len(values) < 3:
            return 0.0
        
        # Simple linear trend
        x = np.arange(len(values))
        trend = np.polyfit(x, values, 1)[0]
        return float(trend)
    
    def _calculate_seasonality(self, demand_records: List[Demand]) -> float:
        """Calculate seasonality factor"""
        if len(demand_records) < 14:
            return 1.0
        
        # Group by day of week
        weekday_demand = {}
        for record in demand_records:
            weekday = record.date.weekday()
            if weekday not in weekday_demand:
                weekday_demand[weekday] = []
            weekday_demand[weekday].append(record.quantity_demanded)
        
        # Calculate coefficient of variation across weekdays
        weekday_means = [np.mean(demands) for demands in weekday_demand.values()]
        if len(weekday_means) > 1:
            return np.std(weekday_means) / max(np.mean(weekday_means), 1)
        
        return 1.0
    
    def calculate_inventory_metrics(self, product_id: str) -> Dict[str, float]:
        """Calculate inventory performance metrics"""
        # Get recent inventory data
        inventory_records = self.session.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).order_by(Inventory.timestamp.desc()).all()
        
        if not inventory_records:
            return {}
        
        stock_levels = [inv.stock_level for inv in inventory_records]
        available_stock = [inv.available_stock for inv in inventory_records]
        
        # Get product info for calculations
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            return {}
        
        # Calculate turnover (simplified)
        demand_stats = self.calculate_demand_statistics(product_id, 30)
        avg_stock = np.mean(stock_levels)
        monthly_demand = demand_stats.get("total_demand", 0)
        
        metrics = {
            "avg_stock_level": avg_stock,
            "max_stock_level": np.max(stock_levels),
            "min_stock_level": np.min(stock_levels),
            "stock_volatility": np.std(stock_levels),
            "avg_available_stock": np.mean(available_stock),
            "inventory_turnover": monthly_demand / max(avg_stock, 1),
            "days_of_supply": avg_stock / max(demand_stats.get("mean_demand", 1), 1),
            "stockout_frequency": len([s for s in available_stock if s <= 0]) / len(available_stock)
        }
        
        return metrics
    
    def prepare_optimization_features(self, product_id: str) -> Dict[str, Any]:
        """Prepare feature set for optimization algorithms"""
        demand_stats = self.calculate_demand_statistics(product_id)
        inventory_metrics = self.calculate_inventory_metrics(product_id)
        
        # Get product information
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            return {}
        
        # Combine all features
        features = {
            "product_id": product_id,
            "category": product.category,
            "unit_cost": product.unit_cost,
            "selling_price": product.selling_price,
            "lead_time_days": product.lead_time_days,
            "shelf_life_days": product.shelf_life_days,
            "min_order_quantity": product.min_order_quantity,
            "max_order_quantity": product.max_order_quantity,
            **demand_stats,
            **inventory_metrics
        }
        
        # Calculate derived features
        if demand_stats and inventory_metrics:
            features["profit_margin"] = (product.selling_price - product.unit_cost) / product.selling_price
            features["demand_variability"] = demand_stats.get("cv_demand", 0)
            features["service_level"] = demand_stats.get("fill_rate", 0)
            features["inventory_efficiency"] = inventory_metrics.get("inventory_turnover", 0)
        
        return features
    
    def create_feature_matrix(self, product_ids: List[str] = None) -> pd.DataFrame:
        """Create feature matrix for all products or specified products"""
        if product_ids is None:
            products = self.session.query(Product).all()
            product_ids = [p.product_id for p in products]
        
        features_list = []
        for product_id in product_ids:
            features = self.prepare_optimization_features(product_id)
            if features:
                features_list.append(features)
        
        if not features_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(features_list)
        
        # Handle missing values
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        return df


class DataAggregator:
    """Aggregates data for reporting and analysis"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def aggregate_daily_metrics(self, date: datetime = None) -> Dict[str, Any]:
        """Aggregate daily performance metrics"""
        if date is None:
            date = datetime.utcnow().date()
        
        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Aggregate demand
        daily_demand = self.session.query(
            func.sum(Demand.quantity_demanded).label("total_demand"),
            func.sum(Demand.quantity_fulfilled).label("total_fulfilled"),
            func.count(Demand.id).label("demand_records")
        ).filter(
            Demand.date >= start_date,
            Demand.date < end_date,
            Demand.is_forecast == False
        ).first()
        
        # Aggregate inventory actions
        daily_actions = self.session.query(
            func.count(InventoryActions.id).label("total_actions"),
            func.sum(InventoryActions.quantity).label("total_quantity_ordered"),
            func.sum(InventoryActions.cost).label("total_cost")
        ).filter(
            InventoryActions.timestamp >= start_date,
            InventoryActions.timestamp < end_date
        ).first()
        
        # Calculate service level
        service_level = 0.0
        if daily_demand.total_demand and daily_demand.total_demand > 0:
            service_level = daily_demand.total_fulfilled / daily_demand.total_demand
        
        return {
            "date": date,
            "total_demand": daily_demand.total_demand or 0,
            "total_fulfilled": daily_demand.total_fulfilled or 0,
            "service_level": service_level,
            "total_actions": daily_actions.total_actions or 0,
            "total_quantity_ordered": daily_actions.total_quantity_ordered or 0,
            "total_cost": daily_actions.total_cost or 0.0,
            "demand_records": daily_demand.demand_records or 0
        }
    
    def aggregate_weekly_metrics(self, week_start: datetime = None) -> Dict[str, Any]:
        """Aggregate weekly performance metrics"""
        if week_start is None:
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=7)
        
        # Get daily metrics for the week
        daily_metrics = []
        current_date = week_start
        while current_date < week_end:
            daily_metric = self.aggregate_daily_metrics(current_date)
            daily_metrics.append(daily_metric)
            current_date += timedelta(days=1)
        
        # Aggregate weekly totals
        weekly_totals = {
            "week_start": week_start,
            "week_end": week_end,
            "total_demand": sum(d["total_demand"] for d in daily_metrics),
            "total_fulfilled": sum(d["total_fulfilled"] for d in daily_metrics),
            "total_actions": sum(d["total_actions"] for d in daily_metrics),
            "total_cost": sum(d["total_cost"] for d in daily_metrics),
            "avg_service_level": np.mean([d["service_level"] for d in daily_metrics]),
            "daily_metrics": daily_metrics
        }
        
        return weekly_totals
    
    def aggregate_product_performance(self, days: int = 30) -> pd.DataFrame:
        """Aggregate performance metrics by product"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all products
        products = self.session.query(Product).all()
        
        performance_data = []
        for product in products:
            # Demand metrics
            demand_data = self.session.query(
                func.sum(Demand.quantity_demanded).label("total_demand"),
                func.sum(Demand.quantity_fulfilled).label("total_fulfilled"),
                func.avg(Demand.quantity_demanded).label("avg_demand")
            ).filter(
                Demand.product_id == product.product_id,
                Demand.date >= start_date,
                Demand.is_forecast == False
            ).first()
            
            # Action metrics
            action_data = self.session.query(
                func.count(InventoryActions.id).label("total_actions"),
                func.sum(InventoryActions.quantity).label("total_ordered"),
                func.sum(InventoryActions.cost).label("total_cost")
            ).filter(
                InventoryActions.product_id == product.product_id,
                InventoryActions.timestamp >= start_date
            ).first()
            
            # Current inventory
            current_inventory = self.session.query(Inventory).filter(
                Inventory.product_id == product.product_id
            ).order_by(Inventory.timestamp.desc()).first()
            
            # Calculate metrics
            service_level = 0.0
            if demand_data.total_demand and demand_data.total_demand > 0:
                service_level = demand_data.total_fulfilled / demand_data.total_demand
            
            performance_data.append({
                "product_id": product.product_id,
                "category": product.category,
                "total_demand": demand_data.total_demand or 0,
                "total_fulfilled": demand_data.total_fulfilled or 0,
                "avg_demand": demand_data.avg_demand or 0,
                "service_level": service_level,
                "total_actions": action_data.total_actions or 0,
                "total_ordered": action_data.total_ordered or 0,
                "total_cost": action_data.total_cost or 0.0,
                "current_stock": current_inventory.stock_level if current_inventory else 0,
                "available_stock": current_inventory.available_stock if current_inventory else 0
            })
        
        return pd.DataFrame(performance_data)


class DataPipeline:
    """Main data pipeline orchestrator"""
    
    def __init__(self, session: Session):
        self.session = session
        self.validator = DataValidator(session)
        self.preprocessor = DataPreprocessor(session)
        self.aggregator = DataAggregator(session)
        self.logger = logging.getLogger(__name__)
    
    def run_data_quality_check(self) -> Dict[str, Any]:
        """Run comprehensive data quality check"""
        self.logger.info("Running data quality check...")
        
        validation_results = self.validator.run_full_validation()
        
        # Log results
        if validation_results["validation_passed"]:
            self.logger.info("Data quality check passed")
        else:
            self.logger.warning(f"Data quality issues found: {validation_results['total_issues']} issues")
        
        return validation_results
    
    def prepare_optimization_data(self, product_ids: List[str] = None) -> pd.DataFrame:
        """Prepare data for optimization algorithms"""
        self.logger.info("Preparing optimization data...")
        
        feature_matrix = self.preprocessor.create_feature_matrix(product_ids)
        
        self.logger.info(f"Prepared features for {len(feature_matrix)} products")
        return feature_matrix
    
    def generate_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        self.logger.info(f"Generating performance report for last {days} days...")
        
        # Daily aggregation
        daily_metrics = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            daily_metric = self.aggregator.aggregate_daily_metrics(date)
            daily_metrics.append(daily_metric)
        
        # Product performance
        product_performance = self.aggregator.aggregate_product_performance(days)
        
        # Overall metrics
        total_demand = sum(d["total_demand"] for d in daily_metrics)
        total_fulfilled = sum(d["total_fulfilled"] for d in daily_metrics)
        avg_service_level = np.mean([d["service_level"] for d in daily_metrics])
        total_cost = sum(d["total_cost"] for d in daily_metrics)
        
        report = {
            "report_period_days": days,
            "generated_at": datetime.utcnow(),
            "summary": {
                "total_demand": total_demand,
                "total_fulfilled": total_fulfilled,
                "overall_service_level": avg_service_level,
                "total_cost": total_cost,
                "products_analyzed": len(product_performance)
            },
            "daily_metrics": daily_metrics,
            "product_performance": product_performance.to_dict("records"),
            "top_performers": product_performance.nlargest(10, "service_level").to_dict("records"),
            "improvement_opportunities": product_performance.nsmallest(10, "service_level").to_dict("records")
        }
        
        self.logger.info("Performance report generated successfully")
        return report
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run complete data pipeline"""
        self.logger.info("Running full data pipeline...")
        
        pipeline_results = {
            "timestamp": datetime.utcnow(),
            "data_quality": self.run_data_quality_check(),
            "optimization_data_prepared": False,
            "performance_report_generated": False
        }
        
        try:
            # Prepare optimization data
            feature_matrix = self.prepare_optimization_data()
            pipeline_results["optimization_data_prepared"] = len(feature_matrix) > 0
            pipeline_results["products_processed"] = len(feature_matrix)
            
            # Generate performance report
            performance_report = self.generate_performance_report()
            pipeline_results["performance_report_generated"] = True
            pipeline_results["performance_summary"] = performance_report["summary"]
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            pipeline_results["error"] = str(e)
        
        self.logger.info("Data pipeline completed")
        return pipeline_results


def main():
    """Test data pipeline"""
    from config.settings import DATABASE_URL
    from .models import create_database
    
    engine = create_database(DATABASE_URL)
    session = get_session(engine)
    
    pipeline = DataPipeline(session)
    results = pipeline.run_full_pipeline()
    
    print(f"Pipeline results: {results}")
    
    session.close()


if __name__ == "__main__":
    main()