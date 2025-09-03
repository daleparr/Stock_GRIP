"""
Live Data Optimizer for Stock GRIP
Integrates live Weld data with GP-EIMS and MPC-RL-MOBO
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Optional

class LiveDataOptimizer:
    """Stock GRIP optimizer using live Weld data"""
    
    def __init__(self, live_data_processor):
        self.processor = live_data_processor
        self.gp_data = None
        self.mpc_data = None
        self.optimization_results = {}
        self.logger = logging.getLogger(__name__)
        
    def initialize_optimization_data(self) -> bool:
        """Initialize data for both optimization algorithms"""
        try:
            # Prepare data for GP-EIMS
            self.gp_data = self.processor.prepare_for_gp_eims()
            self.logger.info(f"GP-EIMS data prepared: {len(self.gp_data)} products")
            
            # Prepare data for MPC-RL-MOBO
            self.mpc_data = self.processor.prepare_for_mpc_rl_mobo()
            self.logger.info(f"MPC-RL-MOBO data prepared: {len(self.mpc_data)} products")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing optimization data: {str(e)}")
            return False
    
    def run_gp_eims_optimization(self) -> Dict[str, Any]:
        """Run GP-EIMS strategic optimization"""
        if self.gp_data is None:
            raise ValueError("GP-EIMS data not initialized")
        
        # Simplified GP-EIMS implementation for live data
        results = {}
        
        for _, product in self.gp_data.iterrows():
            product_id = product['product_id']
            
            # Expected Improvement calculation
            current_performance = product['current_performance']
            demand_potential = product['demand_velocity'] * (1 + product['marketing_efficiency'])
            
            # Strategic recommendations based on live data patterns
            if product['high_performer'] and product['marketing_driven']:
                recommendation = "increase_marketing_investment"
                priority = "high"
            elif product['demand_velocity'] > 2 and product['organic_ratio'] > 0.7:
                recommendation = "maintain_organic_focus"
                priority = "medium"
            elif product['marketing_efficiency'] > 2.0:
                recommendation = "scale_marketing"
                priority = "high"
            else:
                recommendation = "optimize_or_discontinue"
                priority = "low"
            
            # Calculate confidence based on data quality
            confidence = 0.9 if product['high_performer'] else 0.7
            if product['demand_velocity'] == 0:
                confidence = 0.3
            
            results[product_id] = {
                'product_name': product['product_name'],
                'category': product['category_clean'],
                'current_performance': float(current_performance),
                'demand_potential': float(demand_potential),
                'recommendation': recommendation,
                'priority': priority,
                'expected_improvement': float(demand_potential - current_performance),
                'confidence': confidence,
                'demand_velocity': int(product['demand_velocity']),
                'revenue': float(product['revenue']),
                'marketing_efficiency': float(product['marketing_efficiency'])
            }
        
        self.optimization_results['gp_eims'] = results
        return results
    
    def run_mpc_rl_mobo_optimization(self) -> Dict[str, Any]:
        """Run MPC-RL-MOBO tactical optimization"""
        if self.mpc_data is None:
            raise ValueError("MPC-RL-MOBO data not initialized")
        
        # Simplified MPC-RL-MOBO implementation
        results = {}
        
        for _, product in self.mpc_data.iterrows():
            product_id = product['product_id']
            
            # Multi-objective optimization scores
            profit_score = min(product['profit_objective'] / max(self.mpc_data['profit_objective'].max(), 1), 1.0)
            service_score = min(product['inventory_level'] / max(product['demand_forecast'], 1), 1.0)
            cost_efficiency = max(0, 1 - (product['cost_objective'] / max(product['revenue'], 1)))
            
            # Tactical decisions based on inventory and demand
            if product['inventory_level'] < product['reorder_point']:
                action = "immediate_reorder"
                urgency = "high"
            elif product['demand_forecast'] > product['inventory_level'] * 0.5:
                action = "increase_stock"
                urgency = "medium"
            elif service_score > 0.95 and cost_efficiency > 0.7:
                action = "maintain_current"
                urgency = "low"
            else:
                action = "optimize_inventory"
                urgency = "medium"
            
            # Calculate recommended stock level
            safety_factor = 1.5 if product['demand_forecast'] > 0 else 1.0
            recommended_stock = max(
                product['demand_forecast'] * 7 * safety_factor,  # 7 days stock with safety
                product['reorder_point']
            )
            
            results[product_id] = {
                'profit_score': float(profit_score),
                'service_score': float(service_score),
                'cost_efficiency': float(cost_efficiency),
                'action': action,
                'urgency': urgency,
                'recommended_stock_level': float(recommended_stock),
                'current_inventory': float(product['inventory_level']),
                'demand_forecast': float(product['demand_forecast']),
                'optimization_confidence': float((profit_score + service_score + cost_efficiency) / 3)
            }
        
        self.optimization_results['mpc_rl_mobo'] = results
        return results
    
    def generate_unified_recommendations(self) -> Dict[str, Any]:
        """Generate unified recommendations from both algorithms"""
        if not self.optimization_results:
            raise ValueError("No optimization results available")
        
        gp_results = self.optimization_results.get('gp_eims', {})
        mpc_results = self.optimization_results.get('mpc_rl_mobo', {})
        
        unified = {}
        
        for product_id in set(list(gp_results.keys()) + list(mpc_results.keys())):
            gp_rec = gp_results.get(product_id, {})
            mpc_rec = mpc_results.get(product_id, {})
            
            # Combine strategic and tactical recommendations
            unified[product_id] = {
                'product_name': gp_rec.get('product_name', 'Unknown'),
                'category': gp_rec.get('category', 'other'),
                'strategic_recommendation': gp_rec.get('recommendation', 'unknown'),
                'tactical_action': mpc_rec.get('action', 'unknown'),
                'priority': gp_rec.get('priority', 'low'),
                'urgency': mpc_rec.get('urgency', 'low'),
                'expected_improvement': gp_rec.get('expected_improvement', 0),
                'recommended_stock_level': mpc_rec.get('recommended_stock_level', 0),
                'current_performance': gp_rec.get('current_performance', 0),
                'demand_velocity': gp_rec.get('demand_velocity', 0),
                'revenue': gp_rec.get('revenue', 0),
                'overall_confidence': (
                    gp_rec.get('confidence', 0) + mpc_rec.get('optimization_confidence', 0)
                ) / 2
            }
        
        return unified
    
    def get_portfolio_insights(self) -> Dict[str, Any]:
        """Generate portfolio-level insights"""
        summary = self.processor.get_optimization_summary()
        
        insights = {
            'portfolio_health': {
                'total_products': summary['total_products'],
                'high_performers': summary['high_performers'],
                'performance_rate': summary['high_performers'] / max(summary['total_products'], 1)
            },
            'revenue_analysis': {
                'total_revenue': summary['total_revenue'],
                'organic_share': summary['organic_revenue_share'],
                'marketing_roas': summary['overall_marketing_roas'],
                'avg_unit_price': summary['avg_unit_price']
            },
            'channel_effectiveness': {
                'email_responsive_rate': summary['email_responsive_products'] / max(summary['total_products'], 1),
                'marketing_driven_rate': summary['marketing_driven_products'] / max(summary['total_products'], 1),
                'total_marketing_spend': summary['total_marketing_spend']
            },
            'category_performance': summary['top_categories'],
            'demand_distribution': summary['demand_distribution'],
            'optimization_summary': {
                'gp_eims_products': len(self.optimization_results.get('gp_eims', {})),
                'mpc_rl_mobo_products': len(self.optimization_results.get('mpc_rl_mobo', {})),
                'total_expected_improvement': sum([
                    result.get('expected_improvement', 0) 
                    for result in self.optimization_results.get('gp_eims', {}).values()
                ])
            }
        }
        
        return insights
    
    def get_top_recommendations(self, limit: int = 5) -> Dict[str, Any]:
        """Get top recommendations sorted by priority and expected improvement"""
        if not self.optimization_results:
            return {}
        
        unified = self.generate_unified_recommendations()
        
        # Sort by expected improvement and confidence
        sorted_products = sorted(
            unified.items(),
            key=lambda x: (
                x[1]['expected_improvement'] * x[1]['overall_confidence']
            ),
            reverse=True
        )
        
        top_recommendations = {}
        for product_id, rec in sorted_products[:limit]:
            top_recommendations[product_id] = rec
        
        return top_recommendations
    
    def export_optimization_results(self) -> pd.DataFrame:
        """Export optimization results as DataFrame for further analysis"""
        if not self.optimization_results:
            return pd.DataFrame()
        
        unified = self.generate_unified_recommendations()
        
        # Convert to DataFrame
        df = pd.DataFrame.from_dict(unified, orient='index')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'product_id'}, inplace=True)
        
        # Add timestamp
        df['optimization_timestamp'] = datetime.now()
        
        return df