"""
Performance metrics and monitoring utilities for Stock_GRIP
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..data.models import (
    Product, Inventory, Demand, InventoryActions, OptimizationResults,
    PerformanceMetrics, get_session
)
from config.settings import SIMULATION_CONFIG


class MetricCategory(Enum):
    """Categories of performance metrics"""
    COST = "cost"
    SERVICE = "service"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"


@dataclass
class KPI:
    """Key Performance Indicator definition"""
    name: str
    value: float
    target: Optional[float] = None
    unit: str = ""
    category: MetricCategory = MetricCategory.EFFICIENCY
    description: str = ""
    
    @property
    def performance_ratio(self) -> Optional[float]:
        """Calculate performance as ratio to target"""
        if self.target is None or self.target == 0:
            return None
        return self.value / self.target
    
    @property
    def status(self) -> str:
        """Get performance status"""
        if self.target is None:
            return "No Target"
        
        ratio = self.performance_ratio
        if ratio >= 1.0:
            return "✅ On Target"
        elif ratio >= 0.9:
            return "⚠️ Near Target"
        else:
            return "❌ Below Target"


class PerformanceCalculator:
    """Calculate various performance metrics"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def calculate_service_level_metrics(self, days: int = 30) -> Dict[str, KPI]:
        """Calculate service level related metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Overall service level
        demand_data = self.session.query(
            func.sum(Demand.quantity_demanded).label("total_demand"),
            func.sum(Demand.quantity_fulfilled).label("total_fulfilled")
        ).filter(
            Demand.date >= start_date,
            Demand.is_forecast == False
        ).first()
        
        overall_service_level = 0.0
        if demand_data.total_demand and demand_data.total_demand > 0:
            overall_service_level = demand_data.total_fulfilled / demand_data.total_demand
        
        # Stockout frequency
        stockout_days = self.session.query(func.count(func.distinct(Demand.date))).filter(
            Demand.date >= start_date,
            Demand.quantity_fulfilled < Demand.quantity_demanded,
            Demand.is_forecast == False
        ).scalar()
        
        total_days = min(days, (datetime.utcnow() - start_date).days)
        stockout_frequency = stockout_days / max(total_days, 1)
        
        # Fill rate by product category
        category_service = {}
        products = self.session.query(Product).all()
        
        for category in set(p.category for p in products):
            category_demand = self.session.query(
                func.sum(Demand.quantity_demanded).label("cat_demand"),
                func.sum(Demand.quantity_fulfilled).label("cat_fulfilled")
            ).join(Product).filter(
                Product.category == category,
                Demand.date >= start_date,
                Demand.is_forecast == False
            ).first()
            
            if category_demand.cat_demand and category_demand.cat_demand > 0:
                category_service[category] = category_demand.cat_fulfilled / category_demand.cat_demand
            else:
                category_service[category] = 0.0
        
        return {
            "overall_service_level": KPI(
                name="Overall Service Level",
                value=overall_service_level,
                target=SIMULATION_CONFIG["service_level_target"],
                unit="%",
                category=MetricCategory.SERVICE,
                description="Percentage of demand fulfilled"
            ),
            "stockout_frequency": KPI(
                name="Stockout Frequency",
                value=stockout_frequency,
                target=0.05,  # Target: less than 5% of days with stockouts
                unit="%",
                category=MetricCategory.SERVICE,
                description="Percentage of days with stockouts"
            ),
            "avg_category_service": KPI(
                name="Average Category Service Level",
                value=np.mean(list(category_service.values())) if category_service else 0,
                target=SIMULATION_CONFIG["service_level_target"],
                unit="%",
                category=MetricCategory.SERVICE,
                description="Average service level across product categories"
            )
        }
    
    def calculate_cost_metrics(self, days: int = 30) -> Dict[str, KPI]:
        """Calculate cost-related metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total inventory costs
        total_cost = self.session.query(func.sum(InventoryActions.cost)).filter(
            InventoryActions.timestamp >= start_date
        ).scalar() or 0.0
        
        # Number of orders
        total_orders = self.session.query(func.count(InventoryActions.id)).filter(
            InventoryActions.timestamp >= start_date,
            InventoryActions.action_type == "order"
        ).scalar() or 0
        
        # Average order cost
        avg_order_cost = total_cost / max(total_orders, 1)
        
        # Cost per unit fulfilled
        total_fulfilled = self.session.query(func.sum(Demand.quantity_fulfilled)).filter(
            Demand.date >= start_date,
            Demand.is_forecast == False
        ).scalar() or 1
        
        cost_per_unit = total_cost / max(total_fulfilled, 1)
        
        # Holding cost estimation (simplified)
        current_inventory_value = 0.0
        latest_inventory = self.session.query(Inventory).filter(
            Inventory.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).all()
        
        for inv in latest_inventory:
            product = self.session.query(Product).filter(Product.product_id == inv.product_id).first()
            if product:
                current_inventory_value += inv.stock_level * product.unit_cost
        
        daily_holding_cost = current_inventory_value * (SIMULATION_CONFIG["holding_cost_rate"] / 365)
        
        return {
            "total_cost": KPI(
                name="Total Inventory Cost",
                value=total_cost,
                unit="$",
                category=MetricCategory.COST,
                description=f"Total inventory costs over {days} days"
            ),
            "avg_order_cost": KPI(
                name="Average Order Cost",
                value=avg_order_cost,
                target=500.0,  # Target average order cost
                unit="$",
                category=MetricCategory.COST,
                description="Average cost per order placed"
            ),
            "cost_per_unit": KPI(
                name="Cost per Unit Fulfilled",
                value=cost_per_unit,
                target=2.0,  # Target cost per unit
                unit="$/unit",
                category=MetricCategory.COST,
                description="Total cost divided by units fulfilled"
            ),
            "daily_holding_cost": KPI(
                name="Daily Holding Cost",
                value=daily_holding_cost,
                unit="$/day",
                category=MetricCategory.COST,
                description="Estimated daily holding cost"
            )
        }
    
    def calculate_efficiency_metrics(self, days: int = 30) -> Dict[str, KPI]:
        """Calculate efficiency-related metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Inventory turnover
        total_fulfilled = self.session.query(func.sum(Demand.quantity_fulfilled)).filter(
            Demand.date >= start_date,
            Demand.is_forecast == False
        ).scalar() or 0
        
        # Average inventory level
        avg_inventory = self.session.query(func.avg(Inventory.stock_level)).filter(
            Inventory.timestamp >= start_date
        ).scalar() or 1
        
        inventory_turnover = (total_fulfilled / max(avg_inventory, 1)) * (365 / days)  # Annualized
        
        # Order frequency
        total_orders = self.session.query(func.count(InventoryActions.id)).filter(
            InventoryActions.timestamp >= start_date,
            InventoryActions.action_type == "order"
        ).scalar() or 0
        
        order_frequency = total_orders / max(days, 1)  # Orders per day
        
        # Optimization efficiency (convergence speed)
        recent_optimizations = self.session.query(OptimizationResults).filter(
            OptimizationResults.timestamp >= start_date
        ).all()
        
        avg_iterations = 0.0
        if recent_optimizations:
            iterations = [opt.convergence_iterations for opt in recent_optimizations 
                         if opt.convergence_iterations is not None]
            avg_iterations = np.mean(iterations) if iterations else 0.0
        
        # Forecast accuracy (simplified)
        forecast_accuracy = self._calculate_forecast_accuracy(days)
        
        return {
            "inventory_turnover": KPI(
                name="Inventory Turnover",
                value=inventory_turnover,
                target=12.0,  # Target: 12 turns per year
                unit="turns/year",
                category=MetricCategory.EFFICIENCY,
                description="How many times inventory is sold per year"
            ),
            "order_frequency": KPI(
                name="Order Frequency",
                value=order_frequency,
                target=0.5,  # Target: 0.5 orders per day
                unit="orders/day",
                category=MetricCategory.EFFICIENCY,
                description="Average number of orders placed per day"
            ),
            "optimization_efficiency": KPI(
                name="Optimization Convergence",
                value=avg_iterations,
                target=25.0,  # Target: converge within 25 iterations
                unit="iterations",
                category=MetricCategory.EFFICIENCY,
                description="Average iterations to convergence"
            ),
            "forecast_accuracy": KPI(
                name="Forecast Accuracy",
                value=forecast_accuracy,
                target=0.85,  # Target: 85% accuracy
                unit="%",
                category=MetricCategory.EFFICIENCY,
                description="Accuracy of demand forecasts"
            )
        }
    
    def _calculate_forecast_accuracy(self, days: int) -> float:
        """Calculate forecast accuracy (simplified implementation)"""
        # This is a simplified implementation
        # In practice, you'd compare forecasts with actual demand
        
        # Get recent forecasts and actual demand
        start_date = datetime.utcnow() - timedelta(days=days)
        
        forecasts = self.session.query(Demand).filter(
            Demand.date >= start_date,
            Demand.date <= datetime.utcnow(),
            Demand.is_forecast == True
        ).all()
        
        if not forecasts:
            return 0.0
        
        accuracy_scores = []
        
        for forecast in forecasts:
            # Find corresponding actual demand
            actual = self.session.query(Demand).filter(
                Demand.product_id == forecast.product_id,
                Demand.date == forecast.date,
                Demand.is_forecast == False
            ).first()
            
            if actual:
                # Calculate MAPE (Mean Absolute Percentage Error)
                if actual.quantity_demanded > 0:
                    error = abs(forecast.quantity_demanded - actual.quantity_demanded) / actual.quantity_demanded
                    accuracy = max(0, 1 - error)  # Convert error to accuracy
                    accuracy_scores.append(accuracy)
        
        return np.mean(accuracy_scores) if accuracy_scores else 0.0
    
    def calculate_quality_metrics(self, days: int = 30) -> Dict[str, KPI]:
        """Calculate data quality and system reliability metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Data completeness
        total_products = self.session.query(func.count(Product.product_id)).scalar()
        products_with_recent_demand = self.session.query(
            func.count(func.distinct(Demand.product_id))
        ).filter(
            Demand.date >= start_date,
            Demand.is_forecast == False
        ).scalar()
        
        data_completeness = products_with_recent_demand / max(total_products, 1)
        
        # Optimization success rate
        total_optimizations = self.session.query(func.count(OptimizationResults.run_id)).filter(
            OptimizationResults.timestamp >= start_date
        ).scalar()
        
        successful_optimizations = self.session.query(func.count(OptimizationResults.run_id)).filter(
            OptimizationResults.timestamp >= start_date,
            OptimizationResults.constraints_satisfied == True
        ).scalar()
        
        optimization_success_rate = successful_optimizations / max(total_optimizations, 1)
        
        # System uptime (simplified - based on recent activity)
        recent_activity = self.session.query(func.count(PerformanceMetrics.id)).filter(
            PerformanceMetrics.timestamp >= start_date
        ).scalar()
        
        expected_activity = days * 24  # Assuming hourly metrics
        system_uptime = min(1.0, recent_activity / max(expected_activity, 1))
        
        return {
            "data_completeness": KPI(
                name="Data Completeness",
                value=data_completeness,
                target=0.95,  # Target: 95% of products have recent data
                unit="%",
                category=MetricCategory.QUALITY,
                description="Percentage of products with recent demand data"
            ),
            "optimization_success_rate": KPI(
                name="Optimization Success Rate",
                value=optimization_success_rate,
                target=0.98,  # Target: 98% success rate
                unit="%",
                category=MetricCategory.QUALITY,
                description="Percentage of successful optimization runs"
            ),
            "system_uptime": KPI(
                name="System Uptime",
                value=system_uptime,
                target=0.99,  # Target: 99% uptime
                unit="%",
                category=MetricCategory.QUALITY,
                description="System availability and reliability"
            )
        }


