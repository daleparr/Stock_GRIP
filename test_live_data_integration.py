#!/usr/bin/env python3
"""
Test Script for Live Data Integration System
Demonstrates the complete workflow from CSV ingestion to optimization
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine
from src.data.models import create_database, get_session
from src.data.sample_data_generator import SampleDataGenerator, LiveDataTester
from src.data.csv_ingestion import CSVIngestionPipeline
from src.data.data_quality_monitor import DataQualityMonitor
from src.data.live_feature_engineering import LiveFeatureEngineer
from src.data.daily_workflow import WorkflowOrchestrator
from config.settings import DATABASE_URL


class LiveDataIntegrationDemo:
    """Comprehensive demonstration of live data integration capabilities"""
    
    def __init__(self):
        self.database_url = DATABASE_URL
        self.setup_environment()
        
    def setup_environment(self):
        """Setup test environment"""
        print("Setting up test environment...")
        
        # Create necessary directories
        directories = [
            "data/live_feeds",
            "data/processed", 
            "data/errors",
            "reports",
            "logs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.engine = create_database(self.database_url)
        print("✅ Environment setup complete")
    
    def demo_csv_schema_and_generation(self):
        """Demonstrate CSV schema and sample data generation"""
        print("\n📊 DEMO 1: CSV Schema and Data Generation")
        print("=" * 50)
        
        generator = SampleDataGenerator()
        
        # Generate sample data for the last 3 days
        print("Generating sample data for the last 3 days...")
        
        for i in range(3):
            date = datetime.utcnow().date() - timedelta(days=i)
            files = generator.generate_daily_dataset(date)
            
            print(f"\nGenerated data for {date}:")
            for data_type, filepath in files.items():
                file_size = os.path.getsize(filepath) / 1024  # KB
                with open(filepath, 'r') as f:
                    line_count = sum(1 for line in f) - 1  # Exclude header
                
                print(f"  📄 {data_type}: {filepath}")
                print(f"     Size: {file_size:.1f} KB, Records: {line_count}")
        
        # Show sample CSV content
        print("\n📋 Sample CSV Content:")
        sample_file = files['sales']
        with open(sample_file, 'r') as f:
            lines = f.readlines()[:6]  # Header + 5 data rows
            for line in lines:
                print(f"     {line.strip()}")
        
        return True
    
    def demo_csv_ingestion_pipeline(self):
        """Demonstrate CSV ingestion with validation"""
        print("\n🔄 DEMO 2: CSV Ingestion Pipeline")
        print("=" * 50)
        
        pipeline = CSVIngestionPipeline()
        
        print("Processing CSV files...")
        start_time = time.time()
        
        # Process all CSV files in the directory
        results = pipeline.process_daily_files()
        
        processing_time = time.time() - start_time
        
        print(f"\n📈 Ingestion Results:")
        print(f"  ⏱️  Processing Time: {processing_time:.2f} seconds")
        print(f"  📁 Files Processed: {len(results['processed_files'])}")
        print(f"  📊 Total Records: {results['total_records']}")
        print(f"  ✅ Successful: {results['successful_records']}")
        print(f"  ❌ Failed: {results['failed_records']}")
        
        if results['successful_records'] > 0:
            success_rate = (results['successful_records'] / results['total_records']) * 100
            print(f"  📊 Success Rate: {success_rate:.1f}%")
        
        # Show details for each file
        print(f"\n📋 File Processing Details:")
        for file_result in results['processed_files']:
            status_emoji = "✅" if file_result['status'] == 'success' else "⚠️" if file_result['status'] == 'partial' else "❌"
            print(f"  {status_emoji} {file_result['file_name']}: {file_result['status']}")
            print(f"     Records: {file_result['records_successful']}/{file_result['records_processed']}")
            
            if file_result.get('errors'):
                print(f"     Errors: {len(file_result['errors'])}")
        
        return results['successful_records'] > 0
    
    def demo_data_quality_monitoring(self):
        """Demonstrate data quality monitoring and anomaly detection"""
        print("\n🔍 DEMO 3: Data Quality Monitoring")
        print("=" * 50)
        
        session = get_session(self.engine)
        monitor = DataQualityMonitor(session)
        
        print("Running comprehensive data quality checks...")
        
        # Run quality checks
        quality_results = monitor.run_comprehensive_quality_check()
        
        print(f"\n📊 Quality Check Results:")
        print(f"  🎯 Overall Status: {quality_results['overall_status'].upper()}")
        print(f"  ✅ Passed Checks: {quality_results['summary']['passed_checks']}")
        print(f"  ⚠️  Warning Checks: {quality_results['summary']['warning_checks']}")
        print(f"  ❌ Failed Checks: {quality_results['summary']['failed_checks']}")
        
        # Show detailed results
        print(f"\n📋 Detailed Check Results:")
        for check in quality_results['checks']:
            status_emoji = "✅" if check['status'] == 'pass' else "⚠️" if check['status'] == 'warning' else "❌"
            print(f"  {status_emoji} {check['data_source']} - {check['metric_name']}: {check['status']}")
            print(f"     Value: {check['metric_value']:.3f} (Threshold: {check['threshold_value']:.3f})")
            
            if check.get('details') and check['details'].get('anomalies'):
                anomaly_count = len(check['details']['anomalies'])
                if anomaly_count > 0:
                    print(f"     🚨 Anomalies Detected: {anomaly_count}")
        
        session.close()
        return quality_results['overall_status'] in ['pass', 'warning']
    
    def demo_feature_engineering(self):
        """Demonstrate live feature engineering"""
        print("\n🧠 DEMO 4: Live Feature Engineering")
        print("=" * 50)
        
        session = get_session(self.engine)
        feature_engineer = LiveFeatureEngineer(session)
        
        # Get a sample product
        from src.data.models import Product
        products = session.query(Product).limit(3).all()
        
        if not products:
            print("❌ No products found in database")
            session.close()
            return False
        
        print(f"Generating features for {len(products)} products...")
        
        all_features = {}
        for product in products:
            print(f"\n🔧 Processing product: {product.product_id}")
            
            try:
                features = feature_engineer.create_comprehensive_feature_set(product.product_id)
                all_features[product.product_id] = features
                
                print(f"  📊 Generated {len(features)} features")
                
                # Show sample features
                feature_categories = {}
                for feature_name, value in features.items():
                    category = feature_name.split('_')[0]
                    if category not in feature_categories:
                        feature_categories[category] = []
                    feature_categories[category].append((feature_name, value))
                
                print(f"  📋 Feature Categories:")
                for category, category_features in feature_categories.items():
                    print(f"     {category}: {len(category_features)} features")
                    # Show first 2 features in each category
                    for feature_name, value in category_features[:2]:
                        print(f"       {feature_name}: {value:.3f}")
                
            except Exception as e:
                print(f"  ❌ Error generating features: {e}")
        
        session.close()
        
        print(f"\n📈 Feature Engineering Summary:")
        print(f"  🎯 Products Processed: {len(all_features)}")
        total_features = sum(len(features) for features in all_features.values())
        print(f"  📊 Total Features Generated: {total_features}")
        
        return len(all_features) > 0
    
    def demo_daily_workflow(self):
        """Demonstrate automated daily workflow"""
        print("\n🔄 DEMO 5: Automated Daily Workflow")
        print("=" * 50)
        
        orchestrator = WorkflowOrchestrator()
        
        print("Running complete daily workflow...")
        start_time = time.time()
        
        # Run workflow
        workflow_result = orchestrator.run_daily_workflow()
        
        processing_time = time.time() - start_time
        
        print(f"\n📊 Workflow Results:")
        print(f"  🎯 Status: {workflow_result['status'].upper()}")
        print(f"  ⏱️  Duration: {workflow_result['duration_minutes']:.2f} minutes")
        print(f"  📁 Files Processed: {workflow_result['summary']['total_files_processed']}")
        print(f"  📊 Records Processed: {workflow_result['summary']['total_records_processed']}")
        print(f"  ✅ Successful Records: {workflow_result['summary']['successful_records']}")
        print(f"  🔍 Quality Checks Passed: {workflow_result['summary']['quality_checks_passed']}")
        
        print(f"\n📋 Workflow Steps:")
        for step in workflow_result['steps']:
            status_emoji = "✅" if step['status'] == 'success' else "⚠️" if step['status'] == 'warning' else "❌"
            print(f"  {status_emoji} {step['step_name']}: {step['status']} ({step['duration_seconds']:.1f}s)")
        
        if workflow_result.get('errors'):
            print(f"\n❌ Workflow Errors:")
            for error in workflow_result['errors']:
                print(f"  • {error}")
        
        return workflow_result['status'] in ['success', 'warning']
    
    def demo_error_handling(self):
        """Demonstrate error handling with corrupted data"""
        print("\n🚨 DEMO 6: Error Handling and Data Validation")
        print("=" * 50)
        
        generator = SampleDataGenerator()
        
        print("Generating corrupted data samples...")
        corrupted_files = generator.generate_corrupted_data_samples()
        
        print(f"Generated {len(corrupted_files)} corrupted files:")
        for data_type, filepath in corrupted_files.items():
            print(f"  📄 {data_type}: {filepath}")
        
        # Try to process corrupted files
        pipeline = CSVIngestionPipeline()
        
        print(f"\nProcessing corrupted files...")
        for data_type, filepath in corrupted_files.items():
            print(f"\n🔧 Processing {data_type} file...")
            result = pipeline.process_csv_file(filepath, data_type)
            
            status_emoji = "✅" if result['status'] == 'success' else "⚠️" if result['status'] == 'partial' else "❌"
            print(f"  {status_emoji} Status: {result['status']}")
            print(f"  📊 Records: {result['records_successful']}/{result['records_processed']}")
            
            if result.get('errors'):
                print(f"  ❌ Errors ({len(result['errors'])}):")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     • {error}")
                if len(result['errors']) > 3:
                    print(f"     ... and {len(result['errors']) - 3} more errors")
        
        return True
    
    def demo_integration_with_optimization(self):
        """Demonstrate integration with existing optimization system"""
        print("\n🎯 DEMO 7: Integration with Optimization System")
        print("=" * 50)
        
        try:
            from src.optimization.coordinator import OptimizationCoordinator
            from src.data.pipeline import DataPipeline
            
            session = get_session(self.engine)
            
            print("Testing integration with existing optimization system...")
            
            # Test data pipeline integration
            pipeline = DataPipeline(session)
            
            print("\n🔧 Running data quality check...")
            validation_results = pipeline.run_data_quality_check()
            
            print(f"  📊 Validation Status: {'PASSED' if validation_results['validation_passed'] else 'FAILED'}")
            print(f"  🔍 Total Issues: {validation_results['total_issues']}")
            
            # Test optimization data preparation
            print("\n🧠 Preparing optimization data...")
            feature_matrix = pipeline.prepare_optimization_data()
            
            print(f"  📊 Feature Matrix Shape: {feature_matrix.shape if not feature_matrix.empty else 'Empty'}")
            if not feature_matrix.empty:
                print(f"  📋 Features: {list(feature_matrix.columns)[:5]}...")  # Show first 5 features
            
            # Test performance reporting
            print("\n📈 Generating performance report...")
            performance_report = pipeline.generate_performance_report(7)  # Last 7 days
            
            print(f"  📊 Report Summary:")
            summary = performance_report['summary']
            print(f"     Total Demand: {summary['total_demand']}")
            print(f"     Total Fulfilled: {summary['total_fulfilled']}")
            print(f"     Service Level: {summary['overall_service_level']:.1%}")
            print(f"     Products Analyzed: {summary['products_analyzed']}")
            
            session.close()
            return True
            
        except ImportError as e:
            print(f"⚠️  Optimization system not available: {e}")
            return False
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            return False
    
    def run_comprehensive_demo(self):
        """Run complete demonstration"""
        print("🚀 STOCK GRIP LIVE DATA INTEGRATION DEMONSTRATION")
        print("=" * 60)
        print(f"Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        demos = [
            ("CSV Schema and Data Generation", self.demo_csv_schema_and_generation),
            ("CSV Ingestion Pipeline", self.demo_csv_ingestion_pipeline),
            ("Data Quality Monitoring", self.demo_data_quality_monitoring),
            ("Live Feature Engineering", self.demo_feature_engineering),
            ("Automated Daily Workflow", self.demo_daily_workflow),
            ("Error Handling", self.demo_error_handling),
            ("Integration with Optimization", self.demo_integration_with_optimization)
        ]
        
        results = {}
        
        for demo_name, demo_func in demos:
            try:
                print(f"\n" + "="*60)
                success = demo_func()
                results[demo_name] = "✅ PASSED" if success else "❌ FAILED"
            except Exception as e:
                print(f"\n❌ Demo failed with error: {e}")
                results[demo_name] = f"❌ ERROR: {str(e)}"
        
        # Final summary
        print(f"\n" + "="*60)
        print("📊 DEMONSTRATION SUMMARY")
        print("="*60)
        
        passed_count = sum(1 for result in results.values() if "✅" in result)
        total_count = len(results)
        
        for demo_name, result in results.items():
            print(f"{result} {demo_name}")
        
        print(f"\n🎯 Overall Result: {passed_count}/{total_count} demos passed")
        
        if passed_count == total_count:
            print("🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
            print("The live data integration system is ready for production use.")
        else:
            print("⚠️  Some demonstrations had issues. Please review the output above.")
        
        print(f"\nCompleted at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return results


def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            # Quick test - just run a few key demos
            demo = LiveDataIntegrationDemo()
            print("🚀 QUICK LIVE DATA INTEGRATION TEST")
            print("="*50)
            
            success = True
            success &= demo.demo_csv_schema_and_generation()
            success &= demo.demo_csv_ingestion_pipeline()
            success &= demo.demo_data_quality_monitoring()
            
            if success:
                print("\n✅ Quick test completed successfully!")
            else:
                print("\n❌ Quick test had issues.")
        
        elif command == "generate":
            # Just generate sample data
            generator = SampleDataGenerator()
            files = generator.generate_daily_dataset()
            print("Generated sample data files:")
            for data_type, filepath in files.items():
                print(f"  {data_type}: {filepath}")
        
        elif command == "test":
            # Run automated tests
            tester = LiveDataTester()
            results = tester.run_comprehensive_test()
            print(json.dumps(results, indent=2, default=str))
        
        else:
            print("Unknown command. Use 'quick', 'generate', 'test', or no argument for full demo.")
    
    else:
        # Full demonstration
        demo = LiveDataIntegrationDemo()
        demo.run_comprehensive_demo()


if __name__ == "__main__":
    main()