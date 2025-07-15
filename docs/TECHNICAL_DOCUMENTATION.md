# Stock_GRIP Technical Documentation

## Architecture Deep Dive

### System Components

#### 1. Data Layer (`src/data/`)

**Models (`models.py`)**
- SQLAlchemy ORM models for all database entities
- Relationships between products, inventory, demand, and optimization results
- JSON field support for complex parameter storage

**Data Generator (`data_generator.py`)**
- Synthetic FMCG data generation with realistic patterns
- Configurable demand volatility and seasonality
- Multi-category product support with category-specific characteristics

**Pipeline (`pipeline.py`)**
- Data validation and quality checks
- Feature engineering for optimization algorithms
- Performance aggregation and reporting
- ETL processes for data transformation

#### 2. Optimization Layer (`src/optimization/`)

**GP-EIMS Engine (`gp_eims.py`)**
```python
class GPEIMSOptimizer:
    def __init__(self, database_session):
        # Initialize Gaussian Process with RBF kernel
        kernel = C(1.0, (1e-3, 1e3)) * RBF(1.0, (1e-2, 1e2))
        self.gp = GaussianProcessRegressor(kernel=kernel, alpha=noise_variance)
    
    def _expected_improvement(self, X, gp, y_best, xi=0.01):
        # Calculate Expected Improvement acquisition function
        mu, sigma = gp.predict(X, return_std=True)
        imp = mu - y_best - xi
        Z = imp / sigma
        ei = imp * normal_cdf(Z) + sigma * normal_pdf(Z)
        return ei
```

**MPC-RL-MOBO Controller (`mpc_rl_mobo.py`)**
```python
class MPCController:
    def solve_mpc(self, state, product, strategic_params):
        # Decision variables
        order_quantities = cp.Variable(self.control_horizon, integer=True)
        inventory_levels = cp.Variable(self.prediction_horizon + 1)
        
        # Multi-objective optimization
        holding_costs = cp.sum(cp.multiply(inventory_levels[1:], holding_cost))
        stockout_costs = cp.sum(cp.multiply(stockouts, stockout_penalty))
        ordering_costs = cp.sum(cp.multiply(order_quantities > 0, order_cost))
        
        objective = cp.Minimize(holding_costs + stockout_costs + ordering_costs)
```

**Coordination Logic (`coordinator.py`)**
- Orchestrates strategic and tactical optimization
- Manages optimization scheduling and parameter handoff
- Validates consistency between optimization approaches
- Adaptive parameter tuning based on performance

#### 3. Simulation Layer (`src/simulation/`)

**Environment (`environment.py`)**
- Discrete-event simulation of inventory systems
- Realistic demand generation with seasonality and trends
- Strategy testing and comparison framework
- Performance evaluation metrics

#### 4. Utilities (`src/utils/`)

**Metrics (`metrics.py`)**
- KPI calculation and tracking
- Performance dashboard generation
- Alert system for threshold violations
- Trend analysis and comparative reporting

### Algorithm Details

#### GP-EIMS (Gaussian Process Expected Improvement Method)

**Objective Function**:
```
f(θ) = C_holding + C_stockout + C_ordering + P_service
```

Where:
- `θ = [reorder_point, safety_stock, order_quantity]`
- `C_holding`: Holding cost based on average inventory
- `C_stockout`: Penalty for stockouts
- `C_ordering`: Fixed and variable ordering costs
- `P_service`: Service level penalty

**Acquisition Function**:
```
EI(θ) = (μ(θ) - f_best - ξ) * Φ(Z) + σ(θ) * φ(Z)
```

Where:
- `μ(θ), σ(θ)`: GP posterior mean and standard deviation
- `Φ, φ`: Standard normal CDF and PDF
- `Z = (μ(θ) - f_best - ξ) / σ(θ)`

#### MPC-RL-MOBO

**State Vector**:
```
s_t = [stock_level, in_transit, avg_demand, demand_volatility, 
       days_supply, stockout_risk, lead_time, time_progress]
```

**Action Space**:
```
a_t = [order_multiplier] ∈ [0, 0.5, 1.0, 1.5, 2.0]
```

**Reward Function**:
```
r_t = service_reward - holding_cost - stockout_penalty - order_cost - efficiency_penalty
```

**Q-Learning Update**:
```
Q(s_t, a_t) ← Q(s_t, a_t) + α[r_t + γ max_a Q(s_{t+1}, a) - Q(s_t, a_t)]
```

### Database Schema

