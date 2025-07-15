# Stock GRIP Localization Guide

## Overview

This guide shows you exactly where to change currency symbols from $ to £ and customize location names throughout the Stock GRIP system.

## Quick Setup

### 1. Main Configuration File

**File: `config/localization.py`** (Already created)

This is your main configuration file. Simply edit these values:

```python
# Currency Settings
CURRENCY_SYMBOL = "£"  # Change this to your currency

# Location Names - Customize these for your business
WAREHOUSE_LOCATIONS = [
    "warehouse_london",
    "warehouse_manchester", 
    "warehouse_birmingham",
    "distribution_centre_uk"
]

STORE_LOCATIONS = [
    "store_oxford_street",
    "store_covent_garden", 
    "store_canary_wharf",
    "store_westfield",
    "store_kings_road"
]
```

## Detailed File-by-File Changes

### 2. Business Metrics Module

**File: `src/utils/business_metrics.py`** (Already updated)

The business metrics module now automatically uses the localization settings. No manual changes needed.

### 3. Sample Data Generator

**File: `src/data/sample_data_generator.py`** (Already updated)

The sample data generator now uses your custom locations. No manual changes needed.

### 4. Business Dashboard

**File: `app_business.py`**

To update currency symbols in the dashboard, find and replace these lines:

```python
# Line 276: Change
f"${data['financial_impact']['weekly_savings']:,}",
# To:
f"£{data['financial_impact']['weekly_savings']:,}",

# Line 284: Change  
f"${data['financial_impact']['revenue_protected']:,}",
# To:
f"£{data['financial_impact']['revenue_protected']:,}",

# Line 308: Change
st.success(f"**{product['name']}** {product['trend']} - {product['action']} (${product['impact']} opportunity)")
# To:
st.success(f"**{product['name']}** {product['trend']} - {product['action']} (£{product['impact']} opportunity)")

# Line 314: Change
st.warning(f"**{product['name']}** {product['trend']} - {product['action']} (${product['impact']} at risk)")
# To:
st.warning(f"**{product['name']}** {product['trend']} - {product['action']} (£{product['impact']} at risk)")
```

**Store Names in Dashboard:**

```python
# Lines 604-610: Change store names to UK locations
store_data = pd.DataFrame([
    {"Store": "Oxford Street", "Revenue": "£125K", "Revenue_Numeric": 125000, "Margin": "28%", "Margin_Numeric": 28, "Efficiency": "94%", "Efficiency_Numeric": 94, "ROI": "320%", "Status": "🟢 Excellent"},
    {"Store": "Covent Garden", "Revenue": "£98K", "Revenue_Numeric": 98000, "Margin": "25%", "Margin_Numeric": 25, "Efficiency": "89%", "Efficiency_Numeric": 89, "ROI": "285%", "Status": "🟢 Good"},
    {"Store": "Canary Wharf", "Revenue": "£87K", "Revenue_Numeric": 87000, "Margin": "30%", "Margin_Numeric": 30, "Efficiency": "91%", "Efficiency_Numeric": 91, "ROI": "295%", "Status": "🟢 Good"},
    {"Store": "Westfield", "Revenue": "£156K", "Revenue_Numeric": 156000, "Margin": "22%", "Margin_Numeric": 22, "Efficiency": "85%", "Efficiency_Numeric": 85, "ROI": "245%", "Status": "🟡 Monitor"},
    {"Store": "King's Road", "Revenue": "£76K", "Revenue_Numeric": 76000, "Margin": "26%", "Margin_Numeric": 26, "Efficiency": "88%", "Efficiency_Numeric": 88, "ROI": "275%", "Status": "🟢 Good"}
])
```

### 5. Main Application Dashboard

**File: `app.py`**

Update currency symbols:

