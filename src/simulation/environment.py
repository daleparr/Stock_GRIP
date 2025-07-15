"""
Simulation environment for testing and validating inventory optimization strategies
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import random
import uuid
from dataclasses import dataclass
from enum import Enum

from ..data.models import Product, Demand, Inventory, InventoryActions
from config.settings import SIMULATION_CONFIG, PRODUCT_CATEGORIES


class ActionType(Enum):
    """Types of inventory actions"""
    ORDER = "order"
    TRANSFER = "transfer"
    ADJUST = "adjust"
    NO_ACTION = "no_action"


@dataclass
class SimulationState:
    """Current state of the simulation"""
    current_day: int
    total_cost: float
    total_demand: int
    total_fulfilled: int
    stockout_events: int
    total_orders: int
    service_level: float
    inventory_levels: Dict[str, int]
    in_transit_orders: List[Dict]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_day": self.current_day,
            "total_cost": self.total_cost,
            "total_demand": self.total_demand,
            "total_fulfilled": self.total_fulfilled,
            "stockout_events": self.stockout_events,
            "total_orders": self.total_orders,
            "service_level": self.service_level,
            "inventory_levels": self.inventory_levels.copy(),
            "orders_in_transit": len(self.in_transit_orders)
        }


class InventorySimulationEnvironment:
    """
    Comprehensive simulation environment for testing inventory optimization strategies
    """
    
    def __init__(self, products: List[Product], simulation_days: int = 365):
        self.products = {p.product_id: p for p in products}
        self.simulation_days = simulation_days
        self.reset()
        
        # Simulation parameters
        self.holding_cost_rate = SIMULATION_CONFIG["holding_cost_rate"] / 365  # Daily rate
        self.stockout_penalty = SIMULATION_CONFIG["stockout_penalty"]
        self.order_cost = SIMULATION_CONFIG["order_cost"]
        self.warehouse_capacity = SIMULATION_CONFIG["warehouse_capacity"]
        
        # Demand generation parameters
        self.demand_volatility = 0.2
        self.seasonal_amplitude = 0.3
        
    def reset(self) -> SimulationState:
        """Reset simulation to initial state"""
        self.current_day = 0
        self.total_cost = 0.0
        self.total_demand = 0
        self.total_fulfilled = 0
        self.stockout_events = 0
        self.total_orders = 0
        
        # Initialize inventory levels
        self.inventory_levels = {}
        for product_id in self.products:
            # Start with 30-60 days of average demand
            base_demand = self._get_base_demand(product_id)
            initial_stock = int(base_demand * np.random.uniform(30, 60))
            self.inventory_levels[product_id] = initial_stock
        
        # Track orders in transit
        self.in_transit_orders = []
        
        # History tracking
        self.demand_history = {pid: [] for pid in self.products}
        self.action_history = []
        self.state_history = []
        
        return self._get_current_state()
    
    def _get_base_demand(self, product_id: str) -> float:
        """Get base daily demand for a product"""
        product = self.products[product_id]
        category_config = PRODUCT_CATEGORIES[product.category]
        
        # Base demand varies by category
        base_demands = {
            "personal_care": 15,
            "food_beverage": 25,
            "household": 10,
            "electronics": 8
        }
        
        return base_demands.get(product.category, 12)
    
    def _generate_daily_demand(self, product_id: str) -> int:
        """Generate realistic daily demand for a product"""
        base_demand = self._get_base_demand(product_id)
        product = self.products[product_id]
        category_config = PRODUCT_CATEGORIES[product.category]
        
        # Seasonal component
        seasonal_factor = 1 + self.seasonal_amplitude * np.sin(2 * np.pi * self.current_day / 365)
        seasonal_factor *= category_config["seasonality_factor"]
        
        # Weekly pattern (higher demand on weekends for some categories)
        day_of_week = self.current_day % 7
        weekly_factor = 1.0
        if product.category in ["food_beverage", "personal_care"]:
            weekly_factor = 1.3 if day_of_week >= 5 else 0.9
        
        # Random variation
        noise_factor = np.random.normal(1, category_config["demand_volatility"])
        
        # Promotional spikes (2% chance of 2-4x demand)
        promo_factor = 1.0
        if np.random.random() < 0.02:
            promo_factor = np.random.uniform(2, 4)
        
        # Calculate final demand
        daily_demand = base_demand * seasonal_factor * weekly_factor * noise_factor * promo_factor
        
        return max(0, int(daily_demand))
    
    def _process_arrivals(self):
        """Process orders arriving today"""
        arriving_orders = []
        remaining_orders = []
        
        for order in self.in_transit_orders:
            if order["arrival_day"] <= self.current_day:
                arriving_orders.append(order)
            else:
                remaining_orders.append(order)
        
        self.in_transit_orders = remaining_orders
        
        # Add arriving inventory
        for order in arriving_orders:
            product_id = order["product_id"]
            quantity = order["quantity"]
            self.inventory_levels[product_id] += quantity
    
    def _fulfill_demand(self) -> Dict[str, Dict[str, int]]:
        """Fulfill daily demand and return fulfillment results"""
        fulfillment_results = {}
        
        for product_id in self.products:
            # Generate demand
            demand = self._generate_daily_demand(product_id)
            self.demand_history[product_id].append(demand)
            self.total_demand += demand
            
            # Fulfill demand
            available_stock = self.inventory_levels[product_id]
            fulfilled = min(demand, available_stock)
            stockout = demand - fulfilled
            
            # Update inventory
            self.inventory_levels[product_id] = max(0, available_stock - fulfilled)
            
            # Track metrics
            self.total_fulfilled += fulfilled
            if stockout > 0:
                self.stockout_events += 1
            
            fulfillment_results[product_id] = {
                "demand": demand,
                "fulfilled": fulfilled,
                "stockout": stockout,
                "remaining_stock": self.inventory_levels[product_id]
            }
        
        return fulfillment_results
    
    def _calculate_daily_costs(self, actions: Dict[str, Dict]) -> float:
        """Calculate daily costs including holding, stockout, and ordering costs"""
        daily_cost = 0.0
        
        # Holding costs
        for product_id, stock_level in self.inventory_levels.items():
            product = self.products[product_id]
            holding_cost = stock_level * product.unit_cost * self.holding_cost_rate
            daily_cost += holding_cost
        
        # Ordering costs
        for product_id, action in actions.items():
            if action["action_type"] == ActionType.ORDER and action["quantity"] > 0:
                daily_cost += self.order_cost
                # Add product cost
                product = self.products[product_id]
                daily_cost += action["quantity"] * product.unit_cost
        
        return daily_cost
    
    def step(self, actions: Dict[str, Dict]) -> Tuple[SimulationState, Dict[str, Any], bool]:
        """
        Execute one simulation step
        
        Args:
            actions: Dictionary of actions per product
                    {product_id: {"action_type": ActionType, "quantity": int}}
        
        Returns:
            (new_state, step_info, done)
        """
        step_info = {
            "day": self.current_day,
            "actions_taken": {},
            "fulfillment_results": {},
            "daily_cost": 0.0,
            "violations": []
        }
        
        # Process arriving orders
        self._process_arrivals()
        
        # Execute actions
        for product_id, action in actions.items():
            if product_id not in self.products:
                continue
            
            action_type = action.get("action_type", ActionType.NO_ACTION)
            quantity = action.get("quantity", 0)
            
            if action_type == ActionType.ORDER and quantity > 0:
                product = self.products[product_id]
                
                # Check constraints
                if quantity < product.min_order_quantity:
                    step_info["violations"].append(f"{product_id}: Order below minimum")
                    continue
                
                if quantity > product.max_order_quantity:
                    step_info["violations"].append(f"{product_id}: Order above maximum")
                    quantity = product.max_order_quantity
                
                # Check warehouse capacity
                total_inventory = sum(self.inventory_levels.values())
                total_in_transit = sum(order["quantity"] for order in self.in_transit_orders)
                
                if total_inventory + total_in_transit + quantity > self.warehouse_capacity:
                    step_info["violations"].append(f"{product_id}: Warehouse capacity exceeded")
                    continue
                
                # Place order
                arrival_day = self.current_day + product.lead_time_days
                self.in_transit_orders.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "order_day": self.current_day,
                    "arrival_day": arrival_day
                })
                
                self.total_orders += 1
                step_info["actions_taken"][product_id] = {
                    "action_type": action_type.value,
                    "quantity": quantity,
                    "arrival_day": arrival_day
                }
        
        # Fulfill demand
        fulfillment_results = self._fulfill_demand()
        step_info["fulfillment_results"] = fulfillment_results
        
        # Calculate costs
        daily_cost = self._calculate_daily_costs(actions)
        self.total_cost += daily_cost
        step_info["daily_cost"] = daily_cost
        
        # Update day
        self.current_day += 1
        
        # Check if simulation is done
        done = self.current_day >= self.simulation_days
        
        # Record state
        current_state = self._get_current_state()
        self.state_history.append(current_state.to_dict())
        self.action_history.append(step_info)
        
        return current_state, step_info, done
    
    def _get_current_state(self) -> SimulationState:
        """Get current simulation state"""
        service_level = 0.0
        if self.total_demand > 0:
            service_level = self.total_fulfilled / self.total_demand
        
        return SimulationState(
            current_day=self.current_day,
            total_cost=self.total_cost,
            total_demand=self.total_demand,
            total_fulfilled=self.total_fulfilled,
            stockout_events=self.stockout_events,
            total_orders=self.total_orders,
            service_level=service_level,
            inventory_levels=self.inventory_levels.copy(),
            in_transit_orders=self.in_transit_orders.copy()
        )
    
    def get_state_vector(self, product_id: str) -> np.ndarray:
        """Get state vector for a specific product (for RL agents)"""
        if product_id not in self.products:
            return np.zeros(10)
        
        product = self.products[product_id]
        recent_demand = self.demand_history[product_id][-7:] if self.demand_history[product_id] else [0]
        
        # Calculate features
        current_stock = self.inventory_levels[product_id]
        avg_demand = np.mean(recent_demand) if recent_demand else 0
        demand_volatility = np.std(recent_demand) if len(recent_demand) > 1 else 0
        
        # In-transit quantity for this product
        in_transit = sum(order["quantity"] for order in self.in_transit_orders 
                        if order["product_id"] == product_id)
        
        # Days of supply
        days_supply = current_stock / max(avg_demand, 1)
        
        # Stockout risk
        stockout_risk = max(0, (avg_demand * product.lead_time_days - current_stock) / max(avg_demand, 1))
        
        return np.array([
            current_stock,
            in_transit,
            avg_demand,
            demand_volatility,
            days_supply,
            stockout_risk,
            product.lead_time_days,
            self.current_day / self.simulation_days,  # Progress through simulation
            len(recent_demand),
            self.service_level if hasattr(self, 'service_level') else 0
        ])
    
    def run_simulation(self, strategy_function, **strategy_params) -> Dict[str, Any]:
        """
        Run complete simulation with a given strategy
        
        Args:
            strategy_function: Function that takes (environment, product_id, **params) 
                             and returns action dict
            **strategy_params: Parameters to pass to strategy function
        
        Returns:
            Simulation results dictionary
        """
        self.reset()
        
        while self.current_day < self.simulation_days:
            # Get actions from strategy
            actions = {}
            for product_id in self.products:
                action = strategy_function(self, product_id, **strategy_params)
                actions[product_id] = action
            
            # Execute step
            state, step_info, done = self.step(actions)
            
            if done:
                break
        
        # Calculate final metrics
        final_state = self._get_current_state()
        
        results = {
            "simulation_days": self.current_day,
            "total_cost": self.total_cost,
            "total_demand": self.total_demand,
            "total_fulfilled": self.total_fulfilled,
            "service_level": final_state.service_level,
            "stockout_events": self.stockout_events,
            "total_orders": self.total_orders,
            "avg_inventory_level": np.mean(list(self.inventory_levels.values())),
            "final_inventory": self.inventory_levels.copy(),
            "cost_per_unit_demand": self.total_cost / max(self.total_demand, 1),
            "orders_per_day": self.total_orders / max(self.current_day, 1),
            "state_history": self.state_history,
            "action_history": self.action_history
        }
        
        return results


# Strategy functions for testing
def simple_reorder_point_strategy(env: InventorySimulationEnvironment, product_id: str, 
                                 reorder_point: int = None, order_quantity: int = None) -> Dict:
    """Simple reorder point strategy"""
    product = env.products[product_id]
    current_stock = env.inventory_levels[product_id]
    
    # Default parameters if not provided
    if reorder_point is None:
        recent_demand = env.demand_history[product_id][-30:] if env.demand_history[product_id] else [10]
        avg_demand = np.mean(recent_demand)
        reorder_point = int(avg_demand * product.lead_time_days * 1.5)
    
    if order_quantity is None:
        recent_demand = env.demand_history[product_id][-30:] if env.demand_history[product_id] else [10]
        avg_demand = np.mean(recent_demand)
        order_quantity = int(avg_demand * 30)  # 30 days supply
    
    # Check if reorder is needed
    if current_stock <= reorder_point:
        return {
            "action_type": ActionType.ORDER,
            "quantity": max(product.min_order_quantity, min(product.max_order_quantity, order_quantity))
        }
    
    return {"action_type": ActionType.NO_ACTION, "quantity": 0}


def economic_order_quantity_strategy(env: InventorySimulationEnvironment, product_id: str) -> Dict:
    """Economic Order Quantity (EOQ) strategy"""
    product = env.products[product_id]
    current_stock = env.inventory_levels[product_id]
    
    # Calculate EOQ
    recent_demand = env.demand_history[product_id][-90:] if env.demand_history[product_id] else [10]
    annual_demand = np.mean(recent_demand) * 365
    
    holding_cost = product.unit_cost * env.holding_cost_rate * 365
    order_cost = env.order_cost
    
    if holding_cost > 0:
        eoq = np.sqrt(2 * annual_demand * order_cost / holding_cost)
        eoq = int(max(product.min_order_quantity, min(product.max_order_quantity, eoq)))
    else:
        eoq = product.min_order_quantity
    
    # Reorder point
    avg_demand = np.mean(recent_demand) if recent_demand else 10
    reorder_point = int(avg_demand * product.lead_time_days * 1.2)  # 20% safety stock
    
    if current_stock <= reorder_point:
        return {"action_type": ActionType.ORDER, "quantity": eoq}
    
    return {"action_type": ActionType.NO_ACTION, "quantity": 0}


def random_strategy(env: InventorySimulationEnvironment, product_id: str) -> Dict:
    """Random strategy for baseline comparison"""
    product = env.products[product_id]
    
    # 10% chance to order
    if np.random.random() < 0.1:
        quantity = np.random.randint(product.min_order_quantity, product.max_order_quantity + 1)
        return {"action_type": ActionType.ORDER, "quantity": quantity}
    
    return {"action_type": ActionType.NO_ACTION, "quantity": 0}


class StrategyComparator:
    """Compare different inventory strategies"""
    
    def __init__(self, products: List[Product], simulation_days: int = 365):
        self.products = products
        self.simulation_days = simulation_days
        self.results = {}
    
    def compare_strategies(self, strategies: Dict[str, Tuple], num_runs: int = 5) -> Dict[str, Any]:
        """
        Compare multiple strategies
        
        Args:
            strategies: Dict of {strategy_name: (strategy_function, params_dict)}
            num_runs: Number of simulation runs per strategy
        
        Returns:
            Comparison results
        """
        comparison_results = {}
        
        for strategy_name, (strategy_func, params) in strategies.items():
            print(f"Testing strategy: {strategy_name}")
            
            strategy_results = []
            
            for run in range(num_runs):
                env = InventorySimulationEnvironment(self.products, self.simulation_days)
                result = env.run_simulation(strategy_func, **params)
                strategy_results.append(result)
            
            # Aggregate results
            aggregated = self._aggregate_results(strategy_results)
            comparison_results[strategy_name] = aggregated
        
        # Create comparison summary
        summary = self._create_comparison_summary(comparison_results)
        
        return {
            "detailed_results": comparison_results,
            "summary": summary,
            "best_strategy": self._find_best_strategy(comparison_results)
        }
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results from multiple runs"""
        metrics = ["total_cost", "service_level", "stockout_events", "total_orders", "cost_per_unit_demand"]
        
        aggregated = {}
        for metric in metrics:
            values = [r[metric] for r in results]
            aggregated[metric] = {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values)
            }
        
        aggregated["num_runs"] = len(results)
        return aggregated
    
    def _create_comparison_summary(self, results: Dict[str, Dict]) -> pd.DataFrame:
        """Create summary comparison table"""
        summary_data = []
        
        for strategy_name, strategy_results in results.items():
            summary_data.append({
                "Strategy": strategy_name,
                "Avg Cost": strategy_results["total_cost"]["mean"],
                "Avg Service Level": strategy_results["service_level"]["mean"],
                "Avg Stockouts": strategy_results["stockout_events"]["mean"],
                "Cost per Unit": strategy_results["cost_per_unit_demand"]["mean"],
                "Cost Std": strategy_results["total_cost"]["std"]
            })
        
        return pd.DataFrame(summary_data)
    
    def _find_best_strategy(self, results: Dict[str, Dict]) -> Dict[str, str]:
        """Find best strategy for different criteria"""
        best_strategies = {}
        
        # Best by lowest cost
        min_cost = float('inf')
        best_cost_strategy = None
        
        # Best by highest service level
        max_service = 0
        best_service_strategy = None
        
        # Best by cost-service trade-off (composite score)
        best_composite_score = -float('inf')
        best_composite_strategy = None
        
        for strategy_name, strategy_results in results.items():
            cost = strategy_results["total_cost"]["mean"]
            service = strategy_results["service_level"]["mean"]
            
            if cost < min_cost:
                min_cost = cost
                best_cost_strategy = strategy_name
            
            if service > max_service:
                max_service = service
                best_service_strategy = strategy_name
            
            # Composite score: normalize service (0-1) and cost (inverse), then combine
            composite_score = service - (cost / 100000)  # Adjust scaling as needed
            if composite_score > best_composite_score:
                best_composite_score = composite_score
                best_composite_strategy = strategy_name
        
        return {
            "lowest_cost": best_cost_strategy,
            "highest_service": best_service_strategy,
            "best_composite": best_composite_strategy
        }


def main():
    """Test simulation environment"""
    # Create sample products
    products = [
        Product(
            product_id="TEST-001",
            name="Test Product 1",
            category="personal_care",
            unit_cost=10.0,
            selling_price=15.0,
            lead_time_days=5,
            shelf_life_days=365,
            min_order_quantity=10,
            max_order_quantity=1000
        ),
        Product(
            product_id="TEST-002",
            name="Test Product 2",
            category="food_beverage",
            unit_cost=5.0,
            selling_price=8.0,
            lead_time_days=3,
            shelf_life_days=180,
            min_order_quantity=20,
            max_order_quantity=500
        )
    ]
    
    # Test strategy comparison
    comparator = StrategyComparator(products, simulation_days=90)
    
    strategies = {
        "Simple Reorder Point": (simple_reorder_point_strategy, {}),
        "EOQ": (economic_order_quantity_strategy, {}),
        "Random": (random_strategy, {})
    }
    
    results = comparator.compare_strategies(strategies, num_runs=3)
    
    print("Strategy Comparison Results:")
    print(results["summary"])
    print(f"\nBest strategies: {results['best_strategy']}")


if __name__ == "__main__":
    main()