```sql
-- Core product information
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_cost REAL NOT NULL,
    selling_price REAL NOT NULL,
    lead_time_days INTEGER NOT NULL,
    shelf_life_days INTEGER NOT NULL,
    min_order_quantity INTEGER DEFAULT 1,
    max_order_quantity INTEGER DEFAULT 10000
);

-- Inventory tracking
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    stock_level INTEGER NOT NULL,
    reserved_stock INTEGER DEFAULT 0,
    in_transit INTEGER DEFAULT 0,
    available_stock INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Demand history and forecasts
CREATE TABLE demand (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    date DATETIME NOT NULL,
    quantity_demanded INTEGER NOT NULL,
    quantity_fulfilled INTEGER NOT NULL,
    is_forecast BOOLEAN DEFAULT FALSE,
    confidence_interval REAL DEFAULT 0.95,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Strategic optimization parameters
CREATE TABLE optimization_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    reorder_point INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL,
    order_quantity INTEGER NOT NULL,
    review_period_days INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    gp_mean REAL,
    gp_variance REAL,
    acquisition_value REAL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Tactical inventory actions
CREATE TABLE inventory_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    expected_delivery DATETIME,
    cost REAL,
    state_vector TEXT,  -- JSON
    q_value REAL,
    reward REAL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
```

### Performance Considerations

#### Scalability

**Database Optimization**:
- Indexes on frequently queried columns
- Partitioning for large historical data
- Connection pooling for concurrent access

**Algorithm Optimization**:
- Parallel processing for multiple products
- Incremental learning for RL agents
- Efficient matrix operations with NumPy

**Memory Management**:
- Lazy loading of historical data
- Periodic cleanup of old records
- Efficient data structures

#### Computational Complexity

**GP-EIMS**:
- Time complexity: O(n³) for GP training, O(n) for prediction
- Space complexity: O(n²) for covariance matrix
- Optimization: O(k × d) where k=iterations, d=dimensions

**MPC-RL-MOBO**:
- MPC solving: O(h³) where h=horizon length
- RL updates: O(1) for online learning
- Memory: O(m) where m=replay buffer size

### Configuration Management

#### Environment Variables
```bash
# Database configuration
DATABASE_URL=sqlite:///data/stock_grip.db

# Optimization parameters
GP_EIMS_MAX_ITERATIONS=50
MPC_PREDICTION_HORIZON=7
RL_LEARNING_RATE=0.001

# Simulation settings
SERVICE_LEVEL_TARGET=0.95
HOLDING_COST_RATE=0.25
```

#### Configuration Validation
```python
def validate_config():
    assert GP_EIMS_CONFIG["max_iterations"] > 0
    assert 0 < SIMULATION_CONFIG["service_level_target"] <= 1
    assert MPC_RL_CONFIG["prediction_horizon"] >= 1
```

### Testing Strategy

#### Unit Tests
- Individual component testing
- Mock database interactions
- Algorithm correctness validation

#### Integration Tests
- End-to-end workflow testing
- Database consistency checks
- API endpoint validation

#### Performance Tests
- Load testing with large datasets
- Optimization convergence analysis
- Memory usage profiling

#### Simulation Tests
- Strategy comparison validation
- Statistical significance testing
- Robustness analysis

### Deployment Considerations

#### Production Setup
```yaml
# docker-compose.yml
version: '3.8'
services:
  stock-grip:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/stock_grip
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: stock_grip
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

#### Monitoring
- Application performance monitoring (APM)
- Database query performance
- Optimization convergence tracking
- Alert thresholds and notifications

#### Security
- Database connection encryption
- Input validation and sanitization
- Access control and authentication
- Audit logging

### Extension Points

#### Custom Optimization Algorithms
```python
class CustomOptimizer(BaseOptimizer):
    def optimize_product(self, product_id):
        # Implement custom optimization logic
        pass
```

#### Additional Data Sources
```python
class ExternalDataConnector:
    def fetch_demand_data(self, product_id, date_range):
        # Connect to external systems
        pass
```

#### Custom Metrics
```python
class CustomMetricCalculator(PerformanceCalculator):
    def calculate_custom_metrics(self, days):
        # Implement domain-specific metrics
        pass
```

### Research and Development

#### Future Enhancements
1. **Deep Reinforcement Learning**: Replace linear Q-learning with neural networks
2. **Multi-Agent Systems**: Coordinate optimization across supply chain tiers
3. **Uncertainty Quantification**: Bayesian neural networks for demand forecasting
4. **Real-time Adaptation**: Online learning with concept drift detection

#### Experimental Features
- Federated learning across multiple retailers
- Graph neural networks for supply chain modeling
- Causal inference for demand driver analysis
- Quantum optimization algorithms

### Troubleshooting Guide

#### Common Issues

**Optimization Convergence**:
- Check parameter bounds and constraints
- Verify sufficient historical data
- Adjust acquisition function parameters

**Performance Degradation**:
- Monitor database query performance
- Check memory usage patterns
- Profile optimization algorithms

**Data Quality Issues**:
- Validate input data consistency
- Check for missing or anomalous values
- Verify temporal data alignment

#### Debug Tools
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Profile optimization performance
import cProfile
cProfile.run('optimizer.optimize_product(product_id)')

# Memory usage analysis
import tracemalloc
tracemalloc.start()
# ... run code ...
current, peak = tracemalloc.get_traced_memory()
```

### Contributing Guidelines

#### Code Standards
- PEP 8 compliance
- Type hints for all functions
- Comprehensive docstrings
- Unit test coverage >90%

#### Development Workflow
1. Fork repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request
5. Code review and merge

#### Documentation Requirements
- API documentation with examples
- Algorithm explanations
- Configuration guides
- Performance benchmarks