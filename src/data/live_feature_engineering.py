"""
Feature Engineering for Live Data Integration
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .models import Product, Inventory, Demand, get_session
from .live_data_models import LiveSalesData, LiveInventoryUpdate, LiveDemandSignals
from config.settings import DATABASE_URL


class LiveFeatureEngineer:
    """Feature engineering for live data streams"""
    
    def __init__(self, database_session: Session):
        self.session = database_session
        self.logger = logging.getLogger(__name__)
    
    def calculate_demand_velocity_features(self, product_id: str, 
                                         lookback_days: int = 30) -> Dict[str, float]:
        """Calculate demand velocity and trend features"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get live sales data
        sales_data = self.session.query(LiveSalesData).filter(
            and_(
                LiveSalesData.product_id == product_id,
                LiveSalesData.date >= start_date,
                LiveSalesData.date <= end_date
            )
        ).order_by(LiveSalesData.date).all()
        
        if not sales_data:
            return self._get_default_velocity_features()
        
        # Convert to daily aggregates
        daily_sales = {}
        for sale in sales_data:
            date_key = sale.date.date()
            if date_key not in daily_sales:
                daily_sales[date_key] = {'quantity': 0, 'revenue': 0, 'transactions': 0}
            
            daily_sales[date_key]['quantity'] += sale.quantity_sold
            daily_sales[date_key]['revenue'] += sale.revenue
            daily_sales[date_key]['transactions'] += 1
        
        # Create time series
        dates = sorted(daily_sales.keys())
        quantities = [daily_sales[date]['quantity'] for date in dates]
        revenues = [daily_sales[date]['revenue'] for date in dates]
        
        # Calculate features
        features = {
            'avg_daily_quantity': np.mean(quantities),
            'std_daily_quantity': np.std(quantities),
            'max_daily_quantity': np.max(quantities),
            'min_daily_quantity': np.min(quantities),
            'avg_daily_revenue': np.mean(revenues),
            'quantity_trend': self._calculate_trend(quantities),
            'revenue_trend': self._calculate_trend(revenues),
            'demand_volatility': np.std(quantities) / max(np.mean(quantities), 1),
            'revenue_per_unit': np.mean(revenues) / max(np.mean(quantities), 1),
            'days_with_sales': len([q for q in quantities if q > 0]),
            'sales_frequency': len([q for q in quantities if q > 0]) / len(quantities),
            'quantity_acceleration': self._calculate_acceleration(quantities),
            'peak_to_trough_ratio': np.max(quantities) / max(np.min(quantities), 1)
        }
        
        return features
    
    def calculate_channel_performance_features(self, product_id: str,
                                             lookback_days: int = 30) -> Dict[str, float]:
        """Calculate channel-specific performance features"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get sales by channel
        channel_data = self.session.query(
            LiveSalesData.channel,
            func.sum(LiveSalesData.quantity_sold).label('total_quantity'),
            func.sum(LiveSalesData.revenue).label('total_revenue'),
            func.count(LiveSalesData.id).label('transaction_count'),
            func.avg(LiveSalesData.quantity_sold).label('avg_quantity'),
            func.avg(LiveSalesData.revenue).label('avg_revenue')
        ).filter(
            and_(
                LiveSalesData.product_id == product_id,
                LiveSalesData.date >= start_date,
                LiveSalesData.date <= end_date
            )
        ).group_by(LiveSalesData.channel).all()
        
        if not channel_data:
            return self._get_default_channel_features()
        
        # Calculate channel features
        total_quantity = sum(row.total_quantity for row in channel_data)
        total_revenue = sum(row.total_revenue for row in channel_data)
        
        features = {
            'channel_count': len(channel_data),
            'channel_diversity': len(channel_data) / 4.0,  # Normalize by max expected channels
            'dominant_channel_share': max(row.total_quantity for row in channel_data) / max(total_quantity, 1),
            'online_share': 0.0,
            'pos_share': 0.0,
            'marketplace_share': 0.0,
            'wholesale_share': 0.0,
            'channel_revenue_efficiency': 0.0
        }
        
        # Calculate channel-specific shares
        for row in channel_data:
            share = row.total_quantity / max(total_quantity, 1)
            if row.channel == 'online':
                features['online_share'] = share
            elif row.channel == 'pos':
                features['pos_share'] = share
            elif row.channel == 'marketplace':
                features['marketplace_share'] = share
            elif row.channel == 'wholesale':
                features['wholesale_share'] = share
        
        # Calculate revenue efficiency (revenue per transaction)
        if channel_data:
            features['channel_revenue_efficiency'] = total_revenue / sum(row.transaction_count for row in channel_data)
        
        return features
    
    def calculate_inventory_health_features(self, product_id: str) -> Dict[str, float]:
        """Calculate inventory health and availability features"""
        # Get latest inventory updates
        latest_inventory = self.session.query(LiveInventoryUpdate).filter(
            LiveInventoryUpdate.product_id == product_id
        ).order_by(LiveInventoryUpdate.date.desc()).limit(10).all()
        
        if not latest_inventory:
            return self._get_default_inventory_features()
        
        # Get current state
        current = latest_inventory[0]
        
        # Calculate historical trends if we have enough data
        stock_levels = [inv.stock_level for inv in latest_inventory]
        available_stock = [inv.stock_level - inv.reserved_stock for inv in latest_inventory]
        
        features = {
            'current_stock_level': current.stock_level,
            'current_available_stock': current.stock_level - current.reserved_stock,
            'current_reserved_ratio': current.reserved_stock / max(current.stock_level, 1),
            'current_in_transit': current.in_transit,
            'stock_trend': self._calculate_trend(stock_levels) if len(stock_levels) > 2 else 0.0,
            'stock_volatility': np.std(stock_levels) / max(np.mean(stock_levels), 1),
            'avg_stock_level': np.mean(stock_levels),
            'min_stock_level': np.min(stock_levels),
            'max_stock_level': np.max(stock_levels),
            'stock_range_ratio': (np.max(stock_levels) - np.min(stock_levels)) / max(np.mean(stock_levels), 1),
            'availability_ratio': np.mean(available_stock) / max(np.mean(stock_levels), 1),
            'stockout_risk': 1.0 if current.stock_level <= current.reserved_stock else 0.0
        }
        
        return features
    
    def calculate_market_sentiment_features(self, product_id: str,
                                          lookback_days: int = 30) -> Dict[str, float]:
        """Calculate market sentiment and external demand features"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get demand signals
        demand_signals = self.session.query(LiveDemandSignals).filter(
            and_(
                LiveDemandSignals.product_id == product_id,
                LiveDemandSignals.date >= start_date,
                LiveDemandSignals.date <= end_date
            )
        ).order_by(LiveDemandSignals.date.desc()).all()
        
        if not demand_signals:
            return self._get_default_sentiment_features()
        
        # Extract sentiment data
        market_trends = [signal.market_trend for signal in demand_signals if signal.market_trend is not None]
        social_sentiments = [signal.social_sentiment for signal in demand_signals if signal.social_sentiment is not None]
        competitor_prices = [signal.competitor_price for signal in demand_signals if signal.competitor_price is not None]
        
        # Count categorical features
        demand_levels = [signal.external_demand for signal in demand_signals]
        high_demand_days = len([d for d in demand_levels if d == 'high'])
        medium_demand_days = len([d for d in demand_levels if d == 'medium'])
        low_demand_days = len([d for d in demand_levels if d == 'low'])
        
        weather_factors = [signal.weather_factor for signal in demand_signals]
        event_impacts = [signal.event_impact for signal in demand_signals]
        
        features = {
            'avg_market_trend': np.mean(market_trends) if market_trends else 0.0,
            'market_trend_volatility': np.std(market_trends) if len(market_trends) > 1 else 0.0,
            'market_trend_direction': self._calculate_trend(market_trends) if len(market_trends) > 2 else 0.0,
            'avg_social_sentiment': np.mean(social_sentiments) if social_sentiments else 0.0,
            'sentiment_volatility': np.std(social_sentiments) if len(social_sentiments) > 1 else 0.0,
            'high_demand_ratio': high_demand_days / max(len(demand_levels), 1),
            'medium_demand_ratio': medium_demand_days / max(len(demand_levels), 1),
            'low_demand_ratio': low_demand_days / max(len(demand_levels), 1),
            'avg_competitor_price': np.mean(competitor_prices) if competitor_prices else 0.0,
            'competitor_price_trend': self._calculate_trend(competitor_prices) if len(competitor_prices) > 2 else 0.0,
            'weather_diversity': len(set(weather_factors)) / max(len(weather_factors), 1),
            'event_impact_frequency': len([e for e in event_impacts if e != 'none']) / max(len(event_impacts), 1)
        }
        
        return features
    
    def calculate_seasonality_features(self, product_id: str) -> Dict[str, float]:
        """Calculate seasonality and temporal features"""
        current_date = datetime.utcnow()
        
        # Basic temporal features
        features = {
            'day_of_week': current_date.weekday(),
            'day_of_month': current_date.day,
            'day_of_year': current_date.timetuple().tm_yday,
            'week_of_year': current_date.isocalendar()[1],
            'month': current_date.month,
            'quarter': (current_date.month - 1) // 3 + 1,
            'is_weekend': 1.0 if current_date.weekday() >= 5 else 0.0,
            'is_month_start': 1.0 if current_date.day <= 7 else 0.0,
            'is_month_end': 1.0 if current_date.day >= 24 else 0.0,
            'is_quarter_start': 1.0 if current_date.month in [1, 4, 7, 10] and current_date.day <= 7 else 0.0,
            'is_quarter_end': 1.0 if current_date.month in [3, 6, 9, 12] and current_date.day >= 24 else 0.0
        }
        
        # Cyclical encoding for better ML performance
        features.update({
            'day_of_week_sin': np.sin(2 * np.pi * features['day_of_week'] / 7),
            'day_of_week_cos': np.cos(2 * np.pi * features['day_of_week'] / 7),
            'day_of_year_sin': np.sin(2 * np.pi * features['day_of_year'] / 365),
            'day_of_year_cos': np.cos(2 * np.pi * features['day_of_year'] / 365),
            'month_sin': np.sin(2 * np.pi * features['month'] / 12),
            'month_cos': np.cos(2 * np.pi * features['month'] / 12)
        })
        
        return features
    
    def create_comprehensive_feature_set(self, product_id: str,
                                       lookback_days: int = 30) -> Dict[str, float]:
        """Create comprehensive feature set for a product"""
        self.logger.info(f"Creating feature set for product {product_id}")
        
        # Get product information
        product = self.session.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            self.logger.warning(f"Product {product_id} not found")
            return {}
        
        # Base product features
        features = {
            'product_unit_cost': product.unit_cost,
            'product_selling_price': product.selling_price,
            'product_lead_time': product.lead_time_days,
            'product_shelf_life': product.shelf_life_days,
            'product_min_order_qty': product.min_order_quantity,
            'product_max_order_qty': product.max_order_quantity,
            'product_profit_margin': (product.selling_price - product.unit_cost) / product.selling_price
        }
        
        # Add category encoding
        category_features = self._encode_category(product.category)
        features.update(category_features)
        
        # Add all calculated features
        try:
            velocity_features = self.calculate_demand_velocity_features(product_id, lookback_days)
            features.update({f'velocity_{k}': v for k, v in velocity_features.items()})
        except Exception as e:
            self.logger.warning(f"Failed to calculate velocity features for {product_id}: {e}")
        
        try:
            channel_features = self.calculate_channel_performance_features(product_id, lookback_days)
            features.update({f'channel_{k}': v for k, v in channel_features.items()})
        except Exception as e:
            self.logger.warning(f"Failed to calculate channel features for {product_id}: {e}")
        
        try:
            inventory_features = self.calculate_inventory_health_features(product_id)
            features.update({f'inventory_{k}': v for k, v in inventory_features.items()})
        except Exception as e:
            self.logger.warning(f"Failed to calculate inventory features for {product_id}: {e}")
        
        try:
            sentiment_features = self.calculate_market_sentiment_features(product_id, lookback_days)
            features.update({f'sentiment_{k}': v for k, v in sentiment_features.items()})
        except Exception as e:
            self.logger.warning(f"Failed to calculate sentiment features for {product_id}: {e}")
        
        try:
            seasonality_features = self.calculate_seasonality_features(product_id)
            features.update({f'temporal_{k}': v for k, v in seasonality_features.items()})
        except Exception as e:
            self.logger.warning(f"Failed to calculate seasonality features for {product_id}: {e}")
        
        # Add derived features
        derived_features = self._calculate_derived_features(features)
        features.update(derived_features)
        
        return features
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend in time series"""
        if len(values) < 3:
            return 0.0
        
        x = np.arange(len(values))
        try:
            trend = np.polyfit(x, values, 1)[0]
            return float(trend)
        except:
            return 0.0
    
    def _calculate_acceleration(self, values: List[float]) -> float:
        """Calculate acceleration (second derivative) in time series"""
        if len(values) < 4:
            return 0.0
        
        x = np.arange(len(values))
        try:
            coeffs = np.polyfit(x, values, 2)
            acceleration = 2 * coeffs[0]  # Second derivative of quadratic
            return float(acceleration)
        except:
            return 0.0
    
    def _encode_category(self, category: str) -> Dict[str, float]:
        """One-hot encode product category"""
        categories = ['personal_care', 'food_beverage', 'household', 'electronics']
        features = {}
        
        for cat in categories:
            features[f'category_{cat}'] = 1.0 if category == cat else 0.0
        
        return features
    
    def _calculate_derived_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Calculate derived features from existing features"""
        derived = {}
        
        # Inventory efficiency ratios
        if 'velocity_avg_daily_quantity' in features and 'inventory_current_stock_level' in features:
            derived['inventory_turnover_rate'] = features['velocity_avg_daily_quantity'] / max(features['inventory_current_stock_level'], 1)
            derived['days_of_supply'] = features['inventory_current_stock_level'] / max(features['velocity_avg_daily_quantity'], 1)
        
        # Demand-supply balance
        if 'velocity_avg_daily_quantity' in features and 'inventory_current_available_stock' in features:
            derived['supply_demand_ratio'] = features['inventory_current_available_stock'] / max(features['velocity_avg_daily_quantity'], 1)
        
        # Price competitiveness
        if 'product_selling_price' in features and 'sentiment_avg_competitor_price' in features and features['sentiment_avg_competitor_price'] > 0:
            derived['price_competitiveness'] = features['sentiment_avg_competitor_price'] / features['product_selling_price']
        
        # Channel efficiency
        if 'channel_channel_revenue_efficiency' in features and 'product_selling_price' in features:
            derived['channel_efficiency_ratio'] = features['channel_channel_revenue_efficiency'] / max(features['product_selling_price'], 1)
        
        return derived
    
    def _get_default_velocity_features(self) -> Dict[str, float]:
        """Default velocity features when no data available"""
        return {
            'avg_daily_quantity': 0.0,
            'std_daily_quantity': 0.0,
            'max_daily_quantity': 0.0,
            'min_daily_quantity': 0.0,
            'avg_daily_revenue': 0.0,
            'quantity_trend': 0.0,
            'revenue_trend': 0.0,
            'demand_volatility': 0.0,
            'revenue_per_unit': 0.0,
            'days_with_sales': 0.0,
            'sales_frequency': 0.0,
            'quantity_acceleration': 0.0,
            'peak_to_trough_ratio': 1.0
        }
    
    def _get_default_channel_features(self) -> Dict[str, float]:
        """Default channel features when no data available"""
        return {
            'channel_count': 0.0,
            'channel_diversity': 0.0,
            'dominant_channel_share': 0.0,
            'online_share': 0.0,
            'pos_share': 0.0,
            'marketplace_share': 0.0,
            'wholesale_share': 0.0,
            'channel_revenue_efficiency': 0.0
        }
    
    def _get_default_inventory_features(self) -> Dict[str, float]:
        """Default inventory features when no data available"""
        return {
            'current_stock_level': 0.0,
            'current_available_stock': 0.0,
            'current_reserved_ratio': 0.0,
            'current_in_transit': 0.0,
            'stock_trend': 0.0,
            'stock_volatility': 0.0,
            'avg_stock_level': 0.0,
            'min_stock_level': 0.0,
            'max_stock_level': 0.0,
            'stock_range_ratio': 0.0,
            'availability_ratio': 0.0,
            'stockout_risk': 1.0
        }
    
    def _get_default_sentiment_features(self) -> Dict[str, float]:
        """Default sentiment features when no data available"""
        return {
            'avg_market_trend': 0.0,
            'market_trend_volatility': 0.0,
            'market_trend_direction': 0.0,
            'avg_social_sentiment': 0.0,
            'sentiment_volatility': 0.0,
            'high_demand_ratio': 0.0,
            'medium_demand_ratio': 1.0,
            'low_demand_ratio': 0.0,
            'avg_competitor_price': 0.0,
            'competitor_price_trend': 0.0,
            'weather_diversity': 0.0,
            'event_impact_frequency': 0.0
        }


def main():
    """Main function for testing feature engineering"""
    from sqlalchemy import create_engine
    
    engine = create_engine(DATABASE_URL)
    session = get_session(engine)
    
    feature_engineer = LiveFeatureEngineer(session)
    
    # Test with a sample product
    products = session.query(Product).limit(1).all()
    if products:
        product_id = products[0].product_id
        features = feature_engineer.create_comprehensive_feature_set(product_id)
        
        print(f"Features for product {product_id}:")
        for key, value in sorted(features.items()):
            print(f"  {key}: {value}")
    
    session.close()


if __name__ == "__main__":
    main()