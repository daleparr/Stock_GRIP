"""
MPC-RL-MOBO (Model Predictive Control + Reinforcement Learning + Multi-Objective Bayesian Optimization)
for real-time inventory replenishment decisions
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import uuid
import json
from collections import deque
import random

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    cp = None
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from ..data.models import (
    Product, Inventory, Demand, InventoryActions, OptimizationParameters,
    OptimizationResults, PerformanceMetrics, get_session
)
from config.settings import MPC_RL_CONFIG, SIMULATION_CONFIG


class InventoryState:
    """Represents the current state of inventory system"""
    
    def __init__(self, product_id: str, current_stock: int, reserved_stock: int,
                 in_transit: int, recent_demand: List[int], lead_time: int):
        self.product_id = product_id
        self.current_stock = current_stock
        self.reserved_stock = reserved_stock
        self.in_transit = in_transit
        self.available_stock = current_stock - reserved_stock
        self.recent_demand = recent_demand[-7:]  # Last 7 days
        self.lead_time = lead_time
        
        # Derived features
        self.avg_demand = np.mean(recent_demand) if recent_demand else 0
        self.demand_volatility = np.std(recent_demand) if len(recent_demand) > 1 else 0
        self.stock_coverage = self.available_stock / max(self.avg_demand, 1)  # Days of coverage
        self.stockout_risk = max(0, (self.avg_demand * lead_time - self.available_stock) / max(self.avg_demand, 1))
    
    def to_vector(self) -> np.ndarray:
        """Convert state to feature vector for ML models"""
        return np.array([
            self.current_stock,
            self.reserved_stock,
            self.in_transit,
            self.available_stock,
            self.avg_demand,
            self.demand_volatility,
            self.stock_coverage,
            self.stockout_risk,
            self.lead_time,
            len(self.recent_demand)
        ])


class MPCController:
    """Model Predictive Control for inventory optimization"""
    
    def __init__(self, prediction_horizon: int = 7, control_horizon: int = 3):
        self.prediction_horizon = prediction_horizon
        self.control_horizon = control_horizon
        self.warehouse_capacity = SIMULATION_CONFIG["warehouse_capacity"]
        self.service_level_target = SIMULATION_CONFIG["service_level_target"]
    
    def predict_demand(self, historical_demand: List[int], horizon: int) -> np.ndarray:
        """Simple demand forecasting using moving average with trend"""
        if len(historical_demand) < 3:
            return np.full(horizon, max(1, np.mean(historical_demand) if historical_demand else 10))
        
        # Calculate trend
        recent_demand = np.array(historical_demand[-14:])  # Last 2 weeks
        if len(recent_demand) > 7:
            trend = np.mean(recent_demand[-7:]) - np.mean(recent_demand[-14:-7])
        else:
            trend = 0
        
        # Base forecast
        base_forecast = np.mean(historical_demand[-7:])  # Last week average
        
        # Apply trend and add some seasonality
        forecasts = []
        for i in range(horizon):
            # Simple weekly seasonality (higher on weekends)
            day_of_week = (datetime.now() + timedelta(days=i)).weekday()
            seasonal_factor = 1.2 if day_of_week >= 5 else 0.9
            
            forecast = base_forecast + trend * i * seasonal_factor
            forecasts.append(max(0, forecast))
        
        return np.array(forecasts)
    
    def solve_mpc(self, state: InventoryState, product: Product,
                  strategic_params: OptimizationParameters) -> Dict[str, Any]:
        """
        Solve MPC optimization problem
        Returns: Dictionary with optimal actions and predictions
        """
        # Check if cvxpy is available
        if not CVXPY_AVAILABLE:
            return self._solve_mpc_fallback(state, product, strategic_params)
        
        # Predict demand
        demand_forecast = self.predict_demand(state.recent_demand, self.prediction_horizon)
        
        # Decision variables
        order_quantities = cp.Variable(self.control_horizon, integer=True)
        inventory_levels = cp.Variable(self.prediction_horizon + 1)
        stockouts = cp.Variable(self.prediction_horizon, nonneg=True)
        
        # Parameters
        holding_cost = product.unit_cost * SIMULATION_CONFIG["holding_cost_rate"] / 365
        stockout_penalty = SIMULATION_CONFIG["stockout_penalty"]
        order_cost = SIMULATION_CONFIG["order_cost"]
        
        # Constraints
        constraints = []
        
        # Initial inventory
        constraints.append(inventory_levels[0] == state.available_stock)
        
        # Inventory dynamics
        for t in range(self.prediction_horizon):
            if t < self.control_horizon:
                # Orders arrive after lead time
                order_arrival = order_quantities[t] if t >= product.lead_time_days else 0
                constraints.append(
                    inventory_levels[t + 1] == 
                    inventory_levels[t] + order_arrival - demand_forecast[t] + stockouts[t]
                )
            else:
                # No new orders in prediction horizon beyond control horizon
                constraints.append(
                    inventory_levels[t + 1] == 
                    inventory_levels[t] - demand_forecast[t] + stockouts[t]
                )
            
            # Non-negativity of inventory
            constraints.append(inventory_levels[t + 1] >= 0)
            
            # Stockout calculation
            constraints.append(stockouts[t] >= demand_forecast[t] - inventory_levels[t])
        
        # Order constraints
        for t in range(self.control_horizon):
            constraints.append(order_quantities[t] >= 0)
            constraints.append(order_quantities[t] <= product.max_order_quantity)
            
            # Minimum order quantity constraint (if ordering)
            # This is a logical constraint that's hard to express in CVXPY
            # We'll handle it in post-processing
        
        # Capacity constraints
        for t in range(self.prediction_horizon):
            constraints.append(inventory_levels[t] <= self.warehouse_capacity)
        
        # Service level constraint (soft)
        total_demand = cp.sum(demand_forecast)
        total_stockouts = cp.sum(stockouts)
        service_level = 1 - total_stockouts / cp.maximum(total_demand, 1)
        
        # Objective function (multi-objective)
        holding_costs = cp.sum(cp.multiply(inventory_levels[1:], holding_cost))
        stockout_costs = cp.sum(cp.multiply(stockouts, stockout_penalty))
        ordering_costs = cp.sum(cp.multiply(order_quantities > 0, order_cost))
        
        # Service level penalty
        service_penalty = cp.maximum(0, self.service_level_target - service_level) * 10000
        
        objective = cp.Minimize(holding_costs + stockout_costs + ordering_costs + service_penalty)
        
        # Solve problem
        problem = cp.Problem(objective, constraints)
        
        try:
            problem.solve(solver=cp.ECOS_BB, verbose=False)
            
            if problem.status == cp.OPTIMAL:
                optimal_orders = order_quantities.value
                optimal_inventory = inventory_levels.value
                optimal_stockouts = stockouts.value
                
                # Handle minimum order quantity constraint
                for t in range(self.control_horizon):
                    if optimal_orders[t] > 0 and optimal_orders[t] < product.min_order_quantity:
                        optimal_orders[t] = product.min_order_quantity
                
                return {
                    "status": "optimal",
                    "order_quantities": optimal_orders,
                    "predicted_inventory": optimal_inventory,
                    "predicted_stockouts": optimal_stockouts,
                    "demand_forecast": demand_forecast,
                    "total_cost": problem.value,
                    "service_level": float(1 - np.sum(optimal_stockouts) / max(np.sum(demand_forecast), 1))
                }
            else:
                return {"status": "infeasible", "message": f"Problem status: {problem.status}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _solve_mpc_fallback(self, state: InventoryState, product: Product,
                           strategic_params: OptimizationParameters) -> Dict[str, Any]:
        """
        Fallback heuristic-based solution when cvxpy is not available
        Uses simple reorder point logic with safety stock calculations
        """
        # Predict demand using simple method
        demand_forecast = self.predict_demand(state.recent_demand, self.prediction_horizon)
        
        # Calculate reorder point and safety stock
        avg_demand = np.mean(state.recent_demand) if state.recent_demand else 1
        demand_std = np.std(state.recent_demand) if len(state.recent_demand) > 1 else avg_demand * 0.3
        
        # Safety stock for target service level (using normal distribution approximation)
        try:
            from scipy.stats import norm
            z_score = norm.ppf(self.service_level_target)
        except ImportError:
            # Fallback z-scores for common service levels
            if self.service_level_target >= 0.99:
                z_score = 2.33
            elif self.service_level_target >= 0.975:
                z_score = 1.96
            elif self.service_level_target >= 0.95:
                z_score = 1.645
            else:
                z_score = 1.28  # 90% service level
        
        safety_stock = z_score * demand_std * np.sqrt(product.lead_time_days)
        reorder_point = avg_demand * product.lead_time_days + safety_stock
        
        # Simple order logic
        order_quantities = np.zeros(self.control_horizon)
        current_inventory = state.available_stock
        
        for t in range(self.control_horizon):
            # Check if we need to order
            projected_inventory = current_inventory - demand_forecast[t]
            
            if projected_inventory <= reorder_point:
                # Order enough to reach target stock level
                target_stock = reorder_point + avg_demand * 7  # One week buffer
                order_qty = max(0, target_stock - projected_inventory)
                
                # Apply min/max order constraints
                if order_qty > 0:
                    order_qty = max(product.min_order_quantity, order_qty)
                    order_qty = min(product.max_order_quantity, order_qty)
                
                order_quantities[t] = order_qty
                current_inventory += order_qty
            
            current_inventory = max(0, current_inventory - demand_forecast[t])
        
        # Calculate predicted inventory levels and stockouts
        inventory_levels = np.zeros(self.prediction_horizon + 1)
        stockouts = np.zeros(self.prediction_horizon)
        inventory_levels[0] = state.available_stock
        
        for t in range(self.prediction_horizon):
            order_arrival = order_quantities[t] if t < self.control_horizon and t >= product.lead_time_days else 0
            inventory_levels[t + 1] = inventory_levels[t] + order_arrival - demand_forecast[t]
            
            if inventory_levels[t + 1] < 0:
                stockouts[t] = -inventory_levels[t + 1]
                inventory_levels[t + 1] = 0
        
        # Calculate costs (simplified)
        holding_cost = product.unit_cost * SIMULATION_CONFIG["holding_cost_rate"] / 365
        stockout_penalty = SIMULATION_CONFIG["stockout_penalty"]
        order_cost = SIMULATION_CONFIG["order_cost"]
        
        total_cost = (np.sum(inventory_levels[1:]) * holding_cost +
                     np.sum(stockouts) * stockout_penalty +
                     np.sum(order_quantities > 0) * order_cost)
        
        service_level = 1 - np.sum(stockouts) / max(np.sum(demand_forecast), 1)
        
        return {
            "status": "heuristic_fallback",
            "order_quantities": order_quantities,
            "predicted_inventory": inventory_levels,
            "predicted_stockouts": stockouts,
            "demand_forecast": demand_forecast,
            "total_cost": total_cost,
            "service_level": float(service_level),
            "message": "Using heuristic fallback (cvxpy not available)"
        }


class RLAgent:
    """Reinforcement Learning agent for adaptive inventory decisions"""
    
    def __init__(self, state_dim: int = 10, action_dim: int = 1):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.config = MPC_RL_CONFIG
        
        # Experience replay buffer
        self.memory = deque(maxlen=self.config["memory_size"])
        
        # Simple Q-learning with function approximation
        self.q_weights = np.random.normal(0, 0.1, (state_dim, action_dim))
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # Learning parameters
        self.epsilon = self.config["exploration_rate"]
        self.learning_rate = self.config["learning_rate"]
        self.discount_factor = self.config["discount_factor"]
        
        # Action discretization (order quantity multipliers)
        self.action_space = np.array([0, 0.5, 1.0, 1.5, 2.0])  # Multipliers for base order quantity
    
    def get_q_value(self, state: np.ndarray, action_idx: int) -> float:
        """Get Q-value for state-action pair"""
        if not self.is_fitted:
            return 0.0
        
        state_normalized = self.scaler.transform(state.reshape(1, -1))[0]
        return np.dot(state_normalized, self.q_weights[:, 0])  # Simplified linear Q-function
    
    def select_action(self, state: np.ndarray, base_order_quantity: int, 
                     exploration: bool = True) -> Tuple[int, int]:
        """
        Select action using epsilon-greedy policy
        Returns: (action_index, actual_order_quantity)
        """
        if exploration and np.random.random() < self.epsilon:
            # Random exploration
            action_idx = np.random.randint(len(self.action_space))
        else:
            # Greedy action selection
            q_values = [self.get_q_value(state, i) for i in range(len(self.action_space))]
            action_idx = np.argmax(q_values)
        
        # Convert to actual order quantity
        multiplier = self.action_space[action_idx]
        actual_quantity = int(base_order_quantity * multiplier)
        
        return action_idx, actual_quantity
    
    def store_experience(self, state: np.ndarray, action_idx: int, reward: float, 
                        next_state: np.ndarray, done: bool):
        """Store experience in replay buffer"""
        self.memory.append((state, action_idx, reward, next_state, done))
    
    def calculate_reward(self, state_before: InventoryState, action_quantity: int,
                        state_after: InventoryState, product: Product) -> float:
        """Calculate reward for the action taken"""
        # Cost components
        holding_cost = state_after.current_stock * product.unit_cost * 0.001  # Daily holding cost
        
        # Stockout penalty
        stockout_penalty = 0
        if state_after.available_stock <= 0:
            stockout_penalty = SIMULATION_CONFIG["stockout_penalty"] * abs(state_after.available_stock)
        
        # Order cost
        order_cost = SIMULATION_CONFIG["order_cost"] if action_quantity > 0 else 0
        
        # Service level reward
        service_reward = 100 if state_after.available_stock > 0 else -100
        
        # Efficiency reward (penalize excessive inventory)
        efficiency_penalty = max(0, (state_after.stock_coverage - 30) * 10)  # Penalty for >30 days coverage
        
        total_reward = service_reward - holding_cost - stockout_penalty - order_cost - efficiency_penalty
        
        return total_reward
    
    def update_q_function(self, batch_size: int = None):
        """Update Q-function using experience replay"""
        if len(self.memory) < 100:  # Wait for sufficient experience
            return
        
        if batch_size is None:
            batch_size = min(self.config["batch_size"], len(self.memory))
        
        # Sample batch from memory
        batch = random.sample(self.memory, batch_size)
        
        states = np.array([exp[0] for exp in batch])
        actions = np.array([exp[1] for exp in batch])
        rewards = np.array([exp[2] for exp in batch])
        next_states = np.array([exp[3] for exp in batch])
        dones = np.array([exp[4] for exp in batch])
        
        # Fit scaler if not already fitted
        if not self.is_fitted:
            all_states = np.vstack([states, next_states])
            self.scaler.fit(all_states)
            self.is_fitted = True
        
        # Normalize states
        states_norm = self.scaler.transform(states)
        next_states_norm = self.scaler.transform(next_states)
        
        # Calculate targets
        targets = rewards.copy()
        for i in range(len(batch)):
            if not dones[i]:
                # Q-learning update
                next_q_values = [self.get_q_value(next_states[i], a) for a in range(len(self.action_space))]
                targets[i] += self.discount_factor * max(next_q_values)
        
        # Update weights using gradient descent
        for i in range(len(batch)):
            current_q = np.dot(states_norm[i], self.q_weights[:, 0])
            error = targets[i] - current_q
            
            # Gradient update
            self.q_weights[:, 0] += self.learning_rate * error * states_norm[i]
        
        # Decay exploration rate
        self.epsilon = max(0.01, self.epsilon * 0.995)


class MPCRLMOBOController:
    """Main controller combining MPC, RL, and Multi-Objective Bayesian Optimization"""
    
    def __init__(self, database_session: Session):
        self.session = database_session
        self.mpc_controller = MPCController(
            MPC_RL_CONFIG["prediction_horizon"],
            MPC_RL_CONFIG["control_horizon"]
        )
        self.rl_agents = {}  # One agent per product
        
    def get_or_create_agent(self, product_id: str) -> RLAgent:
        """Get or create RL agent for a product"""
        if product_id not in self.rl_agents:
            self.rl_agents[product_id] = RLAgent()
        return self.rl_agents[product_id]
    
    def get_current_state(self, product_id: str) -> Optional[InventoryState]:
        """Get current inventory state for a product"""
        # Get current inventory
        current_inventory = self.session.query(Inventory).filter(
            Inventory.product_id == product_id
        ).order_by(Inventory.timestamp.desc()).first()
        
        if not current_inventory:
            return None
        
        # Get recent demand
        recent_demand = self.session.query(Demand).filter(
            Demand.product_id == product_id,
            Demand.is_forecast == False,
            Demand.date >= datetime.utcnow() - timedelta(days=14)
        ).order_by(Demand.date.desc()).all()
        
        demand_values = [d.quantity_demanded for d in recent_demand]
        
        # Get product info
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        
        return InventoryState(
            product_id=product_id,
            current_stock=current_inventory.stock_level,
            reserved_stock=current_inventory.reserved_stock,
            in_transit=current_inventory.in_transit,
            recent_demand=demand_values,
            lead_time=product.lead_time_days if product else 7
        )
    
    def make_replenishment_decision(self, product_id: str) -> Optional[InventoryActions]:
        """
        Make real-time replenishment decision for a product
        """
        # Get current state
        state = self.get_current_state(product_id)
        if not state:
            return None
        
        # Get product and strategic parameters
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        strategic_params = self.session.query(OptimizationParameters).filter(
            OptimizationParameters.product_id == product_id,
            OptimizationParameters.is_active == True
        ).first()
        
        if not product or not strategic_params:
            return None
        
        # Solve MPC problem
        mpc_result = self.mpc_controller.solve_mpc(state, product, strategic_params)
        
        if mpc_result["status"] != "optimal":
            print(f"MPC failed for {product_id}: {mpc_result.get('message', 'Unknown error')}")
            return None
        
        # Get base order quantity from MPC
        base_order_quantity = int(mpc_result["order_quantities"][0])
        
        # Use RL agent to adjust the decision
        agent = self.get_or_create_agent(product_id)
        state_vector = state.to_vector()
        
        action_idx, final_order_quantity = agent.select_action(
            state_vector, base_order_quantity, exploration=True
        )
        
        # Calculate Q-value for logging
        q_value = agent.get_q_value(state_vector, action_idx)
        
        # Create inventory action
        if final_order_quantity > 0:
            action = InventoryActions(
                product_id=product_id,
                timestamp=datetime.utcnow(),
                action_type="order",
                quantity=final_order_quantity,
                expected_delivery=datetime.utcnow() + timedelta(days=product.lead_time_days),
                cost=final_order_quantity * product.unit_cost + SIMULATION_CONFIG["order_cost"],
                q_value=float(q_value),
                reward=0.0  # Will be updated later
            )
            
            # Store state information
            action.set_state_vector({
                "mpc_recommendation": base_order_quantity,
                "rl_action_index": action_idx,
                "state_features": state_vector.tolist(),
                "demand_forecast": mpc_result["demand_forecast"].tolist(),
                "predicted_service_level": mpc_result["service_level"]
            })
            
            self.session.add(action)
            self.session.commit()
            
            return action
        
        return None
    
    def update_agent_learning(self, product_id: str):
        """Update RL agent based on recent experiences"""
        agent = self.get_or_create_agent(product_id)
        
        # Get recent actions and calculate rewards
        recent_actions = self.session.query(InventoryActions).filter(
            InventoryActions.product_id == product_id,
            InventoryActions.timestamp >= datetime.utcnow() - timedelta(days=7)
        ).order_by(InventoryActions.timestamp.desc()).limit(10).all()
        
        if len(recent_actions) < 2:
            return
        
        # Calculate rewards for recent actions
        for i in range(len(recent_actions) - 1):
            current_action = recent_actions[i]
            next_action = recent_actions[i + 1]
            
            # Get states before and after action
            state_info = current_action.get_state_vector()
            if not state_info:
                continue
            
            state_before = np.array(state_info["state_features"])
            
            # Get state after action (simplified)
            next_state_info = next_action.get_state_vector()
            if next_state_info:
                state_after = np.array(next_state_info["state_features"])
            else:
                continue
            
            # Calculate reward (simplified)
            product = self.session.query(Product).filter(Product.product_id == product_id).first()
            
            # Simple reward based on service level and cost
            predicted_service = state_info.get("predicted_service_level", 0.95)
            service_reward = 100 * predicted_service
            cost_penalty = current_action.cost * 0.01
            
            reward = service_reward - cost_penalty
            
            # Store experience
            agent.store_experience(
                state_before,
                state_info["rl_action_index"],
                reward,
                state_after,
                done=False
            )
            
            # Update action reward in database
            current_action.reward = reward
        
        # Update Q-function
        agent.update_q_function()
        self.session.commit()
    
    def run_optimization_cycle(self) -> Dict[str, Any]:
        """
        Run one cycle of MPC-RL-MOBO optimization for all products
        """
        products = self.session.query(Product).all()
        results = {
            "timestamp": datetime.utcnow(),
            "products_processed": 0,
            "actions_taken": 0,
            "total_cost": 0.0,
            "average_service_level": 0.0
        }
        
        service_levels = []
        
        for product in products:
            try:
                # Make replenishment decision
                action = self.make_replenishment_decision(product.product_id)
                
                if action:
                    results["actions_taken"] += 1
                    results["total_cost"] += action.cost
                    
                    # Get predicted service level
                    state_info = action.get_state_vector()
                    if state_info and "predicted_service_level" in state_info:
                        service_levels.append(state_info["predicted_service_level"])
                
                # Update agent learning
                self.update_agent_learning(product.product_id)
                
                results["products_processed"] += 1
                
            except Exception as e:
                print(f"Error processing {product.product_id}: {str(e)}")
                continue
        
        if service_levels:
            results["average_service_level"] = np.mean(service_levels)
        
        # Save performance metrics
        metrics = [
            PerformanceMetrics(
                metric_name="products_processed",
                metric_value=results["products_processed"],
                metric_category="efficiency"
            ),
            PerformanceMetrics(
                metric_name="actions_taken",
                metric_value=results["actions_taken"],
                metric_category="efficiency"
            ),
            PerformanceMetrics(
                metric_name="total_cost",
                metric_value=results["total_cost"],
                metric_category="cost"
            ),
            PerformanceMetrics(
                metric_name="average_service_level",
                metric_value=results["average_service_level"],
                metric_category="service"
            )
        ]
        
        for metric in metrics:
            self.session.add(metric)
        
        self.session.commit()
        
        return results


def main():
    """Test MPC-RL-MOBO controller"""
    from config.settings import DATABASE_URL
    from ..data.models import create_database
    
    engine = create_database(DATABASE_URL)
    session = get_session(engine)
    
    controller = MPCRLMOBOController(session)
    
    # Run one optimization cycle
    results = controller.run_optimization_cycle()
    print(f"Optimization results: {results}")
    
    session.close()


if __name__ == "__main__":
    main()