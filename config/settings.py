"""
Configuration settings for Stock_GRIP application
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Database configuration
DATABASE_URL = f"sqlite:///{DATA_DIR}/stock_grip.db"

# Live Data Configuration
LIVE_DATA_CONFIG = {
    'data_directory': 'data/live_data/',
    'supported_formats': ['csv'],
    'max_file_size_mb': 100,
    'required_columns': {
        'product_performance': [
            'date', 'product_id', 'product_name',
            'shopify_units_sold', 'shopify_revenue'
        ],
        'marketing_attribution': [
            'date', 'shopify_order_id', 'customer_email',
            'total_attributed_revenue'
        ]
    },
    'validation_rules': {
        'min_products': 1,
        'max_days_old': 90,
        'required_revenue_fields': ['shopify_revenue', 'total_attributed_revenue']
    }
}

# Optimization parameters
GP_EIMS_CONFIG = {
    "max_iterations": 50,
    "acquisition_function": "EI",  # Expected Improvement
    "kernel": "RBF",
    "noise_variance": 0.01,
    "optimization_interval_days": 7,  # Weekly strategic optimization
    "kernel_bounds": {
        "constant_value": (1e-5, 1e5),  # Wider bounds for constant kernel
        "length_scale": (1e-3, 1e3),    # Wider bounds for RBF length scale
    },
    "n_restarts_optimizer": 10,  # Number of restarts for kernel optimization
    "optimizer": "fmin_l_bfgs_b",  # Optimizer for kernel hyperparameters
    "max_iter": 1000,            # Maximum iterations for acquisition optimization
    "n_candidates": 20,          # Number of candidate points for acquisition
    "normalize_y": True,         # Normalize target values
    "warning_suppression": True, # Suppress convergence warnings in production
}

MPC_RL_CONFIG = {
    "prediction_horizon": 7,  # Days ahead
    "control_horizon": 3,     # Days of control actions
    "learning_rate": 0.001,
    "discount_factor": 0.95,
    "exploration_rate": 0.1,
    "batch_size": 32,
    "memory_size": 10000,
}

# E-commerce simulation parameters
SIMULATION_CONFIG = {
    "num_products": 50,
    "simulation_days": 365,
    "warehouse_capacity": 100000,  # units
    "service_level_target": 0.95,
    "holding_cost_rate": 0.25,    # Annual rate
    "stockout_penalty": 10.0,     # Per unit
    "order_cost": 50.0,           # Fixed cost per order
}

# Product categories for FMCG
PRODUCT_CATEGORIES = {
    "personal_care": {
        "demand_volatility": 0.15,
        "seasonality_factor": 1.2,
        "shelf_life_days": 730,
        "lead_time_range": (3, 7),
        "unit_cost_range": (5, 25),
    },
    "food_beverage": {
        "demand_volatility": 0.25,
        "seasonality_factor": 1.5,
        "shelf_life_days": 180,
        "lead_time_range": (1, 5),
        "unit_cost_range": (2, 15),
    },
    "household": {
        "demand_volatility": 0.10,
        "seasonality_factor": 1.1,
        "shelf_life_days": 1095,
        "lead_time_range": (5, 14),
        "unit_cost_range": (8, 40),
    },
    "electronics": {
        "demand_volatility": 0.30,
        "seasonality_factor": 1.8,
        "shelf_life_days": 1825,
        "lead_time_range": (7, 21),
        "unit_cost_range": (15, 100),
    },
}

# Dashboard configuration
DASHBOARD_CONFIG = {
    "refresh_interval": 30,  # seconds
    "chart_height": 400,
    "max_display_products": 20,
    "default_time_range": 30,  # days
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
    "rotation": "1 week",
    "retention": "1 month",
}

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)