class PerformanceDashboard:
    """Generate comprehensive performance dashboards"""
    
    def __init__(self, session: Session):
        self.session = session
        self.calculator = PerformanceCalculator(session)
        self.logger = logging.getLogger(__name__)
    
    def generate_kpi_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive KPI dashboard"""
        self.logger.info(f"Generating KPI dashboard for {days} days")
        
        # Calculate all metric categories
        service_metrics = self.calculator.calculate_service_level_metrics(days)
        cost_metrics = self.calculator.calculate_cost_metrics(days)
        efficiency_metrics = self.calculator.calculate_efficiency_metrics(days)
        quality_metrics = self.calculator.calculate_quality_metrics(days)
        
        # Combine all metrics
        all_metrics = {
            **service_metrics,
            **cost_metrics,
            **efficiency_metrics,
            **quality_metrics
        }
        
        # Calculate overall performance score
        performance_scores = []
        for kpi in all_metrics.values():
            if kpi.performance_ratio is not None:
                performance_scores.append(min(1.0, kpi.performance_ratio))
        
        overall_score = np.mean(performance_scores) if performance_scores else 0.0
        
        # Categorize metrics
        categorized_metrics = {}
        for category in MetricCategory:
            categorized_metrics[category.value] = {
                name: kpi for name, kpi in all_metrics.items()
                if kpi.category == category
            }
        
        # Identify top performers and improvement areas
        on_target = [name for name, kpi in all_metrics.items() if "On Target" in kpi.status]
        needs_improvement = [name for name, kpi in all_metrics.items() if "Below Target" in kpi.status]
        
        dashboard = {
            "generated_at": datetime.utcnow(),
            "period_days": days,
            "overall_performance_score": overall_score,
            "metrics_by_category": categorized_metrics,
            "all_metrics": all_metrics,
            "summary": {
                "total_metrics": len(all_metrics),
                "on_target": len(on_target),
                "needs_improvement": len(needs_improvement),
                "performance_score": overall_score
            },
            "top_performers": on_target,
            "improvement_areas": needs_improvement
        }
        
        return dashboard
    
    def generate_trend_analysis(self, days: int = 90) -> Dict[str, Any]:
        """Generate trend analysis over time"""
        self.logger.info(f"Generating trend analysis for {days} days")
        
        # Calculate metrics for different time periods
        periods = [7, 14, 30, days]
        trend_data = {}
        
        for period in periods:
            if period <= days:
                metrics = {
                    **self.calculator.calculate_service_level_metrics(period),
                    **self.calculator.calculate_cost_metrics(period),
                    **self.calculator.calculate_efficiency_metrics(period)
                }
                
                trend_data[f"{period}_days"] = {
                    name: kpi.value for name, kpi in metrics.items()
                }
        
        # Calculate trends (simple linear trend)
        trends = {}
        for metric_name in trend_data[f"{periods[0]}_days"].keys():
            values = []
            time_points = []
            
            for i, period in enumerate(periods):
                if f"{period}_days" in trend_data and metric_name in trend_data[f"{period}_days"]:
                    values.append(trend_data[f"{period}_days"][metric_name])
                    time_points.append(period)
            
            if len(values) >= 2:
                # Calculate simple trend (positive = improving, negative = declining)
                trend_slope = np.polyfit(time_points, values, 1)[0]
                trends[metric_name] = {
                    "slope": trend_slope,
                    "direction": "improving" if trend_slope > 0 else "declining" if trend_slope < 0 else "stable",
                    "values": dict(zip([f"{p}_days" for p in periods], values))
                }
        
        return {
            "generated_at": datetime.utcnow(),
            "analysis_period_days": days,
            "trend_data": trend_data,
            "trends": trends,
            "improving_metrics": [name for name, trend in trends.items() if trend["direction"] == "improving"],
            "declining_metrics": [name for name, trend in trends.items() if trend["direction"] == "declining"]
        }
    
    def generate_comparative_analysis(self, baseline_days: int = 30, comparison_days: int = 30) -> Dict[str, Any]:
        """Compare performance between two time periods"""
        self.logger.info(f"Generating comparative analysis: {baseline_days} vs {comparison_days} days")
        
        # Calculate metrics for baseline period
        baseline_start = datetime.utcnow() - timedelta(days=baseline_days + comparison_days)
        baseline_end = datetime.utcnow() - timedelta(days=comparison_days)
        
        # Calculate metrics for comparison period (recent)
        comparison_start = datetime.utcnow() - timedelta(days=comparison_days)
        
        # This is a simplified implementation
        # In practice, you'd modify the calculator to accept date ranges
        
        baseline_metrics = {
            **self.calculator.calculate_service_level_metrics(baseline_days),
            **self.calculator.calculate_cost_metrics(baseline_days),
            **self.calculator.calculate_efficiency_metrics(baseline_days)
        }
        
        comparison_metrics = {
            **self.calculator.calculate_service_level_metrics(comparison_days),
            **self.calculator.calculate_cost_metrics(comparison_days),
            **self.calculator.calculate_efficiency_metrics(comparison_days)
        }
        
        # Calculate improvements/deteriorations
        comparisons = {}
        for metric_name in baseline_metrics.keys():
            if metric_name in comparison_metrics:
                baseline_value = baseline_metrics[metric_name].value
                comparison_value = comparison_metrics[metric_name].value
                
                if baseline_value != 0:
                    change_percent = ((comparison_value - baseline_value) / baseline_value) * 100
                else:
                    change_percent = 0
                
                comparisons[metric_name] = {
                    "baseline_value": baseline_value,
                    "comparison_value": comparison_value,
                    "absolute_change": comparison_value - baseline_value,
                    "percent_change": change_percent,
                    "improvement": change_percent > 0
                }
        
        # Identify significant changes
        significant_improvements = {
            name: comp for name, comp in comparisons.items()
            if comp["improvement"] and abs(comp["percent_change"]) > 5
        }
        
        significant_deteriorations = {
            name: comp for name, comp in comparisons.items()
            if not comp["improvement"] and abs(comp["percent_change"]) > 5
        }
        
        return {
            "generated_at": datetime.utcnow(),
            "baseline_period_days": baseline_days,
            "comparison_period_days": comparison_days,
            "baseline_metrics": baseline_metrics,
            "comparison_metrics": comparison_metrics,
            "comparisons": comparisons,
            "significant_improvements": significant_improvements,
            "significant_deteriorations": significant_deteriorations,
            "overall_improvement": len(significant_improvements) > len(significant_deteriorations)
        }


class AlertSystem:
    """Monitor metrics and generate alerts"""
    
    def __init__(self, session: Session):
        self.session = session
        self.calculator = PerformanceCalculator(session)
        self.logger = logging.getLogger(__name__)
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        
        # Get current metrics
        service_metrics = self.calculator.calculate_service_level_metrics(7)  # Last week
        cost_metrics = self.calculator.calculate_cost_metrics(7)
        efficiency_metrics = self.calculator.calculate_efficiency_metrics(7)
        
        all_metrics = {**service_metrics, **cost_metrics, **efficiency_metrics}
        
        # Check each metric against thresholds
        for name, kpi in all_metrics.items():
            if kpi.target is not None:
                performance_ratio = kpi.performance_ratio
                
                if performance_ratio is not None:
                    # Critical alert: performance < 70% of target
                    if performance_ratio < 0.7:
                        alerts.append({
                            "level": "CRITICAL",
                            "metric": name,
                            "value": kpi.value,
                            "target": kpi.target,
                            "performance_ratio": performance_ratio,
                            "message": f"{name} is critically below target ({kpi.value:.2f} vs {kpi.target:.2f})",
                            "timestamp": datetime.utcnow()
                        })
                    
                    # Warning alert: performance < 90% of target
                    elif performance_ratio < 0.9:
                        alerts.append({
                            "level": "WARNING",
                            "metric": name,
                            "value": kpi.value,
                            "target": kpi.target,
                            "performance_ratio": performance_ratio,
                            "message": f"{name} is below target ({kpi.value:.2f} vs {kpi.target:.2f})",
                            "timestamp": datetime.utcnow()
                        })
        
        # Check for system-specific alerts
        system_alerts = self._check_system_alerts()
        alerts.extend(system_alerts)
        
        return alerts
    
    def _check_system_alerts(self) -> List[Dict[str, Any]]:
        """Check for system-specific alert conditions"""
        alerts = []
        
        # Check for recent optimization failures
        recent_failures = self.session.query(OptimizationResults).filter(
            OptimizationResults.timestamp >= datetime.utcnow() - timedelta(hours=24),
            OptimizationResults.constraints_satisfied == False
        ).count()
        
        if recent_failures > 0:
            alerts.append({
                "level": "WARNING",
                "metric": "optimization_failures",
                "value": recent_failures,
                "message": f"{recent_failures} optimization failures in the last 24 hours",
                "timestamp": datetime.utcnow()
            })
        
        # Check for data staleness
        latest_demand = self.session.query(func.max(Demand.date)).filter(
            Demand.is_forecast == False
        ).scalar()
        
        if latest_demand and (datetime.utcnow().date() - latest_demand.date()).days > 2:
            alerts.append({
                "level": "WARNING",
                "metric": "data_staleness",
                "value": (datetime.utcnow().date() - latest_demand.date()).days,
                "message": f"Demand data is {(datetime.utcnow().date() - latest_demand.date()).days} days old",
                "timestamp": datetime.utcnow()
            })
        
        return alerts


def main():
    """Test performance metrics"""
    from config.settings import DATABASE_URL
    from ..data.models import create_database
    
    engine = create_database(DATABASE_URL)
    session = get_session(engine)
    
    # Test performance calculator
    calculator = PerformanceCalculator(session)
    
    service_metrics = calculator.calculate_service_level_metrics(30)
    print("Service Metrics:")
    for name, kpi in service_metrics.items():
        print(f"  {name}: {kpi.value:.3f} {kpi.unit} ({kpi.status})")
    
    # Test dashboard
    dashboard = PerformanceDashboard(session)
    kpi_dashboard = dashboard.generate_kpi_dashboard(30)
    
    print(f"\nOverall Performance Score: {kpi_dashboard['overall_performance_score']:.3f}")
    print(f"Metrics on target: {len(kpi_dashboard['top_performers'])}")
    print(f"Metrics needing improvement: {len(kpi_dashboard['improvement_areas'])}")
    
    # Test alerts
    alert_system = AlertSystem(session)
    alerts = alert_system.check_alerts()
    
    print(f"\nActive alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  {alert['level']}: {alert['message']}")
    
    session.close()


if __name__ == "__main__":
    main()