#!/usr/bin/env python3
"""
Fix data quality issues in the Stock_GRIP database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.models import create_database, get_session, Inventory
from config.settings import DATABASE_URL

def fix_available_stock_calculations():
    """Fix available stock calculations in the database"""
    print("Connecting to database...")
    engine = create_database(DATABASE_URL)
    session = get_session(engine)
    
    try:
        # Get all inventory records
        inventory_records = session.query(Inventory).all()
        print(f"Found {len(inventory_records)} inventory records")
        
        fixed_count = 0
        for inv in inventory_records:
            # Calculate correct available stock
            correct_available = inv.stock_level - inv.reserved_stock
            
            # Check if it needs fixing
            if abs(inv.available_stock - correct_available) > 0.1:
                print(f"Fixing {inv.product_id}: {inv.available_stock} -> {correct_available}")
                inv.available_stock = correct_available
                fixed_count += 1
        
        # Commit changes
        session.commit()
        print(f"Fixed {fixed_count} inventory records")
        
    except Exception as e:
        print(f"Error fixing data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_available_stock_calculations()
    print("Data quality fix completed!")