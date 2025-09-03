"""
Test script for live data integration
Tests the complete pipeline from CSV upload to optimization results
"""
import os
import sys
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.append('src')

def test_live_data_processor():
    """Test the LiveDataProcessor with the uploaded CSV"""
    print("🧪 Testing Live Data Processor...")
    
    try:
        from src.data.live_data_processor import LiveDataProcessor
        
        # Test with the uploaded file
        file_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
        
        if not os.path.exists(file_path):
            print(f"❌ Test file not found: {file_path}")
            return False
        
        # Initialize processor
        processor = LiveDataProcessor(file_path)
        
        # Load data
        if not processor.load_data():
            print("❌ Failed to load data")
            return False
        
        print(f"✅ Loaded {len(processor.data)} records")
        
        # Validate data
        issues = processor.validate_data()
        if issues:
            print(f"⚠️ Validation issues: {issues}")
        else:
            print("✅ Data validation passed")
        
        # Process for Stock GRIP
        processed_data = processor.process_for_stock_grip()
        print(f"✅ Processed {len(processed_data)} products for Stock GRIP")
        
        # Get summary
        summary = processor.get_optimization_summary()
        print(f"📊 Summary: £{summary['total_revenue']:,.2f} revenue, {summary['high_performers']} high performers")
        
        return True
        
    except Exception as e:
        print(f"❌ LiveDataProcessor test failed: {str(e)}")
        return False

def test_live_data_optimizer():
    """Test the LiveDataOptimizer"""
    print("\n🧪 Testing Live Data Optimizer...")
    
    try:
        from src.data.live_data_processor import LiveDataProcessor
        from src.optimization.live_data_optimizer import LiveDataOptimizer
        
        # Load processor
        file_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
        processor = LiveDataProcessor(file_path)
        
        if not processor.load_data():
            print("❌ Failed to load data for optimizer test")
            return False
        
        processor.process_for_stock_grip()
        
        # Initialize optimizer
        optimizer = LiveDataOptimizer(processor)
        
        # Initialize optimization data
        if not optimizer.initialize_optimization_data():
            print("❌ Failed to initialize optimization data")
            return False
        
        print("✅ Optimization data initialized")
        
        # Run GP-EIMS optimization
        gp_results = optimizer.run_gp_eims_optimization()
        print(f"✅ GP-EIMS completed: {len(gp_results)} product recommendations")
        
        # Run MPC-RL-MOBO optimization
        mpc_results = optimizer.run_mpc_rl_mobo_optimization()
        print(f"✅ MPC-RL-MOBO completed: {len(mpc_results)} tactical actions")
        
        # Generate unified recommendations
        unified = optimizer.generate_unified_recommendations()
        print(f"✅ Unified recommendations: {len(unified)} products")
        
        # Get portfolio insights
        insights = optimizer.get_portfolio_insights()
        print(f"📊 Portfolio health: {insights['portfolio_health']['performance_rate']:.1%}")
        
        # Get top recommendations
        top_recs = optimizer.get_top_recommendations(3)
        print("🎯 Top 3 recommendations:")
        for i, (product_id, rec) in enumerate(top_recs.items(), 1):
            print(f"   {i}. {rec['product_name']}: {rec['strategic_recommendation']}")
        
        return True
        
    except Exception as e:
        print(f"❌ LiveDataOptimizer test failed: {str(e)}")
        return False

def test_data_pipeline_integration():
    """Test the updated DataPipeline with live data"""
    print("\n🧪 Testing Data Pipeline Integration...")
    
    try:
        from src.data.pipeline import DataPipeline
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL
        
        # Initialize database session
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Test live data pipeline
        pipeline = DataPipeline(session, data_source='live')
        
        file_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
        data = pipeline.load_live_data(file_path)
        
        if data is not None:
            print(f"✅ Pipeline loaded {len(data)} products")
            
            # Test validation
            validation_result = pipeline.validate_live_data_quality(data)
            if validation_result['validation_issues']:
                print(f"⚠️ Validation issues: {validation_result['validation_issues']}")
            else:
                print("✅ Pipeline validation passed")
            
            # Test summary
            summary = pipeline.get_optimization_summary()
            if summary:
                print(f"📊 Pipeline summary: {summary['total_products']} products")
            
            session.close()
            return True
        else:
            print("❌ Pipeline failed to load data")
            session.close()
            return False
        
    except Exception as e:
        print(f"❌ DataPipeline test failed: {str(e)}")
        return False

def test_app_integration():
    """Test that the app can import all live data modules"""
    print("\n🧪 Testing App Integration...")
    
    try:
        # Test imports that the app uses
        from src.data.live_data_processor import LiveDataProcessor
        from src.optimization.live_data_optimizer import LiveDataOptimizer
        from src.data.pipeline import DataPipeline
        
        print("✅ All live data modules imported successfully")
        
        # Test configuration
        from config.settings import LIVE_DATA_CONFIG
        print(f"✅ Live data config loaded: {len(LIVE_DATA_CONFIG)} settings")
        
        return True
        
    except Exception as e:
        print(f"❌ App integration test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all live data integration tests"""
    print("🚀 Starting Live Data Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Live Data Processor", test_live_data_processor),
        ("Live Data Optimizer", test_live_data_optimizer),
        ("Data Pipeline Integration", test_data_pipeline_integration),
        ("App Integration", test_app_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Live data integration is ready.")
    else:
        print("⚠️ Some tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)