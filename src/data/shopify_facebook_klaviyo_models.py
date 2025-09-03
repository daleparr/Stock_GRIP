"""
Extended data models for Shopify, Facebook, and Klaviyo integration
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from .models import Base, Product

class ShopifyOrderData(Base):
    """Raw Shopify order data"""
    __tablename__ = 'shopify_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shopify_order_id = Column(String, unique=True, nullable=False)
    order_number = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Customer information
    customer_id = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_first_name = Column(String, nullable=True)
    customer_last_name = Column(String, nullable=True)
    customer_orders_count = Column(Integer, default=1)
    customer_total_spent = Column(Float, default=0.0)
    
    # Order totals
    total_price = Column(Float, nullable=False)
    subtotal_price = Column(Float, nullable=False)
    total_tax = Column(Float, default=0.0)
    total_discounts = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    
    # Order status
    financial_status = Column(String, nullable=False)  # paid, pending, refunded, etc.
    fulfillment_status = Column(String, nullable=True)  # fulfilled, partial, unfulfilled
    
    # Location and shipping
    shipping_country = Column(String, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_postcode = Column(String, nullable=True)
    
    # Marketing attribution
    referring_site = Column(String, nullable=True)
    landing_site = Column(String, nullable=True)
    source_name = Column(String, nullable=True)  # web, pos, mobile_app, etc.
    
    # Raw JSON data for flexibility
    raw_data = Column(JSON, nullable=True)
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)

class ShopifyLineItemData(Base):
    """Shopify order line items (individual products)"""
    __tablename__ = 'shopify_line_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shopify_line_item_id = Column(String, unique=True, nullable=False)
    shopify_order_id = Column(String, ForeignKey('shopify_orders.shopify_order_id'), nullable=False)
    
    # Product information
    product_id = Column(String, nullable=False)  # Maps to our internal product_id
    variant_id = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    title = Column(String, nullable=False)
    variant_title = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    
    # Quantities and pricing
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_discount = Column(Float, default=0.0)
    
    # Product attributes
    weight = Column(Float, nullable=True)
    requires_shipping = Column(Boolean, default=True)
    taxable = Column(Boolean, default=True)
    
    # Fulfillment
    fulfillment_service = Column(String, default='manual')
    fulfillment_status = Column(String, nullable=True)
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("ShopifyOrderData", backref="line_items")

class FacebookAdsData(Base):
    """Facebook Ads performance data"""
    __tablename__ = 'facebook_ads_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    
    # Campaign structure
    campaign_id = Column(String, nullable=False)
    campaign_name = Column(String, nullable=False)
    adset_id = Column(String, nullable=False)
    adset_name = Column(String, nullable=False)
    ad_id = Column(String, nullable=False)
    ad_name = Column(String, nullable=False)
    
    # Performance metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0.0)
    reach = Column(Integer, default=0)
    frequency = Column(Float, default=0.0)
    
    # Conversion metrics
    purchases = Column(Integer, default=0)
    purchase_value = Column(Float, default=0.0)
    add_to_cart = Column(Integer, default=0)
    view_content = Column(Integer, default=0)
    initiate_checkout = Column(Integer, default=0)
    
    # Calculated metrics
    ctr = Column(Float, default=0.0)  # Click-through rate
    cpc = Column(Float, default=0.0)  # Cost per click
    cpm = Column(Float, default=0.0)  # Cost per mille
    roas = Column(Float, default=0.0)  # Return on ad spend
    
    # Audience targeting
    age_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    country = Column(String, nullable=True)
    interests = Column(Text, nullable=True)  # JSON string of interests
    
    # Product attribution (if available)
    attributed_products = Column(JSON, nullable=True)  # Products driven by this ad
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)

class KlaviyoEmailData(Base):
    """Klaviyo email campaign and flow data"""
    __tablename__ = 'klaviyo_email_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    
    # Campaign/Flow identification
    campaign_id = Column(String, nullable=True)
    campaign_name = Column(String, nullable=True)
    flow_id = Column(String, nullable=True)
    flow_name = Column(String, nullable=True)
    message_type = Column(String, nullable=False)  # 'campaign' or 'flow'
    
    # Email performance
    recipients = Column(Integer, default=0)
    delivered = Column(Integer, default=0)
    opens = Column(Integer, default=0)
    unique_opens = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    unique_clicks = Column(Integer, default=0)
    unsubscribes = Column(Integer, default=0)
    spam_complaints = Column(Integer, default=0)
    bounces = Column(Integer, default=0)
    
    # Revenue attribution
    attributed_revenue = Column(Float, default=0.0)
    attributed_orders = Column(Integer, default=0)
    
    # Calculated metrics
    delivery_rate = Column(Float, default=0.0)
    open_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    unsubscribe_rate = Column(Float, default=0.0)
    revenue_per_recipient = Column(Float, default=0.0)
    
    # Segmentation
    segment_name = Column(String, nullable=True)
    segment_size = Column(Integer, nullable=True)
    
    # Product attribution
    featured_products = Column(JSON, nullable=True)  # Products featured in email
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)

class KlaviyoCustomerData(Base):
    """Klaviyo customer profile and behavior data"""
    __tablename__ = 'klaviyo_customers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    klaviyo_person_id = Column(String, unique=True, nullable=False)
    
    # Customer identification
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Customer metrics
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    average_order_value = Column(Float, default=0.0)
    last_order_date = Column(DateTime, nullable=True)
    first_order_date = Column(DateTime, nullable=True)
    
    # Engagement metrics
    email_engagement_score = Column(Float, default=0.0)
    last_email_open = Column(DateTime, nullable=True)
    last_email_click = Column(DateTime, nullable=True)
    
    # Segmentation
    customer_segment = Column(String, default='regular')  # VIP, regular, at_risk, etc.
    lifecycle_stage = Column(String, default='active')  # new, active, at_risk, churned
    
    # Preferences
    email_subscribed = Column(Boolean, default=True)
    sms_subscribed = Column(Boolean, default=False)
    preferred_categories = Column(JSON, nullable=True)
    
    # Location
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    
    # Custom properties (flexible JSON field)
    custom_properties = Column(JSON, nullable=True)
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    timestamp_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IntegratedMarketingAttribution(Base):
    """Unified marketing attribution across all channels"""
    __tablename__ = 'marketing_attribution'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    
    # Order/Sale identification
    shopify_order_id = Column(String, ForeignKey('shopify_orders.shopify_order_id'), nullable=True)
    
    # Attribution channels
    first_touch_channel = Column(String, nullable=True)  # facebook, email, organic, etc.
    last_touch_channel = Column(String, nullable=True)
    
    # Facebook attribution
    facebook_campaign_id = Column(String, ForeignKey('facebook_ads_data.campaign_id'), nullable=True)
    facebook_attribution_window = Column(String, nullable=True)  # 1d_view, 7d_click, etc.
    
    # Email attribution
    klaviyo_campaign_id = Column(String, ForeignKey('klaviyo_email_data.campaign_id'), nullable=True)
    klaviyo_flow_id = Column(String, ForeignKey('klaviyo_email_data.flow_id'), nullable=True)
    
    # Attribution values
    attributed_revenue = Column(Float, default=0.0)
    attribution_weight = Column(Float, default=1.0)  # For multi-touch attribution
    
    # Customer journey
    customer_email = Column(String, nullable=True)
    touchpoint_sequence = Column(JSON, nullable=True)  # Journey mapping
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)

class ProductPerformanceAggregated(Base):
    """Aggregated product performance across all channels"""
    __tablename__ = 'product_performance_aggregated'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    
    # Sales metrics
    shopify_units_sold = Column(Integer, default=0)
    shopify_revenue = Column(Float, default=0.0)
    shopify_orders = Column(Integer, default=0)
    
    # Marketing metrics
    facebook_spend = Column(Float, default=0.0)
    facebook_impressions = Column(Integer, default=0)
    facebook_clicks = Column(Integer, default=0)
    facebook_attributed_revenue = Column(Float, default=0.0)
    
    # Email marketing metrics
    klaviyo_emails_sent = Column(Integer, default=0)
    klaviyo_emails_opened = Column(Integer, default=0)
    klaviyo_emails_clicked = Column(Integer, default=0)
    klaviyo_attributed_revenue = Column(Float, default=0.0)
    
    # Calculated performance metrics
    total_marketing_spend = Column(Float, default=0.0)
    total_attributed_revenue = Column(Float, default=0.0)
    marketing_roas = Column(Float, default=0.0)
    cost_per_acquisition = Column(Float, default=0.0)
    
    # Demand indicators
    search_volume = Column(Integer, default=0)  # If available from other sources
    social_mentions = Column(Integer, default=0)
    
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")