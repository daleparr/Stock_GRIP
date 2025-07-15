#!/usr/bin/env python3
"""
Script to update all currency symbols from $ to £ in Stock GRIP
"""
import os
import re

def update_currency_in_file(filepath):
    """Update currency symbols in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace currency patterns
        patterns = [
            (r'f"\${([^}]+):([^}]*)\}"', r'f"£{\1:\2}"'),  # f"${variable:format}" -> f"£{variable:format}"
            (r"f'\${([^}]+):([^}]*)\}'", r"f'£{\1:\2}'"),  # f'${variable:format}' -> f'£{variable:format}'
            (r'f"\${([^}]+)\}"', r'f"£{\1}"'),            # f"${variable}" -> f"£{variable}"
            (r"f'\${([^}]+)\}'", r"f'£{\1}'"),            # f'${variable}' -> f'£{variable}'
            (r'"\$([0-9,]+)K?"', r'"£\1K"'),              # "$125K" -> "£125K"
            (r"'\$([0-9,]+)K?'", r"'£\1K'"),              # '$125K' -> '£125K'
            (r'unit="\$"', r'unit="£"'),                  # unit="$" -> unit="£"
            (r"unit='\$'", r"unit='£'"),                  # unit='$' -> unit='£'
            (r'Total Cost \(\$\)', r'Total Cost (£)'),   # Chart labels
            (r'\$/unit', r'£/unit'),                      # Units
            (r'\$/day', r'£/day'),                        # Units
            (r'Cost: \$', r'Cost: £'),                    # Cost: $ -> Cost: £
            (r'cost: \$', r'cost: £'),                    # cost: $ -> cost: £
            (r'Cost \(\$\)', r'Cost (£)'),                # Cost ($) -> Cost (£)
            (r'Revenue": "\$', r'Revenue": "£'),          # JSON values
            (r'Cost": "\$', r'Cost": "£'),                # JSON values
            (r'impact": "\$', r'impact": "£'),            # JSON values
            (r'value": "\$', r'value": "£'),              # JSON values
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
        else:
            print(f"ℹ️  No changes needed: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")
        return False

def update_store_names_in_business_app():
    """Update store names to UK locations in app_business.py"""
    filepath = 'app_business.py'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Store name replacements
        store_replacements = [
            ('Downtown', 'Oxford Street'),
            ('Mall Location', 'Covent Garden'),
            ('Suburban', 'Canary Wharf'),
            ('Airport', 'Westfield'),
            ('University', "King's Road"),
        ]
        
        for old_name, new_name in store_replacements:
            content = content.replace(f'"{old_name}"', f'"{new_name}"')
            content = content.replace(f"'{old_name}'", f"'{new_name}'")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated store names in: {filepath}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating store names in {filepath}: {e}")
        return False

def main():
    """Main function to update all files"""
    print("STOCK GRIP CURRENCY & LOCATION UPDATE")
    print("=" * 50)
    print("Converting $ to £ and updating locations...")
    
    # Files to update for currency
    currency_files = [
        'app.py',
        'app_business.py', 
        'src/utils/metrics.py',
        'test_stock_grip.py'
    ]
    
    updated_count = 0
    
    # Update currency symbols
    print("\n💰 Updating Currency Symbols:")
    for filepath in currency_files:
        if os.path.exists(filepath):
            if update_currency_in_file(filepath):
                updated_count += 1
        else:
            print(f"⚠️  File not found: {filepath}")
    
    # Update store names
    print("\n🏪 Updating Store Names:")
    if update_store_names_in_business_app():
        updated_count += 1
    
    print(f"\n✅ Update Complete!")
    print(f"📊 Files updated: {updated_count}")
    print(f"💷 Currency changed from $ to £")
    print(f"🇬🇧 Locations updated to UK stores")
    
    print(f"\n📋 Next Steps:")
    print(f"1. Test the changes: streamlit run app_business.py --server.port 8502")
    print(f"2. Generate new sample data: python src/data/sample_data_generator.py generate")
    print(f"3. Check the main dashboard: streamlit run app.py")
    
    print(f"\n📖 For manual customization, see: docs/LOCALIZATION_GUIDE.md")

if __name__ == "__main__":
    main()