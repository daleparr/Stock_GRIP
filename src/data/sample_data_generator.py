"""
Generate Sample CSV Files for Testing Live Data Integration
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from pathlib import Path
from typing import List, Dict, Any
import json

from .models import Product, get_session, create_database
from config.settings import DATABASE_URL, PRODUCT_CATEGORIES


class SampleDataGenerator:
    """Generate realistic sample CSV files for testing"""
    
    def __init__(self):
        self.output_dir = Path("data/live_feeds")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get existing products from database
        self.products = self._get_products()
        
        # Sample data parameters
        self.channels = ['online', 'pos', 'marketplace', 'wholesale']
        self.customer_segments = ['premium', 'regular', 'budget']
        self.fulfillment_methods = ['warehouse', 'store_pickup', 'dropship']
        self.locations = ['warehouse_a', 'warehouse_b', 'store_01', 'store_02', 'store_03']
        self.suppliers = ['SUP001', 'SUP002', 'SUP003', 'SUP004', 'SUP005']
        self.weather_factors = ['hot', 'cold', 'rainy', 'normal']
        self.event_impacts = ['promotion', 'holiday', 'none']
        self.demand_levels = ['high', 'medium', 'low']
    
    def _get_products(self) -> List[Product]:
        """Get products from database"""
        try:
            engine = create_database(DATABASE_URL)
            session = get_session(engine)
            products = session.query(Product).all()
            session.close()
            return products
        except Exception as e:
            print(f"Warning: Could not load products from database: {e}")
            return self._create_sample_products()
    
    def _create_sample_products(self) -> List[Product]:
        """Create sample products if database is not available"""
        products = []
        for i, (category, config) in enumerate(PRODUCT_CATEGORIES.items()):
            for j in range(5):  # 5 products per category
                product_id = f"{category[:3].upper()}-{j:04d}"
                unit_cost = np.random.uniform(*config["unit_cost_range"])
                
                product = type('Product', (), {
                    'product_id': product_id,
                    'category': category,
                    'unit_cost': unit_cost,
                    'selling_price': unit_cost * np.random.uniform(1.3, 2.5),
                    'lead_time_days': np.random.randint(*config["lead_time_range"])
                })()
                
                products.append(product)
        
        return products
    
    def generate_sales_csv(self, date: datetime = None, num_records: int = 100) -> str:
        """Generate sample sales CSV file"""
        if date is None:
            date = datetime.utcnow().date()
        
        sales_data = []
        
        for _ in range(num_records):
            product = random.choice(self.products)
            
            # Generate realistic sales data
            base_quantity = np.random.poisson(10)  # Poisson distribution for sales
            quantity_sold = max(1, base_quantity)
            
            # Price with some variation
            price_variation = np.random.uniform(0.9, 1.1)
            unit_price = product.selling_price * price_variation
            revenue = quantity_sold * unit_price
            
            # Random time within the day
            sale_time = datetime.combine(date, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Promotion code (20% chance)
            promotion_code = random.choice(['SAVE10', 'WINTER20', 'BULK15', '']) if random.random() < 0.2 else ''
            
            sales_record = {
                'date': sale_time.isoformat(),
                'product_id': product.product_id,
                'channel': random.choice(self.channels),
                'quantity_sold': quantity_sold,
                'revenue': round(revenue, 2),
                'customer_segment': random.choice(self.customer_segments),
                'promotion_code': promotion_code,
                'fulfillment_method': random.choice(self.fulfillment_methods)
            }
            
            sales_data.append(sales_record)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(sales_data)
        filename = f"sales_data_{date.strftime('%Y%m%d')}.csv"
        filepath = self.output_dir / filename
        
        df.to_csv(filepath, index=False)
        print(f"Generated sales CSV: {filepath} ({len(sales_data)} records)")
        
        return str(filepath)
    
    def generate_inventory_csv(self, date: datetime = None, num_records: int = None) -> str:
        """Generate sample inventory CSV file"""
        if date is None:
            date = datetime.utcnow().date()
        
        if num_records is None:
            num_records = len(self.products) * len(self.locations)  # One record per product per location
        
        inventory_data = []
        
        for product in self.products:
            for location in self.locations:
                # Generate realistic inventory levels
                base_stock = np.random.randint(50, 500)
                reserved_stock = np.random.randint(0, base_stock // 10)
                in_transit = np.random.randint(0, base_stock // 5)
                
                # Last reorder date (within last 30 days)
                last_reorder = date - timedelta(days=random.randint(1, 30))
                
                inventory_record = {
                    'date': datetime.combine(date, datetime.min.time()).isoformat(),
                    'product_id': product.product_id,
                    'location': location,
                    'stock_level': base_stock,
                    'reserved_stock': reserved_stock,
                    'in_transit': in_transit,
                    'supplier_id': random.choice(self.suppliers),
                    'last_reorder_date': last_reorder.isoformat()
                }
                
                inventory_data.append(inventory_record)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(inventory_data)
        filename = f"inventory_data_{date.strftime('%Y%m%d')}.csv"
        filepath = self.output_dir / filename
        
        df.to_csv(filepath, index=False)
        print(f"Generated inventory CSV: {filepath} ({len(inventory_data)} records)")
        
        return str(filepath)
    
    def generate_demand_csv(self, date: datetime = None, num_records: int = None) -> str:
        """Generate sample demand signals CSV file"""
        if date is None:
            date = datetime.utcnow().date()
        
        if num_records is None:
            num_records = len(self.products)  # One record per product
        
        demand_data = []
        
        for product in self.products:
            # Generate market trend (-1 to 1)
            market_trend = np.random.uniform(-0.5, 0.5)
            
            # Generate competitor price (around product price with variation)
            competitor_price = product.selling_price * np.random.uniform(0.8, 1.2)
            
            # Generate social sentiment (-1 to 1)
            social_sentiment = np.random.uniform(-0.3, 0.7)  # Slightly positive bias
            
            demand_record = {
                'date': datetime.combine(date, datetime.min.time()).isoformat(),
                'product_id': product.product_id,
                'external_demand': random.choice(self.demand_levels),
                'market_trend': round(market_trend, 3),
                'competitor_price': round(competitor_price, 2),
                'weather_factor': random.choice(self.weather_factors),
                'event_impact': random.choice(self.event_impacts),
                'social_sentiment': round(social_sentiment, 3)
            }
            
            demand_data.append(demand_record)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(demand_data)
        filename = f"demand_data_{date.strftime('%Y%m%d')}.csv"
        filepath = self.output_dir / filename
        
        df.to_csv(filepath, index=False)
        print(f"Generated demand CSV: {filepath} ({len(demand_data)} records)")
        
        return str(filepath)
    
    def generate_daily_dataset(self, date: datetime = None) -> Dict[str, str]:
        """Generate complete daily dataset (all CSV types)"""
        if date is None:
            date = datetime.utcnow().date()
        
        print(f"Generating daily dataset for {date}")
        
        files = {
            'sales': self.generate_sales_csv(date),
            'inventory': self.generate_inventory_csv(date),
            'demand': self.generate_demand_csv(date)
        }
        
        return files
    
    def generate_historical_dataset(self, days: int = 7) -> Dict[str, List[str]]:
        """Generate historical dataset for multiple days"""
        print(f"Generating historical dataset for {days} days")
        
        all_files = {
            'sales': [],
            'inventory': [],
            'demand': []
        }
        
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=i)
            daily_files = self.generate_daily_dataset(date)
            
            for data_type, filepath in daily_files.items():
                all_files[data_type].append(filepath)
        
        return all_files
    
    def generate_corrupted_data_samples(self) -> Dict[str, str]:
        """Generate sample files with data quality issues for testing"""
        print("Generating corrupted data samples for testing")
        
        corrupted_files = {}
        
        # Corrupted sales file
        sales_data = [
            {
                'date': '2025-01-15',
                'product_id': 'PER-0001',
                'channel': 'online',
                'quantity_sold': -5,  # Negative quantity (error)
                'revenue': 125.50,
                'customer_segment': 'premium',
                'promotion_code': '',
                'fulfillment_method': 'warehouse'
            },
            {
                'date': 'invalid_date',  # Invalid date format
                'product_id': 'FOO-0002',
                'channel': 'pos',
                'quantity_sold': 'not_a_number',  # Invalid data type
                'revenue': -54.00,  # Negative revenue
                'customer_segment': 'regular',
                'promotion_code': '',
                'fulfillment_method': 'store_pickup'
            },
            {
                'date': '2025-01-15',
                'product_id': '',  # Missing product ID
                'channel': 'invalid_channel',  # Invalid channel
                'quantity_sold': 10,
                'revenue': 100.00,
                'customer_segment': 'premium',
                'promotion_code': '',
                'fulfillment_method': 'warehouse'
            }
        ]
        
        df = pd.DataFrame(sales_data)
        filepath = self.output_dir / "corrupted_sales_data.csv"
        df.to_csv(filepath, index=False)
        corrupted_files['sales'] = str(filepath)
        
        # Corrupted inventory file
        inventory_data = [
            {
                'date': '2025-01-15',
                'product_id': 'PER-0001',
                'location': 'warehouse_a',
                'stock_level': -10,  # Negative stock
                'reserved_stock': 25,  # Reserved > stock
                'in_transit': 50,
                'supplier_id': 'SUP001',
                'last_reorder_date': '2025-01-10'
            },
            {
                'date': '2025-01-15',
                'product_id': 'FOO-0002',
                'location': '',  # Missing location
                'stock_level': 'invalid',  # Invalid data type
                'reserved_stock': 5,
                'in_transit': 0,
                'supplier_id': 'SUP002',
                'last_reorder_date': 'invalid_date'
            }
        ]
        
        df = pd.DataFrame(inventory_data)
        filepath = self.output_dir / "corrupted_inventory_data.csv"
        df.to_csv(filepath, index=False)
        corrupted_files['inventory'] = str(filepath)
        
        return corrupted_files


class LiveDataTester:
    """Test the live data integration system"""
    
    def __init__(self):
        self.generator = SampleDataGenerator()
        
    def test_csv_ingestion(self) -> Dict[str, Any]:
        """Test CSV ingestion pipeline"""
        print("Testing CSV ingestion pipeline...")
        
        from .csv_ingestion import CSVIngestionPipeline
        
        # Generate test data
        test_files = self.generator.generate_daily_dataset()
        
        # Test ingestion
        pipeline = CSVIngestionPipeline()
        results = pipeline.process_daily_files()
        
        return {
            'test_name': 'csv_ingestion',
            'test_files': test_files,
            'ingestion_results': results,
            'status': 'success' if results['failed_records'] == 0 else 'partial'
        }
    
    def test_data_quality_monitoring(self) -> Dict[str, Any]:
        """Test data quality monitoring"""
        print("Testing data quality monitoring...")
        
        from .data_quality_monitor import DataQualityMonitor
        from sqlalchemy import create_engine
        
        # Generate test data including corrupted samples
        self.generator.generate_daily_dataset()
        corrupted_files = self.generator.generate_corrupted_data_samples()
        
        # Test quality monitoring
        engine = create_engine(DATABASE_URL)
        session = get_session(engine)
        
        monitor = DataQualityMonitor(session)
        quality_results = monitor.run_comprehensive_quality_check()
        
        session.close()
        
        return {
            'test_name': 'data_quality_monitoring',
            'corrupted_files': corrupted_files,
            'quality_results': quality_results,
            'status': quality_results['overall_status']
        }
    
    def test_feature_engineering(self) -> Dict[str, Any]:
        """Test feature engineering"""
        print("Testing feature engineering...")
        
        from .live_feature_engineering import LiveFeatureEngineer
        from sqlalchemy import create_engine
        
        # Generate test data
        self.generator.generate_daily_dataset()
        
        # Test feature engineering
        engine = create_engine(DATABASE_URL)
        session = get_session(engine)
        
        feature_engineer = LiveFeatureEngineer(session)
        
        # Test with first product
        products = session.query(Product).limit(1).all()
        if products:
            product_id = products[0].product_id
            features = feature_engineer.create_comprehensive_feature_set(product_id)
            
            session.close()
            
            return {
                'test_name': 'feature_engineering',
                'product_id': product_id,
                'features_count': len(features),
                'sample_features': dict(list(features.items())[:10]),  # First 10 features
                'status': 'success' if features else 'failed'
            }
        
        session.close()
        return {
            'test_name': 'feature_engineering',
            'status': 'failed',
            'error': 'No products found'
        }
    
    def test_daily_workflow(self) -> Dict[str, Any]:
        """Test complete daily workflow"""
        print("Testing complete daily workflow...")
        
        from .daily_workflow import WorkflowOrchestrator
        
        # Generate test data
        self.generator.generate_daily_dataset()
        
        # Test workflow
        orchestrator = WorkflowOrchestrator()
        workflow_result = orchestrator.run_daily_workflow()
        
        return {
            'test_name': 'daily_workflow',
            'workflow_result': workflow_result,
            'status': workflow_result['status']
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("Running comprehensive live data integration test suite...")
        
        test_results = {
            'timestamp': datetime.utcnow(),
            'tests': [],
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        }
        
        # List of tests to run
        tests = [
            self.test_csv_ingestion,
            self.test_data_quality_monitoring,
            self.test_feature_engineering,
            self.test_daily_workflow
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                test_results['tests'].append(result)
                test_results['summary']['total_tests'] += 1
                
                if result['status'] in ['success', 'pass']:
                    test_results['summary']['passed_tests'] += 1
                else:
                    test_results['summary']['failed_tests'] += 1
                    
            except Exception as e:
                error_result = {
                    'test_name': test_func.__name__,
                    'status': 'error',
                    'error': str(e)
                }
                test_results['tests'].append(error_result)
                test_results['summary']['total_tests'] += 1
                test_results['summary']['failed_tests'] += 1
        
        # Overall status
        if test_results['summary']['failed_tests'] == 0:
            test_results['overall_status'] = 'success'
        else:
            test_results['overall_status'] = 'partial'
        
        return test_results


def main():
    """Main function for testing"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'generate':
            # Generate sample data
            generator = SampleDataGenerator()
            if len(sys.argv) > 2 and sys.argv[2] == 'historical':
                days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
                files = generator.generate_historical_dataset(days)
                print(f"Generated historical dataset: {files}")
            else:
                files = generator.generate_daily_dataset()
                print(f"Generated daily dataset: {files}")
        
        elif command == 'test':
            # Run tests
            tester = LiveDataTester()
            results = tester.run_comprehensive_test()
            print(json.dumps(results, indent=2, default=str))
        
        elif command == 'corrupted':
            # Generate corrupted data for testing
            generator = SampleDataGenerator()
            files = generator.generate_corrupted_data_samples()
            print(f"Generated corrupted data samples: {files}")
    
    else:
        print("Usage:")
        print("  python sample_data_generator.py generate [historical [days]]")
        print("  python sample_data_generator.py test")
        print("  python sample_data_generator.py corrupted")


if __name__ == "__main__":
    main()