"""
Database models for Stock_GRIP application
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class Product(Base):
    """Product information table"""
    __tablename__ = 'products'
    
    product_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit_cost = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    shelf_life_days = Column(Integer, nullable=False)
    min_order_quantity = Column(Integer, default=1)
    max_order_quantity = Column(Integer, default=10000)
    
    # Relationships
    inventory_records = relationship("Inventory", back_populates="product")
    demand_records = relationship("Demand", back_populates="product")
    optimization_params = relationship("OptimizationParameters", back_populates="product")

class Inventory(Base):
    """Current and historical inventory levels"""
    __tablename__ = 'inventory'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    stock_level = Column(Integer, nullable=False)
    reserved_stock = Column(Integer, default=0)
    in_transit = Column(Integer, default=0)
    available_stock = Column(Integer, nullable=False)  # stock_level - reserved_stock
    
    # Relationships
    product = relationship("Product", back_populates="inventory_records")

class Demand(Base):
    """Historical and forecasted demand data"""
    __tablename__ = 'demand'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    date = Column(DateTime, nullable=False)
    quantity_demanded = Column(Integer, nullable=False)
    quantity_fulfilled = Column(Integer, nullable=False)
    is_forecast = Column(Boolean, default=False)
    confidence_interval = Column(Float, default=0.95)
    
    # Relationships
    product = relationship("Product", back_populates="demand_records")

class OptimizationParameters(Base):
    """Strategic optimization parameters from GP-EIMS"""
    __tablename__ = 'optimization_parameters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reorder_point = Column(Integer, nullable=False)
    safety_stock = Column(Integer, nullable=False)
    order_quantity = Column(Integer, nullable=False)
    review_period_days = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # GP-EIMS specific fields
    gp_mean = Column(Float)
    gp_variance = Column(Float)
    acquisition_value = Column(Float)
    
    # Relationships
    product = relationship("Product", back_populates="optimization_params")

class OptimizationResults(Base):
    """Results from both GP-EIMS and MPC-RL-MOBO optimization runs"""
    __tablename__ = 'optimization_results'
    
    run_id = Column(String, primary_key=True)
    method = Column(String, nullable=False)  # 'GP-EIMS' or 'MPC-RL-MOBO'
    timestamp = Column(DateTime, default=datetime.utcnow)
    parameters = Column(Text)  # JSON string of parameters
    objective_value = Column(Float)
    constraints_satisfied = Column(Boolean, default=True)
    execution_time_seconds = Column(Float)
    
    # Method-specific fields
    convergence_iterations = Column(Integer)
    final_error = Column(Float)
    
    def set_parameters(self, params_dict):
        """Store parameters as JSON string"""
        self.parameters = json.dumps(params_dict)
    
    def get_parameters(self):
        """Retrieve parameters from JSON string"""
        return json.loads(self.parameters) if self.parameters else {}

class InventoryActions(Base):
    """Real-time inventory actions from MPC-RL-MOBO"""
    __tablename__ = 'inventory_actions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String, nullable=False)  # 'order', 'transfer', 'adjust'
    quantity = Column(Integer, nullable=False)
    expected_delivery = Column(DateTime)
    cost = Column(Float)
    
    # MPC-RL specific fields
    state_vector = Column(Text)  # JSON string of state information
    q_value = Column(Float)
    reward = Column(Float)
    
    def set_state_vector(self, state_dict):
        """Store state vector as JSON string"""
        self.state_vector = json.dumps(state_dict)
    
    def get_state_vector(self):
        """Retrieve state vector from JSON string"""
        return json.loads(self.state_vector) if self.state_vector else {}

class PerformanceMetrics(Base):
    """System performance tracking"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_category = Column(String, nullable=False)  # 'cost', 'service', 'efficiency'
    time_period = Column(String, default='daily')  # 'daily', 'weekly', 'monthly'
    
class SimulationRuns(Base):
    """Simulation execution tracking"""
    __tablename__ = 'simulation_runs'
    
    run_id = Column(String, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    scenario_config = Column(Text)  # JSON string of simulation parameters
    total_cost = Column(Float)
    service_level = Column(Float)
    stockout_events = Column(Integer, default=0)
    total_orders = Column(Integer, default=0)
    
    def set_scenario_config(self, config_dict):
        """Store scenario configuration as JSON string"""
        self.scenario_config = json.dumps(config_dict)
    
    def get_scenario_config(self):
        """Retrieve scenario configuration from JSON string"""
        return json.loads(self.scenario_config) if self.scenario_config else {}

# Database utility functions
def create_database(database_url: str):
    """Create database and all tables"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Also create live data tables
    try:
        from .live_data_models import Base as LiveBase
        LiveBase.metadata.create_all(engine)
    except ImportError:
        pass  # Live data models not available
    
    return engine

def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()