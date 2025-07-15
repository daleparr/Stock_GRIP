# Stock_GRIP User Guide

**G**aussian **R**einforcement **I**nventory **P**latform

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [System Architecture](#system-architecture)
4. [Dashboard Guide](#dashboard-guide)
5. [Optimization Methods](#optimization-methods)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

## Introduction

Stock_GRIP is an advanced inventory optimization platform that combines two powerful approaches:

- **GP-EIMS**: Gaussian Process Expected Improvement Method for strategic parameter tuning
- **MPC-RL-MOBO**: Model Predictive Control + Reinforcement Learning + Multi-Objective Bayesian Optimization for real-time decisions

### Key Features

- 🧠 **Hybrid Optimization**: Strategic and tactical optimization working together
- 📊 **Real-time Dashboard**: Interactive monitoring and control interface
- 🎯 **E-commerce Focus**: Optimized for fast-moving consumer goods (FMCG)
- 📈 **Performance Metrics**: Comprehensive KPI tracking and alerting
- 🎮 **Simulation Environment**: Test strategies before deployment
- 🔄 **Continuous Learning**: Adaptive algorithms that improve over time

## Quick Start

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Stock_GRIP
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:
```bash
streamlit run app.py
```

4. **Initialize the system**:
   - Open your browser to `http://localhost:8501`
   - Navigate to "System Control"
   - Click "🚀 Initialize System"

### First Steps

1. **Generate Sample Data**: The system will create realistic FMCG inventory data
2. **Run Strategic Optimization**: GP-EIMS will optimize inventory parameters
3. **Start Tactical Optimization**: MPC-RL-MOBO will begin real-time decisions
4. **Monitor Performance**: View KPIs and metrics on the dashboard

## System Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Layer    │    │ Optimization    │    │  Application    │
│                 │    │    Engines      │    │     Layer       │
│ • SQLite DB     │◄──►│ • GP-EIMS       │◄──►│ • Streamlit     │
│ • Data Pipeline │    │ • MPC-RL-MOBO   │    │ • Dashboard     │
│ • Validation    │    │ • Coordinator   │    │ • API           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Simulation    │    │   Performance   │    │     Config      │
│                 │    │   Monitoring    │    │                 │
│ • Environment   │    │ • Metrics       │    │ • Settings      │
│ • Strategies    │    │ • Alerts        │    │ • Parameters    │
│ • Validation    │    │ • Reporting     │    │ • Categories    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Data Generation**: Synthetic FMCG data with realistic patterns
2. **Strategic Optimization**: GP-EIMS runs weekly to set parameters
3. **Tactical Optimization**: MPC-RL-MOBO makes real-time decisions
4. **Coordination**: System ensures consistency between approaches
5. **Monitoring**: Continuous performance tracking and alerting

## Dashboard Guide

### Main Dashboard

The main dashboard provides an overview of system performance:

- **Key Metrics**: Service level, demand, cost, and product count
- **Trend Charts**: Daily service level and cost trends
- **Product Performance**: Top performers and improvement opportunities

### System Control

Control and monitor the optimization system:

- **System Status**: Current state of all components
- **Manual Controls**: Start/stop optimization, run cycles
- **Optimization Schedule**: View timing of strategic optimization

### Product Analysis

Detailed analysis of individual products:

- **Product Details**: Cost, pricing, lead times, margins
- **Demand Analysis**: Historical demand vs fulfillment
- **Optimization Parameters**: Current reorder points, safety stock

### Optimization Results

View and analyze optimization performance:

- **Recent Runs**: History of optimization executions
- **Method Comparison**: Performance comparison between GP-EIMS and MPC-RL-MOBO
- **Convergence Analysis**: Optimization efficiency metrics

### Data Quality

Monitor and validate data integrity:

- **Quality Checks**: Automated validation of data consistency
- **Issue Detection**: Identify missing data, anomalies, inconsistencies
- **Data Completeness**: Coverage and freshness metrics

## Optimization Methods

### GP-EIMS (Strategic Optimization)

**Purpose**: Optimize inventory control parameters periodically

**How it works**:
1. Uses Gaussian Processes to model uncertainty in objective function
2. Expected Improvement acquisition function guides parameter search
3. Bayesian optimization efficiently explores parameter space
4. Runs weekly to update strategic parameters

**Parameters Optimized**:
- Reorder points
- Safety stock levels
- Order quantities
- Review periods

**Benefits**:
- Efficient optimization (22× faster than genetic algorithms)
- Uncertainty quantification
- Robust to noisy evaluations
- Principled exploration vs exploitation

### MPC-RL-MOBO (Tactical Optimization)

**Purpose**: Make real-time inventory replenishment decisions

**How it works**:
1. Model Predictive Control predicts future demand and constraints
2. Reinforcement Learning adapts to changing conditions
3. Multi-Objective optimization balances cost vs service level
4. Runs continuously (every 30 minutes by default)

**Decisions Made**:
- When to place orders
- How much to order
- Distribution between locations
- Emergency replenishment

**Benefits**:
- Real-time adaptation
- Constraint satisfaction
- Multi-objective optimization
- Continuous learning

### Coordination Logic

The coordination system ensures both approaches work together effectively:

1. **Parameter Handoff**: GP-EIMS results feed into MPC-RL-MOBO
2. **Consistency Validation**: Checks for conflicts between approaches
3. **Performance Monitoring**: Tracks overall system effectiveness
4. **Adaptive Tuning**: Adjusts parameters based on performance

## Configuration

### Key Configuration Files

- **`config/settings.py`**: Main configuration parameters
- **`requirements.txt`**: Python dependencies
- **Database**: SQLite database in `data/` directory

### Important Settings

#### GP-EIMS Configuration
```python
GP_EIMS_CONFIG = {
    "max_iterations": 50,           # Maximum optimization iterations
    "acquisition_function": "EI",   # Expected Improvement
    "optimization_interval_days": 7 # Weekly optimization
}
```

#### MPC-RL Configuration
```python
MPC_RL_CONFIG = {
    "prediction_horizon": 7,    # Days ahead to predict
    "control_horizon": 3,       # Days of control actions
    "learning_rate": 0.001,     # RL learning rate
    "exploration_rate": 0.1     # RL exploration rate
}
```

#### Simulation Configuration
```python
SIMULATION_CONFIG = {
    "service_level_target": 0.95,  # 95% service level target
    "holding_cost_rate": 0.25,     # Annual holding cost rate
    "stockout_penalty": 10.0       # Cost per stockout unit
}
```

### Product Categories

The system supports four FMCG categories:

1. **Personal Care**: Predictable demand, longer shelf life
2. **Food & Beverage**: Seasonal patterns, shorter shelf life
3. **Household Items**: Steady demand, bulk ordering
4. **Electronics**: Variable demand, long shelf life

Each category has specific parameters for demand volatility, seasonality, and lead times.

## API Reference

### Core Classes

#### StockGRIPSystem
Main system orchestrator:
```python
from src.optimization.coordinator import StockGRIPSystem

system = StockGRIPSystem()
system.initialize_system()
system.start(continuous=True)
```

#### GPEIMSOptimizer
Strategic optimization:
```python
from src.optimization.gp_eims import GPEIMSOptimizer

optimizer = GPEIMSOptimizer(session)
result = optimizer.optimize_product(product_id)
```

#### MPCRLMOBOController
Tactical optimization:
```python
from src.optimization.mpc_rl_mobo import MPCRLMOBOController

controller = MPCRLMOBOController(session)
action = controller.make_replenishment_decision(product_id)
```

#### InventorySimulationEnvironment
Testing and validation:
```python
from src.simulation.environment import InventorySimulationEnvironment

env = InventorySimulationEnvironment(products, simulation_days=365)
results = env.run_simulation(strategy_function)
```

### Database Models

Key database tables:
- **Products**: Product information and constraints
- **Inventory**: Current and historical stock levels
- **Demand**: Historical and forecasted demand
- **OptimizationParameters**: Strategic parameters from GP-EIMS
- **InventoryActions**: Tactical decisions from MPC-RL-MOBO
- **PerformanceMetrics**: System performance tracking

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Problem**: Module import failures
**Solution**: 
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python path includes `src` directory
- Verify file structure matches documentation

#### 2. Database Connection Issues
**Problem**: SQLite database errors
**Solution**:
- Check `data/` directory exists and is writable
- Verify database URL in `config/settings.py`
- Try deleting database file to recreate

#### 3. Optimization Failures
**Problem**: GP-EIMS or MPC-RL-MOBO errors
**Solution**:
- Check sufficient historical data exists (>30 days)
- Verify product parameters are valid
- Review constraint settings in configuration

#### 4. Performance Issues
**Problem**: Slow optimization or dashboard
**Solution**:
- Reduce number of products for testing
- Decrease optimization iterations
- Check system resources (memory, CPU)

#### 5. Data Quality Issues
**Problem**: Validation errors or inconsistent data
**Solution**:
- Run data quality check in dashboard
- Regenerate sample data if needed
- Check for negative values or missing data

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing

Run comprehensive tests:
```bash
python test_stock_grip.py
```

This will validate all components and identify issues.

### Support

For additional support:
1. Check the test results for specific error messages
2. Review log files for detailed error information
3. Verify configuration matches your environment
4. Test with smaller datasets first

## Performance Optimization

### For Large Datasets

1. **Database Optimization**:
   - Consider PostgreSQL for production
   - Add database indexes for frequently queried fields
   - Implement data archiving for old records

2. **Optimization Tuning**:
   - Reduce GP-EIMS iterations for faster convergence
   - Adjust MPC prediction horizon based on needs
   - Use parallel processing for multiple products

3. **Memory Management**:
   - Implement data pagination for large product catalogs
   - Use database sessions efficiently
   - Clear caches periodically

### Monitoring Performance

Key metrics to monitor:
- Optimization convergence time
- Dashboard response time
- Database query performance
- Memory usage patterns

The system includes built-in performance monitoring through the metrics module.