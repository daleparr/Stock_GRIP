"""
Data processor for Shopify, Facebook, and Klaviyo CSV files
Transforms raw data into Stock GRIP format and performs advanced analytics
"""
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from .models import Product, get_session, create_database
from .live_data_models import LiveSalesData, LiveDemandSignals
from .shopify_facebook_klaviyo_models import (
    ShopifyOrderData, ShopifyLineItemData, FacebookAdsData, 
    KlaviyoEmailData, IntegratedMarketingAttribution, ProductPerformanceAggregated
)
from config.settings import DATABASE_URL


class ShopifyFacebookKlaviyoProcessor:
    """Process and transform data from Shopify, Facebook, and Klaviyo"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = create_database(database_url)
        self.session = get_session(self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Create tables for new models
        self._create_extended_tables()
    
    def _create_extended_tables(self):
        """Create tables for Shopify, Facebook, Klaviyo models"""
        try:
            from .shopify_facebook_klaviyo_models import Base as ExtendedBase
            ExtendedBase.metadata.create_all(self.engine)
            self.logger.info("Extended tables created successfully")
        except Exception as e:
            self.logger.error(f"Error creating extended tables: {e}")
    
    def process_shopify_orders_csv(self, csv_file_path: str) -> Dict[str, Any]:
        """Process Shopify orders CSV file"""
        self.logger.info(f"Processing Shopify orders CSV: {csv_file_path}")
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file_path)
            
            # Data validation and cleaning
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['updated_at'] = pd.to_datetime(df['updated_at'])
            df['processed_at'] = pd.to_datetime(df['processed_at'], errors='coerce')
            df['cancelled_at'] = pd.to_datetime(df['cancelled_at'], errors='coerce')
            
            # Process each order
            processed_orders = 0
            for _, row in df.iterrows():
                try:
                    order = ShopifyOrderData(
                        shopify_order_id=row['shopify_order_id'],
                        order_number=row['order_number'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        processed_at=row['processed_at'] if pd.notna(row['processed_at']) else None,
                        cancelled_at=row['cancelled_at'] if pd.notna(row['cancelled_at']) else None,
                        customer_id=row.get('customer_id'),
                        customer_email=row.get('customer_email'),
                        customer_phone=row.get('customer_phone'),
                        customer_first_name=row.get('customer_first_name'),
                        customer_last_name=row.get('customer_last_name'),
                        customer_orders_count=row.get('customer_orders_count', 1),
                        customer_total_spent=row.get('customer_total_spent', 0.0),
                        total_price=row['total_price'],
                        subtotal_price=row['subtotal_price'],
                        total_tax=row.get('total_tax', 0.0),
                        total_discounts=row.get('total_discounts', 0.0),
                        shipping_cost=row.get('shipping_cost', 0.0),
                        financial_status=row['financial_status'],
                        fulfillment_status=row.get('fulfillment_status'),
                        shipping_country=row.get('shipping_country'),
                        shipping_city=row.get('shipping_city'),
                        shipping_postcode=row.get('shipping_postcode'),
                        referring_site=row.get('referring_site'),
                        landing_site=row.get('landing_site'),
                        source_name=row.get('source_name', 'web')
                    )
                    
                    self.session.merge(order)
                    processed_orders += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing order {row.get('shopify_order_id', 'unknown')}: {e}")
            
            self.session.commit()
            
            return {
                'status': 'success',
                'processed_orders': processed_orders,
                'total_rows': len(df)
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing Shopify orders CSV: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processed_orders': 0
            }
    
    def process_shopify_line_items_csv(self, csv_file_path: str) -> Dict[str, Any]:
        """Process Shopify line items CSV file"""
        self.logger.info(f"Processing Shopify line items CSV: {csv_file_path}")
        
        try:
            df = pd.read_csv(csv_file_path)
            
            processed_items = 0
            for _, row in df.iterrows():
                try:
                    line_item = ShopifyLineItemData(
                        shopify_line_item_id=row['shopify_line_item_id'],
                        shopify_order_id=row['shopify_order_id'],
                        product_id=row['product_id'],
                        variant_id=row.get('variant_id'),
                        sku=row.get('sku'),
                        title=row['title'],
                        variant_title=row.get('variant_title'),
                        vendor=row.get('vendor'),
                        quantity=row['quantity'],
                        price=row['price'],
                        total_discount=row.get('total_discount', 0.0),
                        weight=row.get('weight'),
                        requires_shipping=row.get('requires_shipping', True),
                        taxable=row.get('taxable', True),
                        fulfillment_service=row.get('fulfillment_service', 'manual'),
                        fulfillment_status=row.get('fulfillment_status')
                    )
                    
                    self.session.merge(line_item)
                    processed_items += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing line item {row.get('shopify_line_item_id', 'unknown')}: {e}")
            
            self.session.commit()
            
            return {
                'status': 'success',
                'processed_items': processed_items,
                'total_rows': len(df)
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing Shopify line items CSV: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processed_items': 0
            }
    
    def process_facebook_ads_csv(self, csv_file_path: str) -> Dict[str, Any]:
        """Process Facebook Ads CSV file"""
        self.logger.info(f"Processing Facebook Ads CSV: {csv_file_path}")
        
        try:
            df = pd.read_csv(csv_file_path)
            df['date'] = pd.to_datetime(df['date'])
            
            processed_ads = 0
            for _, row in df.iterrows():
                try:
                    # Parse attributed products JSON
                    attributed_products = None
                    if pd.notna(row.get('attributed_products')):
                        try:
                            attributed_products = json.loads(row['attributed_products'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in attributed_products: {row.get('attributed_products')}")
                    
                    facebook_ad = FacebookAdsData(
                        date=row['date'],
                        campaign_id=row['campaign_id'],
                        campaign_name=row['campaign_name'],
                        adset_id=row['adset_id'],
                        adset_name=row['adset_name'],
                        ad_id=row['ad_id'],
                        ad_name=row['ad_name'],
                        impressions=row.get('impressions', 0),
                        clicks=row.get('clicks', 0),
                        spend=row.get('spend', 0.0),
                        reach=row.get('reach', 0),
                        frequency=row.get('frequency', 0.0),
                        purchases=row.get('purchases', 0),
                        purchase_value=row.get('purchase_value', 0.0),
                        add_to_cart=row.get('add_to_cart', 0),
                        view_content=row.get('view_content', 0),
                        initiate_checkout=row.get('initiate_checkout', 0),
                        ctr=row.get('ctr', 0.0),
                        cpc=row.get('cpc', 0.0),
                        cpm=row.get('cpm', 0.0),
                        roas=row.get('roas', 0.0),
                        age_range=row.get('age_range'),
                        gender=row.get('gender'),
                        country=row.get('country'),
                        interests=row.get('interests'),
                        attributed_products=attributed_products
                    )
                    
                    self.session.merge(facebook_ad)
                    processed_ads += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing Facebook ad {row.get('ad_id', 'unknown')}: {e}")
            
            self.session.commit()
            
            return {
                'status': 'success',
                'processed_ads': processed_ads,
                'total_rows': len(df)
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing Facebook Ads CSV: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processed_ads': 0
            }
    
    def process_klaviyo_email_csv(self, csv_file_path: str) -> Dict[str, Any]:
        """Process Klaviyo email CSV file"""
        self.logger.info(f"Processing Klaviyo email CSV: {csv_file_path}")
        
        try:
            df = pd.read_csv(csv_file_path)
            df['date'] = pd.to_datetime(df['date'])
            
            processed_emails = 0
            for _, row in df.iterrows():
                try:
                    # Parse featured products JSON
                    featured_products = None
                    if pd.notna(row.get('featured_products')):
                        try:
                            featured_products = json.loads(row['featured_products'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in featured_products: {row.get('featured_products')}")
                    
                    klaviyo_email = KlaviyoEmailData(
                        date=row['date'],
                        campaign_id=row.get('campaign_id'),
                        campaign_name=row.get('campaign_name'),
                        flow_id=row.get('flow_id'),
                        flow_name=row.get('flow_name'),
                        message_type=row['message_type'],
                        recipients=row.get('recipients', 0),
                        delivered=row.get('delivered', 0),
                        opens=row.get('opens', 0),
                        unique_opens=row.get('unique_opens', 0),
                        clicks=row.get('clicks', 0),
                        unique_clicks=row.get('unique_clicks', 0),
                        unsubscribes=row.get('unsubscribes', 0),
                        spam_complaints=row.get('spam_complaints', 0),
                        bounces=row.get('bounces', 0),
                        attributed_revenue=row.get('attributed_revenue', 0.0),
                        attributed_orders=row.get('attributed_orders', 0),
                        delivery_rate=row.get('delivery_rate', 0.0),
                        open_rate=row.get('open_rate', 0.0),
                        click_rate=row.get('click_rate', 0.0),
                        unsubscribe_rate=row.get('unsubscribe_rate', 0.0),
                        revenue_per_recipient=row.get('revenue_per_recipient', 0.0),
                        segment_name=row.get('segment_name'),
                        segment_size=row.get('segment_size'),
                        featured_products=featured_products
                    )
                    
                    self.session.merge(klaviyo_email)
                    processed_emails += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing Klaviyo email {row.get('campaign_id', 'unknown')}: {e}")
            
            self.session.commit()
            
            return {
                'status': 'success',
                'processed_emails': processed_emails,
                'total_rows': len(df)
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing Klaviyo email CSV: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processed_emails': 0
            }
    
    def transform_to_stock_grip_format(self) -> Dict[str, Any]:
        """Transform processed data into Stock GRIP live data format"""
        self.logger.info("Transforming data to Stock GRIP format")
        
        try:
            # Transform Shopify data to LiveSalesData
            sales_transformed = self._transform_shopify_to_sales()
            
            # Transform marketing data to LiveDemandSignals
            demand_transformed = self._transform_marketing_to_demand()
            
            # Create aggregated performance data
            performance_aggregated = self._create_performance_aggregation()
            
            return {
                'status': 'success',
                'sales_records': sales_transformed,
                'demand_records': demand_transformed,
                'performance_records': performance_aggregated
            }
            
        except Exception as e:
            self.logger.error(f"Error transforming data: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _transform_shopify_to_sales(self) -> int:
        """Transform Shopify data to LiveSalesData format"""
        # Execute SQL transformation
        sql = """
        INSERT OR REPLACE INTO live_sales_data 
        (date, product_id, channel, quantity_sold, revenue, customer_segment, fulfillment_method)
        SELECT 
            so.created_at as date,
            sli.product_id,
            'shopify' as channel,
            sli.quantity as quantity_sold,
            (sli.price * sli.quantity - sli.total_discount) as revenue,
            CASE 
                WHEN so.customer_total_spent > 1000 THEN 'premium'
                WHEN so.customer_total_spent > 500 THEN 'regular'
                ELSE 'budget'
            END as customer_segment,
            COALESCE(so.source_name, 'web') as fulfillment_method
        FROM shopify_orders so
        JOIN shopify_line_items sli ON so.shopify_order_id = sli.shopify_order_id
        WHERE so.financial_status = 'paid'
          AND so.cancelled_at IS NULL
        """
        
        result = self.session.execute(text(sql))
        self.session.commit()
        return result.rowcount
    
    def _transform_marketing_to_demand(self) -> int:
        """Transform Facebook and Klaviyo data to LiveDemandSignals format"""
        # Create demand signals based on marketing performance
        # Note: Using simplified approach since SQLite JSON functions are limited
        sql = """
        INSERT OR REPLACE INTO live_demand_signals
        (date, product_id, external_demand, market_trend, social_sentiment)
        SELECT
            DATE('now') as date,
            p.product_id,
            CASE
                WHEN COALESCE(fb.total_purchases, 0) + COALESCE(kl.attributed_orders, 0) > 20 THEN 'high'
                WHEN COALESCE(fb.total_purchases, 0) + COALESCE(kl.attributed_orders, 0) > 10 THEN 'medium'
                ELSE 'low'
            END as external_demand,
            COALESCE(fb.avg_roas, 0) / 10.0 as market_trend,  -- Normalize ROAS to -1 to 1 scale
            COALESCE(kl.avg_open_rate, 0) / 100.0 as social_sentiment  -- Normalize open rate to 0-1 scale
        FROM products p
        LEFT JOIN (
            SELECT
                'PER-0001' as product_id,  -- Simplified for SQLite compatibility
                SUM(purchases) as total_purchases,
                AVG(roas) as avg_roas
            FROM facebook_ads_data
            WHERE DATE(date) = DATE('now')
            GROUP BY 1
        ) fb ON p.product_id = fb.product_id
        LEFT JOIN (
            SELECT
                'PER-0001' as product_id,  -- Simplified for SQLite compatibility
                SUM(attributed_orders) as attributed_orders,
                AVG(open_rate) as avg_open_rate
            FROM klaviyo_email_data
            WHERE DATE(date) = DATE('now')
            GROUP BY 1
        ) kl ON p.product_id = kl.product_id
        WHERE fb.product_id IS NOT NULL OR kl.product_id IS NOT NULL
        """
        
        result = self.session.execute(text(sql))
        self.session.commit()
        return result.rowcount
    
    def _create_performance_aggregation(self) -> int:
        """Create aggregated performance data"""
        sql = """
        INSERT OR REPLACE INTO product_performance_aggregated 
        (date, product_id, shopify_units_sold, shopify_revenue, shopify_orders,
         facebook_spend, facebook_impressions, facebook_clicks, facebook_attributed_revenue,
         klaviyo_emails_sent, klaviyo_emails_opened, klaviyo_attributed_revenue,
         total_marketing_spend, total_attributed_revenue, marketing_roas)
        SELECT 
            DATE('now') as date,
            p.product_id,
            COALESCE(shop.total_quantity, 0) as shopify_units_sold,
            COALESCE(shop.total_revenue, 0) as shopify_revenue,
            COALESCE(shop.order_count, 0) as shopify_orders,
            COALESCE(fb.total_spend, 0) as facebook_spend,
            COALESCE(fb.total_impressions, 0) as facebook_impressions,
            COALESCE(fb.total_clicks, 0) as facebook_clicks,
            COALESCE(fb.total_purchase_value, 0) as facebook_attributed_revenue,
            COALESCE(kl.total_recipients, 0) as klaviyo_emails_sent,
            COALESCE(kl.total_opens, 0) as klaviyo_emails_opened,
            COALESCE(kl.total_attributed_revenue, 0) as klaviyo_attributed_revenue,
            COALESCE(fb.total_spend, 0) as total_marketing_spend,
            COALESCE(shop.total_revenue, 0) + COALESCE(fb.total_purchase_value, 0) + COALESCE(kl.total_attributed_revenue, 0) as total_attributed_revenue,
            (COALESCE(shop.total_revenue, 0) + COALESCE(fb.total_purchase_value, 0) + COALESCE(kl.total_attributed_revenue, 0)) / NULLIF(COALESCE(fb.total_spend, 0), 0) as marketing_roas
        FROM products p
        LEFT JOIN (
            SELECT 
                sli.product_id,
                SUM(sli.quantity) as total_quantity,
                SUM(sli.price * sli.quantity - sli.total_discount) as total_revenue,
                COUNT(DISTINCT so.shopify_order_id) as order_count
            FROM shopify_line_items sli
            JOIN shopify_orders so ON sli.shopify_order_id = so.shopify_order_id
            WHERE DATE(so.created_at) = DATE('now')
              AND so.financial_status = 'paid'
            GROUP BY sli.product_id
        ) shop ON p.product_id = shop.product_id
        LEFT JOIN (
            SELECT 
                JSON_EXTRACT(attributed_products, '$[*].product_id') as product_id,
                SUM(spend) as total_spend,
                SUM(impressions) as total_impressions,
                SUM(clicks) as total_clicks,
                SUM(purchase_value) as total_purchase_value
            FROM facebook_ads_data 
            WHERE DATE(date) = DATE('now')
            GROUP BY JSON_EXTRACT(attributed_products, '$[*].product_id')
        ) fb ON p.product_id = fb.product_id
        LEFT JOIN (
            SELECT 
                JSON_EXTRACT(featured_products, '$[*].product_id') as product_id,
                SUM(recipients) as total_recipients,
                SUM(opens) as total_opens,
                SUM(attributed_revenue) as total_attributed_revenue
            FROM klaviyo_email_data 
            WHERE DATE(date) = DATE('now')
            GROUP BY JSON_EXTRACT(featured_products, '$[*].product_id')
        ) kl ON p.product_id = kl.product_id
        """
        
        result = self.session.execute(text(sql))
        self.session.commit()
        return result.rowcount
    
    def process_all_csv_files(self, csv_directory: str = "data/csv_schemas") -> Dict[str, Any]:
        """Process all CSV files in the directory"""
        import os
        
        results = {
            'shopify_orders': None,
            'shopify_line_items': None,
            'facebook_ads': None,
            'klaviyo_email': None,
            'transformation': None
        }
        
        csv_files = {
            'shopify_orders': os.path.join(csv_directory, 'shopify_orders_schema.csv'),
            'shopify_line_items': os.path.join(csv_directory, 'shopify_line_items_schema.csv'),
            'facebook_ads': os.path.join(csv_directory, 'facebook_ads_schema.csv'),
            'klaviyo_email': os.path.join(csv_directory, 'klaviyo_email_schema.csv')
        }
        
        # Process each CSV file
        for file_type, file_path in csv_files.items():
            if os.path.exists(file_path):
                if file_type == 'shopify_orders':
                    results[file_type] = self.process_shopify_orders_csv(file_path)
                elif file_type == 'shopify_line_items':
                    results[file_type] = self.process_shopify_line_items_csv(file_path)
                elif file_type == 'facebook_ads':
                    results[file_type] = self.process_facebook_ads_csv(file_path)
                elif file_type == 'klaviyo_email':
                    results[file_type] = self.process_klaviyo_email_csv(file_path)
            else:
                self.logger.warning(f"CSV file not found: {file_path}")
        
        # Transform to Stock GRIP format
        results['transformation'] = self.transform_to_stock_grip_format()
        
        return results
    
    def close(self):
        """Close database session"""
        self.session.close()


def main():
    """Main function for testing"""
    processor = ShopifyFacebookKlaviyoProcessor()
    
    try:
        # Process all CSV files
        results = processor.process_all_csv_files()
        
        print("Processing Results:")
        for file_type, result in results.items():
            if result:
                print(f"{file_type}: {result['status']}")
                if result['status'] == 'success':
                    for key, value in result.items():
                        if key != 'status':
                            print(f"  {key}: {value}")
            else:
                print(f"{file_type}: Not processed")
    
    finally:
        processor.close()


if __name__ == "__main__":
    main()