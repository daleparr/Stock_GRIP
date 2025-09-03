#!/usr/bin/env python3
"""
Test script for Shopify, Facebook, and Klaviyo data integration
"""
import os
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_shopify_facebook_klaviyo_integration():
    """Test the complete Shopify, Facebook, Klaviyo integration"""
    print("SHOPIFY, FACEBOOK & KLAVIYO INTEGRATION TEST")
    print("=" * 50)
    
    try:
        # Import the processor
        from src.data.shopify_facebook_klaviyo_processor import ShopifyFacebookKlaviyoProcessor
        from src.data.models import create_database, get_session
        from config.settings import DATABASE_URL
        
        print("1. Initializing processor...")
        processor = ShopifyFacebookKlaviyoProcessor()
        
        print("2. Processing CSV files...")
        results = processor.process_all_csv_files()
        
        print("\n3. Processing Results:")
        print("-" * 30)
        
        total_success = 0
        total_files = 0
        
        for file_type, result in results.items():
            if result:
                total_files += 1
                status_symbol = "SUCCESS" if result['status'] == 'success' else "FAILED"
                print(f"{status_symbol} {file_type}: {result['status']}")
                
                if result['status'] == 'success':
                    total_success += 1
                    # Show processing details
                    for key, value in result.items():
                        if key not in ['status', 'error'] and isinstance(value, (int, float)):
                            print(f"    {key}: {value}")
                else:
                    print(f"    Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"- {file_type}: Not processed (file not found)")
        
        print(f"\n4. Summary:")
        print(f"   Files processed successfully: {total_success}/{total_files}")
        
        if total_success == total_files:
            print("   Status: ALL INTEGRATIONS SUCCESSFUL!")
            
            # Test data queries
            print("\n5. Testing data queries...")
            test_data_queries(processor)
        else:
            print("   Status: Some integrations failed")
        
        processor.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_data_queries(processor):
    """Test SQL queries on the integrated data"""
    try:
        from sqlalchemy import text
        
        # Test 1: Check Shopify sales transformation
        print("\n   Testing Shopify sales transformation...")
        result = processor.session.execute(text("""
            SELECT COUNT(*) as sales_records FROM live_sales_data 
            WHERE channel = 'shopify'
        """)).fetchone()
        print(f"   - Shopify sales records: {result[0]}")
        
        # Test 2: Check demand signals
        print("   Testing demand signals...")
        result = processor.session.execute(text("""
            SELECT COUNT(*) as demand_records FROM live_demand_signals
        """)).fetchone()
        print(f"   - Demand signal records: {result[0]}")
        
        # Test 3: Check performance aggregation
        print("   Testing performance aggregation...")
        result = processor.session.execute(text("""
            SELECT COUNT(*) as performance_records FROM product_performance_aggregated
        """)).fetchone()
        print(f"   - Performance aggregation records: {result[0]}")
        
        # Test 4: Sample unified view
        print("   Testing unified product performance view...")
        result = processor.session.execute(text("""
            SELECT 
                product_id,
                shopify_units_sold,
                facebook_spend,
                klaviyo_emails_sent,
                total_attributed_revenue,
                marketing_roas
            FROM product_performance_aggregated 
            WHERE total_attributed_revenue > 0
            LIMIT 3
        """)).fetchall()
        
        if result:
            print("   - Sample unified performance data:")
            for row in result:
                print(f"     Product {row[0]}: {row[1]} units, £{row[2]:.2f} FB spend, "
                      f"{row[3]} emails, £{row[4]:.2f} revenue, {row[5]:.2f}x ROAS")
        
        print("   ✓ All data queries successful!")
        
    except Exception as e:
        print(f"   ✗ Data query error: {e}")

def generate_sample_data():
    """Generate additional sample data for testing"""
    print("\nGENERATING ADDITIONAL SAMPLE DATA")
    print("=" * 40)
    
    # This would be where you could add more sample data generation
    # For now, we'll use the existing CSV schema files
    
    csv_files = [
        "data/csv_schemas/shopify_orders_schema.csv",
        "data/csv_schemas/shopify_line_items_schema.csv", 
        "data/csv_schemas/facebook_ads_schema.csv",
        "data/csv_schemas/klaviyo_email_schema.csv"
    ]
    
    print("Sample CSV files available:")
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            file_size = os.path.getsize(csv_file)
            print(f"FOUND {csv_file} ({file_size} bytes)")
        else:
            print(f"MISSING {csv_file}")

def show_sql_examples():
    """Show example SQL queries for the integrated data"""
    print("\nSQL QUERY EXAMPLES")
    print("=" * 30)
    
    examples = [
        {
            "title": "Daily Revenue by Channel",
            "sql": """
SELECT 
    DATE(date) as sale_date,
    channel,
    SUM(revenue) as total_revenue,
    COUNT(*) as transaction_count
FROM live_sales_data 
WHERE date >= DATE('now', '-7 days')
GROUP BY DATE(date), channel
ORDER BY sale_date DESC, total_revenue DESC;
            """
        },
        {
            "title": "Facebook Ad Performance by Product",
            "sql": """
SELECT 
    JSON_EXTRACT(attributed_products, '$[0].product_id') as product_id,
    campaign_name,
    SUM(spend) as total_spend,
    SUM(purchase_value) as total_revenue,
    SUM(purchase_value) / SUM(spend) as roas
FROM facebook_ads_data 
WHERE attributed_products IS NOT NULL
GROUP BY JSON_EXTRACT(attributed_products, '$[0].product_id'), campaign_name
ORDER BY roas DESC;
            """
        },
        {
            "title": "Email Campaign Effectiveness",
            "sql": """
SELECT 
    campaign_name,
    SUM(recipients) as total_recipients,
    AVG(open_rate) as avg_open_rate,
    AVG(click_rate) as avg_click_rate,
    SUM(attributed_revenue) as total_revenue,
    SUM(attributed_revenue) / SUM(recipients) as revenue_per_recipient
FROM klaviyo_email_data 
WHERE message_type = 'campaign'
GROUP BY campaign_name
ORDER BY revenue_per_recipient DESC;
            """
        },
        {
            "title": "Unified Product Performance",
            "sql": """
SELECT 
    p.product_id,
    p.name,
    COALESCE(shop.units_sold, 0) as shopify_units,
    COALESCE(fb.spend, 0) as facebook_spend,
    COALESCE(kl.emails_sent, 0) as email_recipients,
    (COALESCE(shop.revenue, 0) + COALESCE(fb.attributed_revenue, 0) + COALESCE(kl.attributed_revenue, 0)) as total_revenue
FROM products p
LEFT JOIN product_performance_aggregated shop ON p.product_id = shop.product_id
LEFT JOIN (SELECT product_id, SUM(spend) as spend, SUM(purchase_value) as attributed_revenue FROM facebook_ads_data GROUP BY product_id) fb ON p.product_id = fb.product_id  
LEFT JOIN (SELECT product_id, SUM(recipients) as emails_sent, SUM(attributed_revenue) as attributed_revenue FROM klaviyo_email_data GROUP BY product_id) kl ON p.product_id = kl.product_id
ORDER BY total_revenue DESC;
            """
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(example['sql'])

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            test_shopify_facebook_klaviyo_integration()
        elif command == "generate":
            generate_sample_data()
        elif command == "sql":
            show_sql_examples()
        else:
            print("Unknown command. Use 'test', 'generate', or 'sql'")
    else:
        # Run full test by default
        test_shopify_facebook_klaviyo_integration()
        generate_sample_data()
        show_sql_examples()

if __name__ == "__main__":
    main()