```python
# Line 214-215: Change
f"${report['summary']['total_cost']:,.0f}",
delta=f"-${report['summary']['total_cost'] * 0.05:.0f}"
# To:
f"£{report['summary']['total_cost']:,.0f}",
delta=f"-£{report['summary']['total_cost'] * 0.05:.0f}"

# Line 254: Change
labels={'total_cost': 'Total Cost ($)', 'date': 'Date'}
# To:
labels={'total_cost': 'Total Cost (£)', 'date': 'Date'}

# Line 418: Change
st.metric("Unit Cost", f"${selected_product.unit_cost:.2f}")
# To:
st.metric("Unit Cost", f"£{selected_product.unit_cost:.2f}")

# Line 421: Change
st.metric("Selling Price", f"${selected_product.selling_price:.2f}")
# To:
st.metric("Selling Price", f"£{selected_product.selling_price:.2f}")
```

### 6. Utilities and Metrics

**File: `src/utils/metrics.py`**

Update currency units:

```python
# Line 184: Change
unit="$",
# To:
unit="£",

# Line 192: Change
unit="$",
# To:
unit="£",

# Line 200: Change
unit="$/unit",
# To:
unit="£/unit",

# Line 207: Change
unit="$/day",
# To:
unit="£/day",
```

### 7. Test Files

**File: `test_stock_grip.py`**

Update test output currency:

```python
# Line 213: Change
print(f"   Cost: ${action.cost:.2f}")
# To:
print(f"   Cost: £{action.cost:.2f}")

# Line 286: Change
print(f"   Total cost: ${result['total_cost']:.2f}")
# To:
print(f"   Total cost: £{result['total_cost']:.2f}")
```

## Automated Update Script

You can create a simple script to make all currency changes automatically:

**File: `update_currency.py`**

```python
#!/usr/bin/env python3
"""
Script to update all currency symbols from $ to £
"""
import os
import re

def update_currency_in_file(filepath):
    """Update currency symbols in a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace currency patterns
    patterns = [
        (r'\$\{([^}]+)\}', r'£{\1}'),  # ${variable} -> £{variable}
        (r'"\$([0-9,]+)"', r'"£\1"'),  # "$1,000" -> "£1,000"
        (r"'\$([0-9,]+)'", r"'£\1'"),  # '$1,000' -> '£1,000'
        (r'\$([0-9,]+)', r'£\1'),      # $1000 -> £1000
        (r'unit="\$"', r'unit="£"'),   # unit="$" -> unit="£"
        (r"unit='\$'", r"unit='£'"),   # unit='$' -> unit='£'
        (r'Total Cost \(\$\)', r'Total Cost (£)'),  # Chart labels
        (r'\$/unit', r'£/unit'),       # Units
        (r'\$/day', r'£/day'),         # Units
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated: {filepath}")

# Files to update
files_to_update = [
    'app.py',
    'app_business.py', 
    'src/utils/metrics.py',
    'test_stock_grip.py'
]

for filepath in files_to_update:
    if os.path.exists(filepath):
        update_currency_in_file(filepath)
    else:
        print(f"File not found: {filepath}")

print("Currency update complete!")
```

## Testing Your Changes

After making changes, test with:

```bash
# Generate sample data with new locations
python src/data/sample_data_generator.py generate

# Run the business dashboard
streamlit run app_business.py --server.port 8502

# Check the main dashboard
streamlit run app.py
```

## Summary of Changes

### Currency ($ to £):
1. ✅ **`config/localization.py`** - Main configuration (done)
2. ✅ **`src/utils/business_metrics.py`** - Business metrics (done)
3. **`app_business.py`** - Business dashboard (manual update needed)
4. **`app.py`** - Main dashboard (manual update needed)
5. **`src/utils/metrics.py`** - Utility metrics (manual update needed)
6. **`test_stock_grip.py`** - Test outputs (manual update needed)

### Locations:
1. ✅ **`config/localization.py`** - Location definitions (done)
2. ✅ **`src/data/sample_data_generator.py`** - Sample data (done)
3. **`app_business.py`** - Store names in dashboard (manual update needed)

The system is designed to be easily customizable. Most changes can be made in the `config/localization.py` file, with some manual updates needed in the dashboard files for display purposes.