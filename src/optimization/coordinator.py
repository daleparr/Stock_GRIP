"""
Coordination logic for integrating GP-EIMS and MPC-RL-MOBO optimization approaches
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time
from sqlalchemy.orm import Session

from .gp_eims import GPEIMSOptimizer
from .mpc_rl_mobo import MPCRLMOBOController
from ..data.models import (
    Product, OptimizationParameters, OptimizationResults, 
    PerformanceMetrics, get_session
)
from config.settings import GP_EIMS_CONFIG, MPC_RL_CONFIG, DATABASE_URL


class OptimizationCoordinator:
    """
    Coordinates strategic (GP-EIMS) and tactical (MPC-RL-MOBO) optimization
    """
    
    def __init__(self, database_session: Session):
        self.session = database_session
        
        # Initialize optimizers with error handling
        try:
            self.gp_eims_optimizer = GPEIMSOptimizer(database_session)
            self.gp_eims_available = True
        except Exception as e:
            print(f"Warning: GP-EIMS optimizer initialization failed: {e}")
            self.gp_eims_optimizer = None
            self.gp_eims_available = False
        
        try:
            self.mpc_rl_controller = MPCRLMOBOController(database_session)
            self.mpc_rl_available = True
        except Exception as e:
            print(f"Warning: MPC-RL-MOBO controller initialization failed: {e}")
            self.mpc_rl_controller = None
            self.mpc_rl_available = False
        
        # Coordination state
        self.last_strategic_optimization = None
        self.strategic_optimization_interval = timedelta(
            days=GP_EIMS_CONFIG.get("optimization_interval_days", 7)
        )
        
        # Performance tracking
        self.performance_history = []
        self.is_running = False
        self.optimization_thread = None
        
    def should_run_strategic_optimization(self) -> bool:
        """Check if strategic optimization should be run"""
        if self.last_strategic_optimization is None:
            return True
        
        time_since_last = datetime.utcnow() - self.last_strategic_optimization
        return time_since_last >= self.strategic_optimization_interval
    
    def run_strategic_optimization(self) -> Dict[str, any]:
        """
        Run GP-EIMS strategic optimization for all products
        """
        if not self.gp_eims_available:
            print("Strategic optimization unavailable - GP-EIMS not initialized")
            return {
                "status": "unavailable",
                "message": "GP-EIMS optimizer not available",
                "products_optimized": 0
            }
            
        print("Starting strategic optimization (GP-EIMS)...")
        start_time = datetime.utcnow()
        
        try:
            # Run GP-EIMS optimization
            optimized_params = self.gp_eims_optimizer.optimize_all_products()
            
            # Update last optimization time
            self.last_strategic_optimization = datetime.utcnow()
            
            # Calculate performance metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                "status": "success",
                "timestamp": self.last_strategic_optimization,
                "products_optimized": len(optimized_params),
                "execution_time_seconds": execution_time,
                "method": "GP-EIMS"
            }
            
            # Save performance metrics
            metrics = [
                PerformanceMetrics(
                    metric_name="strategic_optimization_runtime",
                    metric_value=execution_time,
                    metric_category="efficiency",
                    time_period="weekly"
                ),
                PerformanceMetrics(
                    metric_name="products_optimized_strategic",
                    metric_value=len(optimized_params),
                    metric_category="efficiency",
                    time_period="weekly"
                )
            ]
            
            for metric in metrics:
                self.session.add(metric)
            self.session.commit()
            
            print(f"Strategic optimization completed: {len(optimized_params)} products optimized")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "timestamp": datetime.utcnow(),
                "error_message": str(e),
                "method": "GP-EIMS"
            }
            print(f"Strategic optimization failed: {str(e)}")
            return error_result
    
    def run_tactical_optimization(self) -> Dict[str, any]:
        """
        Run MPC-RL-MOBO tactical optimization cycle
        """
        try:
            # Run MPC-RL-MOBO optimization
            result = self.mpc_rl_controller.run_optimization_cycle()
            result["status"] = "success"
            result["method"] = "MPC-RL-MOBO"
            
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "timestamp": datetime.utcnow(),
                "error_message": str(e),
                "method": "MPC-RL-MOBO"
            }
            print(f"Tactical optimization failed: {str(e)}")
            return error_result
    
    def validate_parameter_consistency(self) -> List[Dict[str, any]]:
        """
        Validate consistency between strategic parameters and tactical decisions
        """
        issues = []
        
        # Get all products with strategic parameters
        products_with_params = self.session.query(Product).join(OptimizationParameters).filter(
            OptimizationParameters.is_active == True
        ).all()
        
        for product in products_with_params:
            strategic_params = self.session.query(OptimizationParameters).filter(
                OptimizationParameters.product_id == product.product_id,
                OptimizationParameters.is_active == True
            ).first()
            
            if not strategic_params:
                continue
            
            # Check for recent tactical decisions that deviate significantly from strategic parameters
            recent_actions = self.session.query(InventoryActions).filter(
                InventoryActions.product_id == product.product_id,
                InventoryActions.timestamp >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            if recent_actions:
                avg_tactical_quantity = np.mean([action.quantity for action in recent_actions])
                strategic_quantity = strategic_params.order_quantity
                
                # Check for significant deviation (>50%)
                if abs(avg_tactical_quantity - strategic_quantity) / strategic_quantity > 0.5:
                    issues.append({
                        "product_id": product.product_id,
                        "issue_type": "quantity_deviation",
                        "strategic_quantity": strategic_quantity,
                        "avg_tactical_quantity": avg_tactical_quantity,
                        "deviation_percent": abs(avg_tactical_quantity - strategic_quantity) / strategic_quantity * 100
                    })
        
        return issues
    
    def calculate_system_performance(self) -> Dict[str, float]:
        """
        Calculate overall system performance metrics
        """
        # Get recent performance metrics
        recent_metrics = self.session.query(PerformanceMetrics).filter(
            PerformanceMetrics.timestamp >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if not recent_metrics:
            return {}
        
        # Group metrics by category
        metrics_by_category = {}
        for metric in recent_metrics:
            if metric.metric_category not in metrics_by_category:
                metrics_by_category[metric.metric_category] = []
            metrics_by_category[metric.metric_category].append(metric.metric_value)
        
        # Calculate averages
        performance = {}
        for category, values in metrics_by_category.items():
            performance[f"avg_{category}"] = np.mean(values)
            performance[f"std_{category}"] = np.std(values)
        
        # Calculate composite scores
        if "service" in metrics_by_category and "cost" in metrics_by_category:
            service_score = np.mean(metrics_by_category["service"])
            cost_score = np.mean(metrics_by_category["cost"])
            
            # Normalize and combine (higher service is better, lower cost is better)
            performance["composite_score"] = service_score - (cost_score / 10000)  # Normalize cost
        
        return performance
    
    def adaptive_parameter_adjustment(self) -> Dict[str, any]:
        """
        Adaptively adjust optimization parameters based on performance
        """
        performance = self.calculate_system_performance()
        adjustments = []
        
        if not performance:
            return {"adjustments": adjustments, "reason": "insufficient_data"}
        
        # Adjust GP-EIMS parameters based on performance
        if "avg_efficiency" in performance:
            efficiency = performance["avg_efficiency"]
            
            # If efficiency is low, increase GP-EIMS iterations
            if efficiency < 0.7:  # Threshold for low efficiency
                new_max_iterations = min(100, GP_EIMS_CONFIG["max_iterations"] * 1.2)
                adjustments.append({
                    "parameter": "gp_eims_max_iterations",
                    "old_value": GP_EIMS_CONFIG["max_iterations"],
                    "new_value": int(new_max_iterations),
                    "reason": "low_efficiency"
                })
        
        # Adjust MPC-RL parameters based on service level
        if "avg_service" in performance:
            service_level = performance["avg_service"]
            
            # If service level is low, increase prediction horizon
            if service_level < 0.9:  # Below 90% service level
                new_horizon = min(14, MPC_RL_CONFIG["prediction_horizon"] + 1)
                adjustments.append({
                    "parameter": "mpc_prediction_horizon",
                    "old_value": MPC_RL_CONFIG["prediction_horizon"],
                    "new_value": new_horizon,
                    "reason": "low_service_level"
                })
            
            # If service level is very high, we might be over-stocking
            elif service_level > 0.98:
                new_horizon = max(3, MPC_RL_CONFIG["prediction_horizon"] - 1)
                adjustments.append({
                    "parameter": "mpc_prediction_horizon",
                    "old_value": MPC_RL_CONFIG["prediction_horizon"],
                    "new_value": new_horizon,
                    "reason": "high_service_level_potential_overstock"
                })
        
        return {
            "adjustments": adjustments,
            "performance_metrics": performance,
            "timestamp": datetime.utcnow()
        }
    
    def run_coordination_cycle(self) -> Dict[str, any]:
        """
        Run one complete coordination cycle
        """
        cycle_start = datetime.utcnow()
        results = {
            "timestamp": cycle_start,
            "strategic_optimization": None,
            "tactical_optimization": None,
            "validation_issues": [],
            "performance_metrics": {},
            "parameter_adjustments": {}
        }
        
        # 1. Check if strategic optimization is needed
        if self.should_run_strategic_optimization():
            print("Running strategic optimization...")
            results["strategic_optimization"] = self.run_strategic_optimization()
        
        # 2. Run tactical optimization
        print("Running tactical optimization...")
        results["tactical_optimization"] = self.run_tactical_optimization()
        
        # 3. Validate parameter consistency
        print("Validating parameter consistency...")
        results["validation_issues"] = self.validate_parameter_consistency()
        
        # 4. Calculate system performance
        print("Calculating system performance...")
        results["performance_metrics"] = self.calculate_system_performance()
        
        # 5. Adaptive parameter adjustment
        print("Checking for parameter adjustments...")
        results["parameter_adjustments"] = self.adaptive_parameter_adjustment()
        
        # 6. Log cycle completion
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        
        cycle_metric = PerformanceMetrics(
            metric_name="coordination_cycle_duration",
            metric_value=cycle_duration,
            metric_category="efficiency",
            time_period="daily"
        )
        self.session.add(cycle_metric)
        self.session.commit()
        
        print(f"Coordination cycle completed in {cycle_duration:.2f} seconds")
        
        return results
    
    def start_continuous_optimization(self, tactical_interval_minutes: int = 30):
        """
        Start continuous optimization with scheduled strategic and tactical cycles
        """
        if self.is_running:
            print("Optimization is already running")
            return
        
        self.is_running = True
        
        def run_scheduler():
            last_strategic = time.time()
            last_tactical = time.time()
            last_coordination = time.time()
            
            strategic_interval = 7 * 24 * 3600  # 7 days in seconds
            tactical_interval = tactical_interval_minutes * 60  # minutes to seconds
            coordination_interval = 24 * 3600  # 24 hours in seconds
            
            while self.is_running:
                current_time = time.time()
                
                # Check for strategic optimization (weekly)
                if current_time - last_strategic >= strategic_interval:
                    try:
                        self.run_strategic_optimization()
                        last_strategic = current_time
                    except Exception as e:
                        print(f"Strategic optimization error: {e}")
                
                # Check for tactical optimization
                if current_time - last_tactical >= tactical_interval:
                    try:
                        self.run_tactical_optimization()
                        last_tactical = current_time
                    except Exception as e:
                        print(f"Tactical optimization error: {e}")
                
                # Check for coordination cycle (daily)
                if current_time - last_coordination >= coordination_interval:
                    try:
                        self.run_coordination_cycle()
                        last_coordination = current_time
                    except Exception as e:
                        print(f"Coordination cycle error: {e}")
                
                time.sleep(60)  # Check every minute
        
        self.optimization_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.optimization_thread.start()
        
        print(f"Continuous optimization started:")
        print(f"- Strategic optimization: Weekly")
        print(f"- Tactical optimization: Every {tactical_interval_minutes} minutes")
        print(f"- Coordination cycle: Daily at 02:00")
    
    def stop_continuous_optimization(self):
        """Stop continuous optimization"""
        self.is_running = False
        
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=5)
        
        print("Continuous optimization stopped")
    
    def get_optimization_status(self) -> Dict[str, any]:
        """Get current optimization status"""
        return {
            "is_running": self.is_running,
            "last_strategic_optimization": self.last_strategic_optimization,
            "next_strategic_optimization": (
                self.last_strategic_optimization + self.strategic_optimization_interval
                if self.last_strategic_optimization else None
            ),
            "strategic_interval_days": GP_EIMS_CONFIG["optimization_interval_days"],
            "tactical_running": self.is_running,
            "performance_summary": self.calculate_system_performance()
        }


class StockGRIPSystem:
    """
    Main system class that orchestrates the entire Stock_GRIP application
    """
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = DATABASE_URL
        
        from ..data.models import create_database
        self.engine = create_database(database_url)
        self.session = get_session(self.engine)
        
        # Initialize coordinator
        self.coordinator = OptimizationCoordinator(self.session)
        
        # System state
        self.is_initialized = False
    
    def initialize_system(self, generate_sample_data: bool = True) -> Dict[str, any]:
        """
        Initialize the Stock_GRIP system
        """
        print("Initializing Stock_GRIP system...")
        
        if generate_sample_data:
            print("Generating sample data...")
            from ..data.data_generator import FMCGDataGenerator
            
            generator = FMCGDataGenerator(self.engine.url)
            generator.populate_database()
            generator.close()
        
        # Run initial strategic optimization
        print("Running initial strategic optimization...")
        strategic_result = self.coordinator.run_strategic_optimization()
        
        # Run initial tactical optimization
        print("Running initial tactical optimization...")
        tactical_result = self.coordinator.run_tactical_optimization()
        
        self.is_initialized = True
        
        return {
            "status": "initialized",
            "timestamp": datetime.utcnow(),
            "strategic_optimization": strategic_result,
            "tactical_optimization": tactical_result
        }
    
    def start(self, continuous: bool = True, tactical_interval_minutes: int = 30):
        """Start the Stock_GRIP system"""
        if not self.is_initialized:
            self.initialize_system()
        
        if continuous:
            self.coordinator.start_continuous_optimization(tactical_interval_minutes)
        
        print("Stock_GRIP system started successfully!")
    
    def stop(self):
        """Stop the Stock_GRIP system"""
        self.coordinator.stop_continuous_optimization()
        self.session.close()
        print("Stock_GRIP system stopped")
    
    def get_system_status(self) -> Dict[str, any]:
        """Get comprehensive system status"""
        return {
            "system_initialized": self.is_initialized,
            "optimization_status": self.coordinator.get_optimization_status(),
            "database_connected": self.session.is_active,
            "timestamp": datetime.utcnow()
        }


def main():
    """Test the coordination system"""
    system = StockGRIPSystem()
    
    # Initialize and start system
    init_result = system.initialize_system()
    print(f"Initialization result: {init_result}")
    
    # Run one coordination cycle
    cycle_result = system.coordinator.run_coordination_cycle()
    print(f"Coordination cycle result: {cycle_result}")
    
    # Get system status
    status = system.get_system_status()
    print(f"System status: {status}")
    
    system.stop()


if __name__ == "__main__":
    main()