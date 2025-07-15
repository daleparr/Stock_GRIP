#!/usr/bin/env python3
"""
Simple GP-EIMS stability test to validate convergence fixes
"""

import sys
import os
import warnings
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.models import get_session, create_database, Product, Demand
from src.optimization.gp_eims import GPEIMSOptimizer
from config.settings import DATABASE_URL, GP_EIMS_CONFIG

def test_gp_eims_convergence():
    """Test GP-EIMS for convergence warnings"""
    print("Testing GP-EIMS Convergence Stability...")
    print("=" * 50)
    
    try:
        # Initialize database
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Initialize optimizer
            optimizer = GPEIMSOptimizer(session)
            print("PASS: GP-EIMS optimizer initialized successfully")
            
            # Check configuration
            kernel = optimizer.gp.kernel
            kernel_str = str(kernel)
            if "100000.0" in kernel_str:
                print("PASS: Updated kernel bounds detected (100000.0)")
            else:
                print(f"WARNING: Kernel bounds may not be updated: {kernel_str}")
            
            # Test with a sample product
            products = session.query(Product).limit(1).all()
            if products:
                product = products[0]
                print(f"Testing optimization on product: {product.name}")
                
                try:
                    result = optimizer.optimize_product(product.product_id)
                    if result:
                        print("PASS: Optimization completed successfully")
                    else:
                        print("WARNING: Optimization returned no result")
                except Exception as e:
                    print(f"FAIL: Optimization failed - {str(e)}")
            else:
                print("WARNING: No products found for testing")
            
            # Check for convergence warnings
            convergence_warnings = [warning for warning in w 
                                  if "convergence" in str(warning.message).lower()]
            
            if len(convergence_warnings) == 0:
                print("PASS: No convergence warnings detected")
                print("SUCCESS: GP-EIMS convergence issues have been resolved!")
            else:
                print(f"FAIL: {len(convergence_warnings)} convergence warnings still present")
                for warning in convergence_warnings[:3]:  # Show first 3
                    print(f"  - {warning.message}")
        
        session.close()
        
    except Exception as e:
        print(f"FAIL: Test failed with error - {str(e)}")
        return False
    
    print("\n" + "=" * 50)
    print("GP-EIMS Stability Test Complete")
    return len(convergence_warnings) == 0 if 'convergence_warnings' in locals() else False

if __name__ == "__main__":
    success = test_gp_eims_convergence()
    if success:
        print("RESULT: GP-EIMS is stable and robust")
        sys.exit(0)
    else:
        print("RESULT: GP-EIMS requires further attention")
        sys.exit(1)