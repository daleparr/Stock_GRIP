"""
Comprehensive test script for Stock_GRIP end-to-end workflow
"""
import sys
import os
import time
import traceback
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        # Core modules
        from src.data.models import Product, Inventory, Demand, create_database, get_session
        from src.data.data_generator import FMCGDataGenerator
        from src.data.pipeline import DataPipeline
        
        # Optimization modules
        from src.optimization.gp_eims import GPEIMSOptimizer
        from src.optimization.mpc_rl_mobo import MPCRLMOBOController
        from src.optimization.coordinator import StockGRIPSystem
        
        # Simulation and utilities
        from src.simulation.environment import InventorySimulationEnvironment, StrategyComparator
        from src.utils.metrics import PerformanceCalculator, PerformanceDashboard
        
        # Configuration
        from config.settings import DATABASE_URL, GP_EIMS_CONFIG, MPC_RL_CONFIG
        
        print("✅ All imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_database_setup():
    """Test database creation and basic operations"""
    print("\n🗄️ Testing database setup...")
    
    try:
        from src.data.models import create_database, get_session, Product
        from config.settings import DATABASE_URL
        
        # Create database
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Test basic query
        product_count = session.query(Product).count()
        print(f"✅ Database connected. Products in database: {product_count}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_data_generation():
    """Test synthetic data generation"""
    print("\n📊 Testing data generation...")
    
    try:
        from src.data.data_generator import FMCGDataGenerator
        from src.data.models import get_session, create_database, Product, Demand
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Check if data already exists
        existing_products = session.query(Product).count()
        
        if existing_products == 0:
            print("Generating sample data...")
            generator = FMCGDataGenerator(DATABASE_URL)
            generator.populate_database(num_products=10, simulation_days=30)  # Smaller dataset for testing
            generator.close()
        
        # Verify data
        product_count = session.query(Product).count()
        demand_count = session.query(Demand).count()
        
        print(f"✅ Data generation successful. Products: {product_count}, Demand records: {demand_count}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Data generation error: {e}")
        traceback.print_exc()
        return False


def test_data_pipeline():
    """Test data pipeline and validation"""
    print("\n🔧 Testing data pipeline...")
    
    try:
        from src.data.pipeline import DataPipeline
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        pipeline = DataPipeline(session)
        
        # Run data quality check
        validation_results = pipeline.run_data_quality_check()
        
        if validation_results["validation_passed"]:
            print("✅ Data quality validation passed")
        else:
            print(f"⚠️ Data quality issues found: {validation_results['total_issues']} issues")
        
        # Test feature preparation
        feature_matrix = pipeline.prepare_optimization_data()
        print(f"✅ Feature matrix prepared: {len(feature_matrix)} products")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Data pipeline error: {e}")
        traceback.print_exc()
        return False


def test_gp_eims_optimization():
    """Test GP-EIMS optimization"""
    print("\n🧠 Testing GP-EIMS optimization...")
    
    try:
        from src.optimization.gp_eims import GPEIMSOptimizer
        from src.data.models import get_session, create_database, Product
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        optimizer = GPEIMSOptimizer(session)
        
        # Get first product for testing
        first_product = session.query(Product).first()
        
        if first_product:
            print(f"Optimizing parameters for product: {first_product.product_id}")
            
            # Run optimization with reduced iterations for testing
            original_max_iter = optimizer.config["max_iterations"]
            optimizer.config["max_iterations"] = 5  # Reduce for testing
            
            result = optimizer.optimize_product(first_product.product_id)
            
            # Restore original config
            optimizer.config["max_iterations"] = original_max_iter
            
            if result:
                print(f"✅ GP-EIMS optimization successful")
                print(f"   Reorder Point: {result.reorder_point}")
                print(f"   Safety Stock: {result.safety_stock}")
                print(f"   Order Quantity: {result.order_quantity}")
            else:
                print("⚠️ GP-EIMS optimization returned no result")
        else:
            print("⚠️ No products found for optimization")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ GP-EIMS optimization error: {e}")
        traceback.print_exc()
        return False


def test_mpc_rl_optimization():
    """Test MPC-RL-MOBO optimization"""
    print("\n⚡ Testing MPC-RL-MOBO optimization...")
    
    try:
        from src.optimization.mpc_rl_mobo import MPCRLMOBOController
        from src.data.models import get_session, create_database, Product
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        controller = MPCRLMOBOController(session)
        
        # Get first product for testing
        first_product = session.query(Product).first()
        
        if first_product:
            print(f"Testing MPC-RL-MOBO for product: {first_product.product_id}")
            
            # Test replenishment decision
            action = controller.make_replenishment_decision(first_product.product_id)
            
            if action:
                print(f"✅ MPC-RL-MOBO decision successful")
                print(f"   Action: {action.action_type}")
                print(f"   Quantity: {action.quantity}")
                print(f"   Cost: £{action.cost:.2f}")
            else:
                print("ℹ️ No action recommended by MPC-RL-MOBO")
        else:
            print("⚠️ No products found for optimization")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ MPC-RL-MOBO optimization error: {e}")
        traceback.print_exc()
        return False


def test_coordination():
    """Test coordination between optimization approaches"""
    print("\n🎯 Testing optimization coordination...")
    
    try:
        from src.optimization.coordinator import OptimizationCoordinator
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        coordinator = OptimizationCoordinator(session)
        
        # Test coordination cycle
        print("Running coordination cycle...")
        result = coordinator.run_coordination_cycle()
        
        print(f"✅ Coordination cycle completed")
        print(f"   Strategic optimization: {result['strategic_optimization'] is not None}")
        print(f"   Tactical optimization: {result['tactical_optimization'] is not None}")
        print(f"   Validation issues: {len(result['validation_issues'])}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Coordination error: {e}")
        traceback.print_exc()
        return False


def test_simulation():
    """Test simulation environment"""
    print("\n🎮 Testing simulation environment...")
    
    try:
        from src.simulation.environment import (
            InventorySimulationEnvironment, StrategyComparator,
            simple_reorder_point_strategy, economic_order_quantity_strategy
        )
        from src.data.models import get_session, create_database, Product
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Get products for simulation
        products = session.query(Product).limit(3).all()
        
        if products:
            print(f"Testing simulation with {len(products)} products...")
            
            # Test single strategy
            env = InventorySimulationEnvironment(products, simulation_days=30)
            result = env.run_simulation(simple_reorder_point_strategy)
            
            print(f"✅ Simulation completed")
            print(f"   Total cost: ${result['total_cost']:.2f}")
            print(f"   Service level: {result['service_level']:.1%}")
            print(f"   Total orders: {result['total_orders']}")
            
            # Test strategy comparison
            print("Testing strategy comparison...")
            comparator = StrategyComparator(products[:2], simulation_days=20)  # Smaller test
            
            strategies = {
                "Simple Reorder": (simple_reorder_point_strategy, {}),
                "EOQ": (economic_order_quantity_strategy, {})
            }
            
            comparison = comparator.compare_strategies(strategies, num_runs=2)
            print(f"✅ Strategy comparison completed")
            print(f"   Best strategy: {comparison['best_strategy']['best_composite']}")
        else:
            print("⚠️ No products found for simulation")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        traceback.print_exc()
        return False


def test_metrics():
    """Test performance metrics and monitoring"""
    print("\n📈 Testing performance metrics...")
    
    try:
        from src.utils.metrics import PerformanceCalculator, PerformanceDashboard, AlertSystem
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL
        
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Test performance calculator
        calculator = PerformanceCalculator(session)
        
        service_metrics = calculator.calculate_service_level_metrics(7)
        cost_metrics = calculator.calculate_cost_metrics(7)
        
        print(f"✅ Performance metrics calculated")
        print(f"   Service metrics: {len(service_metrics)}")
        print(f"   Cost metrics: {len(cost_metrics)}")
        
        # Test dashboard
        dashboard = PerformanceDashboard(session)
        kpi_dashboard = dashboard.generate_kpi_dashboard(7)
        
        print(f"✅ KPI dashboard generated")
        print(f"   Overall score: {kpi_dashboard['overall_performance_score']:.3f}")
        print(f"   Total metrics: {kpi_dashboard['summary']['total_metrics']}")
        
        # Test alerts
        alert_system = AlertSystem(session)
        alerts = alert_system.check_alerts()
        
        print(f"✅ Alert system tested")
        print(f"   Active alerts: {len(alerts)}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        traceback.print_exc()
        return False


def test_system_integration():
    """Test full system integration"""
    print("\n🚀 Testing full system integration...")
    
    try:
        from src.optimization.coordinator import StockGRIPSystem
        
        # Initialize system
        system = StockGRIPSystem()
        
        print("Initializing Stock_GRIP system...")
        init_result = system.initialize_system(generate_sample_data=False)  # Use existing data
        
        if init_result["status"] == "initialized":
            print("✅ System initialization successful")
            
            # Get system status
            status = system.get_system_status()
            print(f"   System initialized: {status['system_initialized']}")
            print(f"   Database connected: {status['database_connected']}")
            
            # Test one coordination cycle
            print("Testing coordination cycle...")
            cycle_result = system.coordinator.run_coordination_cycle()
            
            print("✅ Full system integration test successful")
        else:
            print(f"⚠️ System initialization incomplete: {init_result}")
        
        # Clean up
        system.stop()
        return True
        
    except Exception as e:
        print(f"❌ System integration error: {e}")
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests in sequence"""
    print("Starting Stock_GRIP End-to-End Testing")
    print("=" * 50)
    
    start_time = time.time()
    
    tests = [
        ("Import Test", test_imports),
        ("Database Setup", test_database_setup),
        ("Data Generation", test_data_generation),
        ("Data Pipeline", test_data_pipeline),
        ("GP-EIMS Optimization", test_gp_eims_optimization),
        ("MPC-RL-MOBO Optimization", test_mpc_rl_optimization),
        ("Coordination", test_coordination),
        ("Simulation", test_simulation),
        ("Performance Metrics", test_metrics),
        ("System Integration", test_system_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Summary")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    elapsed_time = time.time() - start_time
    print(f"Total time: {elapsed_time:.1f} seconds")
    
    if passed == total:
        print("\nAll tests passed! Stock_GRIP is ready for use.")
        return True
    else:
        print(f"\n{total - passed} tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)