#!/usr/bin/env python3
"""
Simple script to update currency symbols from $ to £
"""
import os
import re

def update_currency_in_file(filepath):
    """Update currency symbols in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Simple currency replacements
        replacements = [
            ('f"${', 'f"£{'),
            ("f'${", "f'£{"),
            ('unit="$"', 'unit="£"'),
            ("unit='$'", "unit='£'"),
            ('Total Cost ($)', 'Total Cost (£)'),
            ('$/unit', '£/unit'),
            ('$/day', '£/day'),
            ('Cost: $', 'Cost: £'),
            ('"$125K"', '"£125K"'),
            ('"$98K"', '"£98K"'),
            ('"$87K"', '"£87K"'),
            ('"$156K"', '"£156K"'),
            ('"$76K"', '"£76K"'),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
        else:
            print(f"No changes needed: {filepath}")
            return False
            
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def main():
    """Main function"""
    print("STOCK GRIP CURRENCY UPDATE")
    print("=" * 30)
    print("Converting $ to £...")
    
    files = ['app.py', 'app_business.py', 'src/utils/metrics.py', 'test_stock_grip.py']
    
    updated = 0
    for filepath in files:
        if os.path.exists(filepath):
            if update_currency_in_file(filepath):
                updated += 1
        else:
            print(f"File not found: {filepath}")
    
    print(f"\nUpdate complete! Files updated: {updated}")
    print("Currency changed from $ to £")

if __name__ == "__main__":
    main()