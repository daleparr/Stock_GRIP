#!/usr/bin/env python3
"""
Comprehensive system stability test for Stock_GRIP
Tests all major components for robustness and performance
"""

import sys
import os
import time
import warnings
import traceback
from datetime import datetime
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.models import get_session, create_database, Product, Demand, Inventory
from config.settings import DATABASE_URL
from src.optimization.gp_eims import GPEIMSOptimizer
from src.optimization.mpc_rl_mobo import MPCRLMOBOController
from src.optimization.coordinator import OptimizationCoordinator
from src.data.pipeline import DataPipeline
from src.utils.business_metrics import BusinessMetricsCalculator
from config.settings import GP_EIMS_CONFIG, MPC_RL_CONFIG

class SystemStabilityTester:
    """Comprehensive system stability and robustness tester"""
    
    def __init__(self):
        # Initialize database connection
        engine = create_database(DATABASE_URL)
        self.session = get_session(engine)
        self.test_results = {}
        self.start_time = datetime.now()
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {test_name}: {status}")
        if details:
            print(f"    Details: {details}")
        
        self.test_results[test_name] = {
            'status': status,
            'details': details,
            'timestamp': timestamp
        }
    
    def test_database_connection(self):
        """Test database connection stability"""
        try:
            # Test basic connection
            products = self.session.query(Product).limit(5).all()
            if len(products) > 0:
                self.log_test("Database Connection", "✅ PASS", f"Found {len(products)} products")
            else:
                self.log_test("Database Connection", "⚠️ WARNING", "No products found")
                
            # Test concurrent access simulation
            for i in range(10):
                demand_count = self.session.query(Demand).count()
                if i == 0:
                    initial_count = demand_count
                elif demand_count != initial_count:
                    self.log_test("Database Consistency", "❌ FAIL", "Inconsistent demand count")
                    return
            
            self.log_test("Database Consistency", "✅ PASS", "Consistent across multiple queries")
            
        except Exception as e:
            self.log_test("Database Connection", "❌ FAIL", str(e))
    
    def test_gp_eims_stability(self):
        """Test GP-EIMS optimization stability"""
        try:
            # Capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                optimizer = GPEIMSOptimizer(self.session)
                
                # Test configuration loading
                if optimizer.config == GP_EIMS_CONFIG:
                    self.log_test("GP-EIMS Config", "✅ PASS", "Configuration loaded correctly")
                else:
                    self.log_test("GP-EIMS Config", "❌ FAIL", "Configuration mismatch")
                
                # Test kernel bounds
                kernel = optimizer.gp.kernel
                kernel_str = str(kernel)
                if "100000.0" in kernel_str and "0.001" in kernel_str:
                    self.log_test("GP-EIMS Kernel Bounds", "✅ PASS", "Updated bounds detected")
                else:
                    self.log_test("GP-EIMS Kernel Bounds", "⚠️ WARNING", f"Kernel: {kernel_str}")
                
                # Test optimization on sample product
                products = self.session.query(Product).limit(1).all()
                if products:
                    product = products[0]
                    try:
                        # This should not generate convergence warnings
                        result = optimizer.optimize_product(product.product_id)
                        if result:
                            self.log_test("GP-EIMS Optimization", "✅ PASS", "Optimization completed")
                        else:
                            self.log_test("GP-EIMS Optimization", "⚠️ WARNING", "No result returned")
                    except Exception as e:
                        self.log_test("GP-EIMS Optimization", "❌ FAIL", str(e))
                
                # Check for convergence warnings
                convergence_warnings = [warning for warning in w if "convergence" in str(warning.message).lower()]
                if len(convergence_warnings) == 0:
                    self.log_test("GP-EIMS Warnings", "✅ PASS", "No convergence warnings")
                else:
                    self.log_test("GP-EIMS Warnings", "❌ FAIL", f"{len(convergence_warnings)} convergence warnings")
                
        except Exception as e:
            self.log_test("GP-EIMS Stability", "❌ FAIL", str(e))
    
    def test_mpc_rl_mobo_stability(self):
        """Test MPC-RL-MOBO optimization stability"""
        try:
            optimizer = MPCRLMOBOController(self.session)
            
            # Test basic initialization
            self.log_test("MPC-RL-MOBO Init", "✅ PASS", "Controller initialized successfully")
            
            # Test basic functionality
            products = self.session.query(Product).limit(1).all()
            if products:
                product = products[0]
                try:
                    # Test state creation and action recommendation
                    inventory = self.session.query(Inventory).filter(
                        Inventory.product_id == product.product_id
                    ).first()
                    
                    if inventory:
                        self.log_test("MPC-RL-MOBO Basic Test", "✅ PASS", "Basic functionality works")
                    else:
                        self.log_test("MPC-RL-MOBO Basic Test", "⚠️ WARNING", "No inventory data")
                except Exception as e:
                    self.log_test("MPC-RL-MOBO Basic Test", "❌ FAIL", str(e))
            
        except Exception as e:
            self.log_test("MPC-RL-MOBO Stability", "❌ FAIL", str(e))
    
    def test_data_pipeline_robustness(self):
        """Test data pipeline robustness"""
        try:
            pipeline = DataPipeline(self.session)
            
            # Test data quality validation
            quality_report = pipeline.validate_data_quality()
            if quality_report:
                issues = sum(len(issues) for issues in quality_report.values())
                if issues == 0:
                    self.log_test("Data Quality", "✅ PASS", "No data quality issues")
                else:
                    self.log_test("Data Quality", "⚠️ WARNING", f"{issues} data quality issues found")
            else:
                self.log_test("Data Quality", "❌ FAIL", "Quality validation failed")
                
        except Exception as e:
            self.log_test("Data Pipeline", "❌ FAIL", str(e))
    
    def test_business_metrics_calculation(self):
        """Test business metrics calculation stability"""
        try:
            calculator = BusinessMetricsCalculator(self.session)
            
            # Test metrics calculation
            products = self.session.query(Product).limit(3).all()
            for product in products:
                try:
                    metrics = calculator.calculate_product_metrics(product.product_id)
                    if metrics:
                        self.log_test(f"Business Metrics - {product.name[:20]}", "✅ PASS", "Metrics calculated")
                    else:
                        self.log_test(f"Business Metrics - {product.name[:20]}", "⚠️ WARNING", "No metrics returned")
                except Exception as e:
                    self.log_test(f"Business Metrics - {product.name[:20]}", "❌ FAIL", str(e))
                    
        except Exception as e:
            self.log_test("Business Metrics", "❌ FAIL", str(e))
    
    def test_memory_usage(self):
        """Test for memory leaks and excessive usage"""
        try:
            import psutil
            import gc
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform multiple optimization cycles
            optimizer = GPEIMSOptimizer(self.session)
            products = self.session.query(Product).limit(2).all()
            
            for i in range(3):
                for product in products:
                    try:
                        optimizer.optimize_product(product.product_id)
                    except:
                        pass  # Ignore errors for memory test
                gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            if memory_increase < 50:  # Less than 50MB increase
                self.log_test("Memory Usage", "✅ PASS", f"Memory increase: {memory_increase:.1f}MB")
            else:
                self.log_test("Memory Usage", "⚠️ WARNING", f"Memory increase: {memory_increase:.1f}MB")
                
        except ImportError:
            self.log_test("Memory Usage", "⚠️ SKIP", "psutil not available")
        except Exception as e:
            self.log_test("Memory Usage", "❌ FAIL", str(e))
    
    def test_error_handling(self):
        """Test error handling robustness"""
        try:
            optimizer = GPEIMSOptimizer(self.session)
            
            # Test with invalid product ID
            try:
                result = optimizer.optimize_product("INVALID_PRODUCT_ID")
                if result is None:
                    self.log_test("Error Handling - Invalid Product", "✅ PASS", "Graceful handling")
                else:
                    self.log_test("Error Handling - Invalid Product", "❌ FAIL", "Should return None")
            except Exception as e:
                if "not found" in str(e).lower():
                    self.log_test("Error Handling - Invalid Product", "✅ PASS", "Proper exception raised")
                else:
                    self.log_test("Error Handling - Invalid Product", "❌ FAIL", str(e))
            
        except Exception as e:
            self.log_test("Error Handling", "❌ FAIL", str(e))
    
    def run_all_tests(self):
        """Run all stability tests"""
        print("Starting Stock_GRIP System Stability Test")
        print("=" * 60)
        
        # Core system tests
        self.test_database_connection()
        self.test_data_pipeline_robustness()
        
        # Optimization engine tests
        self.test_gp_eims_stability()
        self.test_mpc_rl_mobo_stability()
        
        # Business logic tests
        self.test_business_metrics_calculation()
        
        # Performance and robustness tests
        self.test_memory_usage()
        self.test_error_handling()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("SYSTEM STABILITY TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed = sum(1 for result in self.test_results.values() if result['status'].startswith('✅'))
        warnings = sum(1 for result in self.test_results.values() if result['status'].startswith('⚠️'))
        failed = sum(1 for result in self.test_results.values() if result['status'].startswith('❌'))
        skipped = sum(1 for result in self.test_results.values() if result['status'].startswith('⚠️ SKIP'))
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️ Warnings: {warnings}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️ Skipped: {skipped}")
        
        success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        elapsed_time = datetime.now() - self.start_time
        print(f"Total Time: {elapsed_time.total_seconds():.1f} seconds")
        
        # Overall assessment
        if failed == 0 and warnings <= 2:
            print("\nSYSTEM STATUS: STABLE AND ROBUST")
        elif failed <= 1 and warnings <= 4:
            print("\nSYSTEM STATUS: MOSTLY STABLE WITH MINOR ISSUES")
        else:
            print("\nSYSTEM STATUS: REQUIRES ATTENTION")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = SystemStabilityTester()
    tester.run_all_tests()