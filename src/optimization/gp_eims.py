"""
GP-EIMS (Gaussian Process Expected Improvement Method) for strategic inventory optimization
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from datetime import datetime, timedelta
import uuid
import warnings
from scipy.optimize import minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

# Suppress sklearn convergence warnings for production use
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn.gaussian_process')

from ..data.models import (
    Product, Demand, OptimizationParameters, OptimizationResults, 
    PerformanceMetrics, get_session
)
from config.settings import GP_EIMS_CONFIG, SIMULATION_CONFIG


class InventorySimulator:
    """Simple inventory simulation for objective function evaluation"""
    
    def __init__(self, product: Product, demand_history: List[Demand]):
        self.product = product
        self.demand_history = demand_history
        self.holding_cost_rate = SIMULATION_CONFIG["holding_cost_rate"] / 365  # Daily rate
        self.stockout_penalty = SIMULATION_CONFIG["stockout_penalty"]
        self.order_cost = SIMULATION_CONFIG["order_cost"]
    
    def simulate(self, reorder_point: int, safety_stock: int, order_quantity: int, 
                 simulation_days: int = 90) -> Dict[str, float]:
        """
        Simulate inventory system with given parameters
        Returns: Dictionary with cost metrics
        """
        # Initialize simulation state
        current_stock = safety_stock + order_quantity
        total_holding_cost = 0.0
        total_stockout_cost = 0.0
        total_order_cost = 0.0
        stockout_events = 0
        total_orders = 0
        
        # Get recent demand data
        recent_demand = sorted(self.demand_history[-simulation_days:], key=lambda x: x.date)
        
        for i, demand_record in enumerate(recent_demand):
            daily_demand = demand_record.quantity_demanded
            
            # Check if reorder is needed
            if current_stock <= reorder_point:
                current_stock += order_quantity
                total_order_cost += self.order_cost
                total_orders += 1
            
            # Fulfill demand
            fulfilled = min(daily_demand, current_stock)
            stockout = daily_demand - fulfilled
            current_stock = max(0, current_stock - fulfilled)
            
            # Calculate costs
            total_holding_cost += current_stock * self.product.unit_cost * self.holding_cost_rate
            
            if stockout > 0:
                total_stockout_cost += stockout * self.stockout_penalty
                stockout_events += 1
        
        # Calculate metrics
        total_cost = total_holding_cost + total_stockout_cost + total_order_cost
        service_level = 1.0 - (stockout_events / len(recent_demand)) if recent_demand else 1.0
        
        return {
            "total_cost": total_cost,
            "holding_cost": total_holding_cost,
            "stockout_cost": total_stockout_cost,
            "order_cost": total_order_cost,
            "service_level": service_level,
            "stockout_events": stockout_events,
            "total_orders": total_orders
        }


class GPEIMSOptimizer:
    """Gaussian Process Expected Improvement Method for inventory optimization"""
    
    def __init__(self, database_session: Session):
        self.session = database_session
        self.config = GP_EIMS_CONFIG
        
        # Initialize Gaussian Process with configuration-based kernel bounds
        kernel_bounds = self.config["kernel_bounds"]
        constant_bounds = kernel_bounds["constant_value"]
        rbf_bounds = kernel_bounds["length_scale"]
        
        kernel = C(1.0, constant_bounds) * RBF(1.0, rbf_bounds)
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=self.config["noise_variance"],
            n_restarts_optimizer=self.config["n_restarts_optimizer"],
            optimizer=self.config["optimizer"],
            random_state=42
        )
        
        # Data normalization
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.data_normalized = False
        
        # Optimization history
        self.X_observed = []  # Parameter combinations tried
        self.y_observed = []  # Objective values observed
        
    def _normalize_data(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Normalize input features and target values using StandardScaler"""
        if not self.data_normalized:
            X_normalized = self.scaler_X.fit_transform(X)
            y_normalized = self.scaler_y.fit_transform(y.reshape(-1, 1)).flatten()
            self.data_normalized = True
        else:
            X_normalized = self.scaler_X.transform(X)
            y_normalized = self.scaler_y.transform(y.reshape(-1, 1)).flatten()
        return X_normalized, y_normalized
    
    def _denormalize_prediction(self, y_pred: np.ndarray, y_std: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Denormalize predictions back to original scale"""
        y_pred_denorm = self.scaler_y.inverse_transform(y_pred.reshape(-1, 1)).flatten()
        if y_std is not None:
            # Scale standard deviation by the same factor
            scale_factor = np.sqrt(self.scaler_y.var_[0])
            y_std_denorm = y_std * scale_factor
            return y_pred_denorm, y_std_denorm
        return y_pred_denorm, None
    
    def _normalize_parameters(self, params: np.ndarray, bounds: List[Tuple[float, float]]) -> np.ndarray:
        """Normalize parameters to [0, 1] range"""
        normalized = np.zeros_like(params)
        for i, (low, high) in enumerate(bounds):
            normalized[i] = (params[i] - low) / (high - low)
        return normalized
    
    def _denormalize_parameters(self, normalized_params: np.ndarray,
                               bounds: List[Tuple[float, float]]) -> np.ndarray:
        """Denormalize parameters from [0, 1] range"""
        params = np.zeros_like(normalized_params)
        for i, (low, high) in enumerate(bounds):
            params[i] = normalized_params[i] * (high - low) + low
        return params
    
    def _expected_improvement(self, X: np.ndarray, gp: GaussianProcessRegressor, 
                             y_best: float, xi: float = 0.01) -> np.ndarray:
        """
        Calculate Expected Improvement acquisition function
        """
        mu, sigma = gp.predict(X, return_std=True)
        sigma = sigma.reshape(-1, 1)
        
        # Handle numerical stability
        with np.errstate(divide='warn'):
            imp = mu - y_best - xi
            Z = imp / sigma
            ei = imp * self._normal_cdf(Z) + sigma * self._normal_pdf(Z)
            ei[sigma == 0.0] = 0.0
        
        return ei
    
    def _normal_cdf(self, x: np.ndarray) -> np.ndarray:
        """Standard normal cumulative distribution function"""
        return 0.5 * (1 + np.sign(x) * np.sqrt(1 - np.exp(-2 * x**2 / np.pi)))
    
    def _normal_pdf(self, x: np.ndarray) -> np.ndarray:
        """Standard normal probability density function"""
        return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)
    
    def _objective_function(self, params: np.ndarray, product: Product, 
                           demand_history: List[Demand]) -> float:
        """
        Objective function to minimize (total inventory cost)
        """
        reorder_point, safety_stock, order_quantity = params.astype(int)
        
        # Ensure valid parameters
        reorder_point = max(0, reorder_point)
        safety_stock = max(0, safety_stock)
        order_quantity = max(product.min_order_quantity, 
                           min(product.max_order_quantity, order_quantity))
        
        # Run simulation
        simulator = InventorySimulator(product, demand_history)
        results = simulator.simulate(reorder_point, safety_stock, order_quantity)
        
        # Multi-objective: minimize cost while maintaining service level
        cost_penalty = results["total_cost"]
        service_penalty = 0.0
        
        # Penalty for service level below target
        target_service_level = SIMULATION_CONFIG["service_level_target"]
        if results["service_level"] < target_service_level:
            service_penalty = 10000 * (target_service_level - results["service_level"])
        
        return cost_penalty + service_penalty
    
    def _get_parameter_bounds(self, product: Product, demand_stats: Dict) -> List[Tuple[int, int]]:
        """Get reasonable bounds for optimization parameters"""
        avg_demand = demand_stats["mean_demand"]
        max_demand = demand_stats["max_demand"]
        lead_time = product.lead_time_days
        
        # Reorder point: lead time demand + buffer
        reorder_point_bounds = (
            int(avg_demand * lead_time * 0.5),
            int(max_demand * lead_time * 2)
        )
        
        # Safety stock: 0 to 30 days of average demand
        safety_stock_bounds = (0, int(avg_demand * 30))
        
        # Order quantity: min to reasonable max
        order_quantity_bounds = (
            product.min_order_quantity,
            min(product.max_order_quantity, int(avg_demand * 60))  # 2 months supply
        )
        
        return [reorder_point_bounds, safety_stock_bounds, order_quantity_bounds]
    
    def optimize_product(self, product_id: str) -> Optional[OptimizationParameters]:
        """
        Optimize inventory parameters for a single product using GP-EIMS
        """
        # Get product and demand data
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Get recent demand history
        demand_history = self.session.query(Demand).filter(
            Demand.product_id == product_id,
            Demand.is_forecast == False
        ).order_by(Demand.date.desc()).limit(180).all()  # Last 6 months
        
        if len(demand_history) < 30:
            print(f"Insufficient demand history for product {product_id}")
            return None
        
        # Calculate demand statistics
        demand_values = [d.quantity_demanded for d in demand_history]
        demand_stats = {
            "mean_demand": np.mean(demand_values),
            "std_demand": np.std(demand_values),
            "max_demand": np.max(demand_values),
            "min_demand": np.min(demand_values)
        }
        
        # Get parameter bounds
        bounds = self._get_parameter_bounds(product, demand_stats)
        
        # Initialize with current parameters or reasonable defaults
        current_params = self.session.query(OptimizationParameters).filter(
            OptimizationParameters.product_id == product_id,
            OptimizationParameters.is_active == True
        ).first()
        
        if current_params:
            initial_guess = np.array([
                current_params.reorder_point,
                current_params.safety_stock,
                current_params.order_quantity
            ])
        else:
            # Default initialization
            initial_guess = np.array([
                int(demand_stats["mean_demand"] * product.lead_time_days * 1.5),
                int(demand_stats["mean_demand"] * 7),  # 1 week safety stock
                int(demand_stats["mean_demand"] * 30)   # 1 month order quantity
            ])
        
        # Ensure initial guess is within bounds
        for i, (low, high) in enumerate(bounds):
            initial_guess[i] = max(low, min(high, initial_guess[i]))
        
        # Bayesian Optimization loop
        best_params = initial_guess.copy()
        best_value = float('inf')
        
        # Evaluate initial point
        initial_value = self._objective_function(initial_guess, product, demand_history)
        self.X_observed = [self._normalize_parameters(initial_guess, bounds)]
        self.y_observed = [initial_value]
        
        if initial_value < best_value:
            best_value = initial_value
            best_params = initial_guess.copy()
        
        print(f"Optimizing {product_id}: Initial value = {initial_value:.2f}")
        
        for iteration in range(self.config["max_iterations"]):
            if len(self.X_observed) > 1:
                # Fit Gaussian Process with normalization and warning suppression
                X_array = np.array(self.X_observed)
                y_array = np.array(self.y_observed)
                
                # Normalize data for better GP performance
                X_normalized, y_normalized = self._normalize_data(X_array, y_array)
                
                # Suppress warnings during fitting
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.gp.fit(X_normalized, y_normalized)
                
                # Find next point to evaluate using Expected Improvement
                def neg_ei(x):
                    x_reshaped = x.reshape(1, -1)
                    # Transform to normalized space for GP prediction
                    x_norm = self.scaler_X.transform(self._denormalize_parameters(x_reshaped, bounds))
                    ei = self._expected_improvement(x_norm, self.gp, np.min(y_normalized))[0]
                    return -ei
                
                # Optimize acquisition function
                best_ei = float('inf')
                best_x = None
                
                # Multiple random starts for acquisition optimization
                for _ in range(self.config["n_candidates"]):
                    x0 = np.random.random(len(bounds))
                    result = minimize(
                        neg_ei, x0, method='L-BFGS-B',
                        bounds=[(0, 1)] * len(bounds),
                        options={'maxiter': self.config.get("max_iter", 1000)}
                    )
                    
                    if result.fun < best_ei:
                        best_ei = result.fun
                        best_x = result.x
                
                if best_x is not None:
                    next_params_normalized = best_x
                else:
                    # Fallback to random sampling
                    next_params_normalized = np.random.random(len(bounds))
            else:
                # Random exploration for first few iterations
                next_params_normalized = np.random.random(len(bounds))
            
            # Denormalize and evaluate
            next_params = self._denormalize_parameters(next_params_normalized, bounds)
            next_params = next_params.astype(int)
            
            # Ensure parameters are within bounds
            for i, (low, high) in enumerate(bounds):
                next_params[i] = max(low, min(high, next_params[i]))
            
            # Evaluate objective function
            next_value = self._objective_function(next_params, product, demand_history)
            
            # Update observations
            self.X_observed.append(next_params_normalized)
            self.y_observed.append(next_value)
            
            # Update best solution
            if next_value < best_value:
                best_value = next_value
                best_params = next_params.copy()
                print(f"Iteration {iteration + 1}: New best value = {best_value:.2f}")
            
            # Early stopping if improvement is small
            if iteration > 10 and len(self.y_observed) > 5:
                recent_improvement = np.min(self.y_observed[-5:]) - np.min(self.y_observed[:-5])
                if abs(recent_improvement) < best_value * 0.01:  # 1% improvement threshold
                    print(f"Early stopping at iteration {iteration + 1}")
                    break
        
        # Create optimization result
        run_id = str(uuid.uuid4())
        
        # Get final GP predictions for the best parameters
        if len(self.X_observed) > 1:
            best_params_normalized = self._normalize_parameters(best_params, bounds)
            gp_mean, gp_std = self.gp.predict(best_params_normalized.reshape(1, -1), return_std=True)
            gp_variance = gp_std[0] ** 2
            
            # Calculate acquisition value
            acquisition_value = self._expected_improvement(
                best_params_normalized.reshape(1, -1), self.gp, np.min(self.y_observed)
            )[0]
        else:
            gp_mean = [best_value]
            gp_variance = 0.0
            acquisition_value = 0.0
        
        # Save optimization parameters
        opt_params = OptimizationParameters(
            product_id=product_id,
            timestamp=datetime.utcnow(),
            reorder_point=int(best_params[0]),
            safety_stock=int(best_params[1]),
            order_quantity=int(best_params[2]),
            review_period_days=1,
            is_active=True,
            gp_mean=float(gp_mean[0]),
            gp_variance=float(gp_variance),
            acquisition_value=float(acquisition_value)
        )
        
        # Deactivate previous parameters
        self.session.query(OptimizationParameters).filter(
            OptimizationParameters.product_id == product_id,
            OptimizationParameters.is_active == True
        ).update({"is_active": False})
        
        self.session.add(opt_params)
        
        # Save optimization results
        opt_result = OptimizationResults(
            run_id=run_id,
            method="GP-EIMS",
            timestamp=datetime.utcnow(),
            objective_value=float(best_value),
            constraints_satisfied=True,
            execution_time_seconds=0.0,  # Would need timing in real implementation
            convergence_iterations=len(self.y_observed),
            final_error=float(best_value)
        )
        
        opt_result.set_parameters({
            "product_id": product_id,
            "reorder_point": int(best_params[0]),
            "safety_stock": int(best_params[1]),
            "order_quantity": int(best_params[2]),
            "bounds": bounds,
            "demand_stats": demand_stats
        })
        
        self.session.add(opt_result)
        self.session.commit()
        
        print(f"Optimization completed for {product_id}")
        print(f"Best parameters: ROP={best_params[0]}, SS={best_params[1]}, OQ={best_params[2]}")
        print(f"Best objective value: {best_value:.2f}")
        
        return opt_params
    
    def optimize_all_products(self) -> List[OptimizationParameters]:
        """
        Optimize inventory parameters for all products
        """
        products = self.session.query(Product).all()
        results = []
        
        print(f"Starting GP-EIMS optimization for {len(products)} products...")
        
        for i, product in enumerate(products):
            print(f"\nOptimizing product {i+1}/{len(products)}: {product.product_id}")
            
            try:
                result = self.optimize_product(product.product_id)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error optimizing {product.product_id}: {str(e)}")
                continue
        
        print(f"\nGP-EIMS optimization completed. Optimized {len(results)} products.")
        return results


def main():
    """Test GP-EIMS optimization"""
    from config.settings import DATABASE_URL
    from ..data.models import create_database
    
    engine = create_database(DATABASE_URL)
    session = get_session(engine)
    
    optimizer = GPEIMSOptimizer(session)
    
    # Test with first product
    products = session.query(Product).limit(1).all()
    if products:
        result = optimizer.optimize_product(products[0].product_id)
        print(f"Optimization result: {result}")
    
    session.close()


if __name__ == "__main__":
    main()