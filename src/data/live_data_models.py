"""
Extended data models for live data integration
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from .models import Base, Product

class LiveSalesData(Base):
    """Live sales data from e-commerce, POS, and marketplace channels"""
    __tablename__ = 'live_sales_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    channel = Column(String, nullable=False)  # 'online', 'pos', 'marketplace'
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False)
    customer_segment = Column(String, default='regular')  # 'premium', 'regular', 'budget'
    promotion_code = Column(String, nullable=True)
    fulfillment_method = Column(String, default='warehouse')  # 'warehouse', 'store_pickup', 'dropship'
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")

class LiveInventoryUpdate(Base):
    """Live inventory updates from various sources"""
    __tablename__ = 'live_inventory_updates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    location = Column(String, nullable=False)  # 'warehouse_a', 'store_01', etc.
    stock_level = Column(Integer, nullable=False)
    reserved_stock = Column(Integer, default=0)
    in_transit = Column(Integer, default=0)
    supplier_id = Column(String, nullable=True)
    last_reorder_date = Column(DateTime, nullable=True)
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")

class LiveDemandSignals(Base):
    """External demand signals and market indicators"""
    __tablename__ = 'live_demand_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    external_demand = Column(String, nullable=False)  # 'high', 'medium', 'low'
    market_trend = Column(Float, default=0.0)  # -1.0 to 1.0
    competitor_price = Column(Float, nullable=True)
    weather_factor = Column(String, default='normal')  # 'hot', 'cold', 'rainy', 'normal'
    event_impact = Column(String, default='none')  # 'promotion', 'holiday', 'none'
    social_sentiment = Column(Float, default=0.0)  # -1.0 to 1.0
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")

class DataIngestionLog(Base):
    """Log of data ingestion activities"""
    __tablename__ = 'data_ingestion_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'sales', 'inventory', 'demand'
    records_processed = Column(Integer, default=0)
    records_successful = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    processing_time_seconds = Column(Float, default=0.0)
    status = Column(String, default='pending')  # 'pending', 'success', 'failed', 'partial'
    error_details = Column(Text, nullable=True)
    
    def set_error_details(self, errors_dict):
        """Store error details as JSON string"""
        self.error_details = json.dumps(errors_dict)
    
    def get_error_details(self):
        """Retrieve error details from JSON string"""
        return json.loads(self.error_details) if self.error_details else {}

class DataQualityMetrics(Base):
    """Data quality metrics for monitoring"""
    __tablename__ = 'data_quality_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    data_source = Column(String, nullable=False)  # 'sales', 'inventory', 'demand'
    metric_name = Column(String, nullable=False)  # 'completeness', 'accuracy', 'timeliness'
    metric_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # 'pass', 'warning', 'fail'
    details = Column(Text, nullable=True)
    
    def set_details(self, details_dict):
        """Store details as JSON string"""
        self.details = json.dumps(details_dict)
    
    def get_details(self):
        """Retrieve details from JSON string"""
        return json.loads(self.details) if self.details else {}