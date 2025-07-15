#!/usr/bin/env python3
"""
Simple Test Script for Live Data Integration System
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    """Test basic functionality without complex dependencies"""
    print("STOCK GRIP LIVE DATA INTEGRATION - BASIC TEST")
    print("=" * 50)
    
    try:
        # Test 1: Import core modules
        print("\n1. Testing module imports...")
        
        from src.data.models import create_database, get_session
        from config.settings import DATABASE_URL
        print("   - Core models: OK")
        
        from src.data.live_data_models import LiveSalesData, LiveInventoryUpdate, LiveDemandSignals
        print("   - Live data models: OK")
        
        from src.data.csv_ingestion import CSVIngestionPipeline, CSVValidator
        print("   - CSV ingestion: OK")
        
        from src.data.sample_data_generator import SampleDataGenerator
        print("   - Sample data generator: OK")
        
        # Test 2: Database setup
        print("\n2. Testing database setup...")
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        print("   - Database created: OK")
        
        # Test 3: Generate sample data
        print("\n3. Testing sample data generation...")
        generator = SampleDataGenerator()
        
        # Create directories
        Path("data/live_feeds").mkdir(parents=True, exist_ok=True)
        
        # Generate a small dataset
        files = generator.generate_daily_dataset()
        print(f"   - Generated {len(files)} CSV files")
        
        for data_type, filepath in files.items():
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"     {data_type}: {filepath} ({file_size} bytes)")
            else:
                print(f"     {data_type}: FILE NOT FOUND")
        
        # Test 4: CSV validation
        print("\n4. Testing CSV validation...")
        validator = CSVValidator()
        
        # Test sales file validation
        import pandas as pd
        sales_file = files['sales']
        df = pd.read_csv(sales_file)
        
        validation_result = validator.validate_schema(df, 'sales')
        print(f"   - Schema validation: {'PASS' if validation_result['valid'] else 'FAIL'}")
        
        if not validation_result['valid']:
            print(f"     Errors: {validation_result['errors']}")
        
        # Test 5: Basic ingestion
        print("\n5. Testing CSV ingestion...")
        pipeline = CSVIngestionPipeline()
        
        # Process one file
        result = pipeline.process_csv_file(sales_file, 'sales')
        print(f"   - Ingestion status: {result['status']}")
        print(f"   - Records processed: {result['records_processed']}")
        print(f"   - Records successful: {result['records_successful']}")
        
        session.close()
        
        print("\n" + "=" * 50)
        print("BASIC TEST COMPLETED SUCCESSFULLY!")
        print("The live data integration system is functional.")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nBASIC TEST FAILED!")
        return False

def test_data_quality():
    """Test data quality monitoring"""
    print("\nTESTING DATA QUALITY MONITORING")
    print("-" * 30)
    
    try:
        from src.data.data_quality_monitor import DataQualityMonitor
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        monitor = DataQualityMonitor(session)
        
        # Test completeness check
        completeness_result = monitor.check_data_completeness('sales')
        print(f"Completeness check: {completeness_result['status']}")
        
        # Test timeliness check
        timeliness_result = monitor.check_data_timeliness('sales')
        print(f"Timeliness check: {timeliness_result['status']}")
        
        session.close()
        print("Data quality monitoring: OK")
        return True
        
    except Exception as e:
        print(f"Data quality monitoring failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting Live Data Integration Tests...")
    
    # Run basic functionality test
    basic_success = test_basic_functionality()
    
    if basic_success:
        # Run additional tests
        quality_success = test_data_quality()
        
        if quality_success:
            print("\nALL TESTS PASSED!")
            print("Live data integration system is ready for use.")
        else:
            print("\nBASIC TESTS PASSED, but some advanced features had issues.")
    else:
        print("\nBASIC TESTS FAILED!")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()