"""
Marketing-Inventory Integration Module (Phase 2)
Integrates marketing attribution data with inventory optimization algorithms
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging

class MarketingInventoryIntegrator:
    """
    Phase 2: Marketing-Inventory Integration
    Coordinates marketing performance with inventory optimization
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Channel volatility multipliers based on marketing attribution analysis
        self.channel_volatility = {
            'multi_channel_star': 1.1,      # Slightly higher due to campaign coordination
            'facebook_focused': 1.3,        # 30% more volatile due to ad performance fluctuations
            'email_focused': 2.0,           # 100% more volatile due to campaign spikes
            'organic_focused': 1.0,         # Baseline volatility (most stable)
            'marketing_dependent': 1.4,     # 40% more volatile due to paid dependency
            'low_marketing_impact': 0.9     # 10% less volatile (steady baseline demand)
        }
        
        # Marketing efficiency thresholds for demand adjustments
        self.efficiency_thresholds = {
            'facebook_roas_high': 3.0,      # High Facebook ROAS threshold
            'facebook_roas_medium': 2.0,    # Medium Facebook ROAS threshold
            'email_efficiency_high': 1.0,   # High email efficiency threshold (£1.0 per email)
            'email_efficiency_medium': 0.5  # Medium email efficiency threshold
        }
    
    def calculate_marketing_adjusted_demand(self, product_data: pd.DataFrame, 
                                          forecast_days: int = 42) -> pd.DataFrame:
        """
        Calculate marketing-adjusted demand forecasting (Phase 2 Core Feature)
        
        Args:
            product_data: DataFrame with product performance and marketing data
            forecast_days: Number of days to forecast (default 42 for 6-week lead time)
            
        Returns:
            DataFrame with marketing-adjusted demand forecasts
        """
        adjusted_data = product_data.copy()
        
        # Base demand calculation
        adjusted_data['base_daily_demand'] = adjusted_data['shopify_units_sold'] / 30
        
        # Marketing efficiency multipliers
        adjusted_data['marketing_multiplier'] = 1.0  # Default baseline
        
        # Facebook ROAS adjustments
        facebook_roas = adjusted_data.get('facebook_roas_7d', 0)
        adjusted_data.loc[facebook_roas >= self.efficiency_thresholds['facebook_roas_high'], 
                         'marketing_multiplier'] *= 1.15  # 15% boost for high ROAS
        adjusted_data.loc[(facebook_roas >= self.efficiency_thresholds['facebook_roas_medium']) & 
                         (facebook_roas < self.efficiency_thresholds['facebook_roas_high']), 
                         'marketing_multiplier'] *= 1.08  # 8% boost for medium ROAS
        
        # Email efficiency adjustments
        email_efficiency = adjusted_data.get('email_efficiency_3d', 0)
        adjusted_data.loc[email_efficiency >= self.efficiency_thresholds['email_efficiency_high'], 
                         'marketing_multiplier'] *= 1.12  # 12% boost for high efficiency
        adjusted_data.loc[(email_efficiency >= self.efficiency_thresholds['email_efficiency_medium']) & 
                         (email_efficiency < self.efficiency_thresholds['email_efficiency_high']), 
                         'marketing_multiplier'] *= 1.06  # 6% boost for medium efficiency
        
        # Multi-channel star bonus
        adjusted_data.loc[adjusted_data.get('marketing_mix_type', '') == 'multi_channel_star', 
                         'marketing_multiplier'] *= 1.05  # Additional 5% for multi-channel excellence
        
        # Calculate marketing-adjusted demand
        adjusted_data['marketing_adjusted_daily_demand'] = (
            adjusted_data['base_daily_demand'] * adjusted_data['marketing_multiplier']
        )
        
        # 6-week forecast with marketing adjustments
        adjusted_data['marketing_adjusted_6week_demand'] = (
            adjusted_data['marketing_adjusted_daily_demand'] * forecast_days
        )
        
        # Add confidence scoring based on marketing data quality
        adjusted_data['demand_forecast_confidence'] = self._calculate_demand_confidence(adjusted_data)
        
        return adjusted_data
    
    def calculate_channel_specific_safety_stock(self, product_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate channel-specific safety stock optimization (Phase 2 Core Feature)
        
        Args:
            product_data: DataFrame with marketing mix and performance data
            
        Returns:
            DataFrame with channel-adjusted safety stock recommendations
        """
        safety_data = product_data.copy()
        
        # Base safety stock calculation (14 days default)
        safety_data['base_safety_days'] = 14
        safety_data['base_daily_demand'] = safety_data['shopify_units_sold'] / 30
        safety_data['base_safety_stock'] = (
            safety_data['base_daily_demand'] * safety_data['base_safety_days']
        )
        
        # Channel-specific volatility adjustments
        marketing_mix = safety_data.get('marketing_mix_type', 'low_marketing_impact')
        safety_data['channel_volatility_multiplier'] = marketing_mix.map(self.channel_volatility).fillna(1.0)
        
        # Calculate channel-adjusted safety stock
        safety_data['channel_adjusted_safety_stock'] = (
            safety_data['base_safety_stock'] * safety_data['channel_volatility_multiplier']
        )
        
        # Additional adjustments for high-performing channels
        # Facebook stars get extra buffer during campaign periods
        safety_data.loc[safety_data.get('facebook_star', 0) == 1, 
                       'channel_adjusted_safety_stock'] *= 1.1
        
        # Email champions get extra buffer for campaign spikes
        safety_data.loc[safety_data.get('email_champion', 0) == 1, 
                       'channel_adjusted_safety_stock'] *= 1.15
        
        # Organic winners get reduced safety stock (more predictable)
        safety_data.loc[safety_data.get('organic_winner', 0) == 1, 
                       'channel_adjusted_safety_stock'] *= 0.95
        
        # Calculate safety stock days for transparency
        safety_data['channel_adjusted_safety_days'] = (
            safety_data['channel_adjusted_safety_stock'] / 
            safety_data['base_daily_demand'].replace(0, 1)
        )
        
        return safety_data
    
    def generate_marketing_driven_reorder_recommendations(self, product_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate marketing-driven reorder recommendations (Phase 2 Core Feature)
        
        Args:
            product_data: DataFrame with marketing and inventory data
            
        Returns:
            DataFrame with marketing-optimized reorder recommendations
        """
        try:
            # Debug: Log available columns
            self.logger.info(f"Marketing Integration Debug - Available columns: {list(product_data.columns)}")
            
            # Check for required marketing columns
            required_marketing_cols = ['facebook_roas_7d', 'email_efficiency_3d', 'marketing_mix_type']
            missing_cols = [col for col in required_marketing_cols if col not in product_data.columns]
            
            if missing_cols:
                self.logger.warning(f"Missing marketing columns: {missing_cols}")
                # Return original data with fallback calculations
                return self._apply_fallback_calculations(product_data)
            
            reorder_data = product_data.copy()
            
            # Get marketing-adjusted demand and safety stock
            demand_adjusted = self.calculate_marketing_adjusted_demand(reorder_data)
            safety_adjusted = self.calculate_channel_specific_safety_stock(demand_adjusted)
        except Exception as e:
            self.logger.error(f"Error in marketing integration: {str(e)}")
            # Return original data with fallback calculations
            return self._apply_fallback_calculations(product_data)
        
        # Current inventory levels
        current_stock = safety_adjusted.get('current_inventory_level', 
                                          safety_adjusted['shopify_units_sold'] / 30 * 10)  # Fallback estimate
        available_stock = safety_adjusted.get('available_inventory', current_stock)
        
        # Marketing-optimized reorder calculation
        total_needed = (
            safety_adjusted['marketing_adjusted_6week_demand'] + 
            safety_adjusted['channel_adjusted_safety_stock']
        )
        
        marketing_reorder = np.maximum(0, total_needed - available_stock)
        
        # Apply marketing priority adjustments
        priority_multiplier = 1.0
        
        # Multi-channel stars get priority
        priority_multiplier = np.where(
            safety_adjusted.get('marketing_mix_type', '') == 'multi_channel_star',
            1.1, priority_multiplier
        )
        
        # Facebook stars get campaign preparation priority
        priority_multiplier = np.where(
            safety_adjusted.get('facebook_star', 0) == 1,
            priority_multiplier * 1.05, priority_multiplier
        )
        
        # Email champions get campaign coordination priority
        priority_multiplier = np.where(
            safety_adjusted.get('email_champion', 0) == 1,
            priority_multiplier * 1.08, priority_multiplier
        )
        
        safety_adjusted['marketing_optimized_reorder'] = marketing_reorder * priority_multiplier
        
        # Cap at reasonable maximum (90 days of demand)
        max_reasonable = safety_adjusted['marketing_adjusted_daily_demand'] * 90
        safety_adjusted['marketing_optimized_reorder'] = np.minimum(
            safety_adjusted['marketing_optimized_reorder'], max_reasonable
        )
        
        # Marketing-driven priority classification
        safety_adjusted['marketing_priority'] = self._classify_marketing_priority(safety_adjusted)
        
        # Revenue impact calculation
        unit_price = safety_adjusted['shopify_revenue'] / safety_adjusted['shopify_units_sold'].replace(0, 1)
        safety_adjusted['marketing_revenue_opportunity'] = (
            safety_adjusted['marketing_optimized_reorder'] * unit_price
        )
        
        return safety_adjusted
    
    def _calculate_demand_confidence(self, data: pd.DataFrame) -> pd.Series:
        """Calculate confidence score for demand forecasts based on marketing data quality"""
        confidence = pd.Series(0.7, index=data.index)  # Base confidence
        
        # Higher confidence for products with good marketing data
        confidence += np.where(data.get('facebook_roas_7d', 0) > 0, 0.1, 0)
        confidence += np.where(data.get('email_efficiency_3d', 0) > 0, 0.1, 0)
        confidence += np.where(data.get('shopify_units_sold', 0) > 10, 0.1, 0)  # Sales volume
        
        # Multi-channel stars get highest confidence
        confidence += np.where(data.get('marketing_mix_type', '') == 'multi_channel_star', 0.1, 0)
        
        return np.clip(confidence, 0.3, 0.95)  # Keep between 30% and 95%
    
    def _classify_marketing_priority(self, data: pd.DataFrame) -> pd.Series:
        """Classify marketing-driven priority for inventory decisions"""
        priority = pd.Series('MEDIUM', index=data.index)
        
        # High priority for multi-channel stars
        priority = np.where(
            data.get('marketing_mix_type', '') == 'multi_channel_star',
            'HIGH', priority
        )
        
        # High priority for Facebook stars with high ROAS
        priority = np.where(
            (data.get('facebook_star', 0) == 1) & (data.get('facebook_roas_7d', 0) > 4.0),
            'HIGH', priority
        )
        
        # High priority for email champions with high efficiency
        priority = np.where(
            (data.get('email_champion', 0) == 1) & (data.get('email_efficiency_3d', 0) > 1.5),
            'HIGH', priority
        )
        
        # Low priority for low marketing impact
        priority = np.where(
            data.get('marketing_mix_type', '') == 'low_marketing_impact',
            'LOW', priority
        )
        
        return priority
    
    def simulate_campaign_impact(self, product_data: pd.DataFrame, 
                                campaign_lift: float = 0.3, 
                                campaign_duration_days: int = 7) -> pd.DataFrame:
        """
        Simulate impact of marketing campaigns on inventory needs (Phase 2 Enhancement)
        
        Args:
            product_data: DataFrame with product and marketing data
            campaign_lift: Expected demand lift from campaign (default 30%)
            campaign_duration_days: Duration of campaign impact
            
        Returns:
            DataFrame with campaign impact analysis
        """
        campaign_data = product_data.copy()
        
        # Base daily demand
        base_demand = campaign_data['shopify_units_sold'] / 30
        
        # Campaign impact varies by marketing mix
        mix_type = campaign_data.get('marketing_mix_type', 'low_marketing_impact')
        
        # Channel-specific campaign responsiveness
        campaign_responsiveness = {
            'multi_channel_star': 1.5,      # 50% higher response
            'facebook_focused': 1.3,        # 30% higher response
            'email_focused': 1.4,           # 40% higher response
            'organic_focused': 0.8,         # 20% lower response
            'marketing_dependent': 1.2,     # 20% higher response
            'low_marketing_impact': 0.6     # 40% lower response
        }
        
        responsiveness = mix_type.map(campaign_responsiveness).fillna(1.0)
        
        # Calculate campaign-adjusted demand lift
        campaign_data['campaign_demand_lift'] = (
            base_demand * campaign_lift * responsiveness * campaign_duration_days
        )
        
        # Additional inventory needed for campaign
        campaign_data['campaign_inventory_needed'] = campaign_data['campaign_demand_lift']
        
        # Campaign preparation lead time (days before campaign to order)
        campaign_data['campaign_prep_days'] = np.where(
            campaign_data.get('facebook_star', 0) == 1, 14, 21  # Facebook stars need less prep time
        )
        
        return campaign_data
    def _apply_fallback_calculations(self, product_data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply fallback calculations when marketing data is unavailable
        """
        fallback_data = product_data.copy()
        
        # Add missing marketing columns with default values
        fallback_data['facebook_roas_7d'] = 0.0
        fallback_data['email_efficiency_3d'] = 0.0
        fallback_data['marketing_mix_type'] = 'low_marketing_impact'
        fallback_data['facebook_star'] = 0
        fallback_data['email_champion'] = 0
        fallback_data['organic_winner'] = 0
        
        # Basic demand calculation without marketing adjustments
        fallback_data['base_daily_demand'] = fallback_data['shopify_units_sold'] / 30
        fallback_data['marketing_multiplier'] = 1.0
        fallback_data['marketing_adjusted_daily_demand'] = fallback_data['base_daily_demand']
        fallback_data['marketing_adjusted_6week_demand'] = fallback_data['base_daily_demand'] * 42
        
        # Basic safety stock (no channel adjustments)
        fallback_data['channel_volatility_multiplier'] = 1.0
        fallback_data['channel_adjusted_safety_stock'] = fallback_data['base_daily_demand'] * 7  # 1 week safety
        
        # Basic reorder calculation
        current_stock = fallback_data.get('current_inventory_level', 
                                        fallback_data['shopify_units_sold'] / 30 * 10)
        total_needed = (fallback_data['marketing_adjusted_6week_demand'] + 
                       fallback_data['channel_adjusted_safety_stock'])
        fallback_data['marketing_optimized_reorder'] = np.maximum(0, total_needed - current_stock)
        
        # Default marketing attributes
        fallback_data['marketing_priority'] = 'MEDIUM'
        fallback_data['demand_forecast_confidence'] = 0.7
        fallback_data['marketing_revenue_opportunity'] = 0.0
        
        self.logger.info("Applied fallback calculations due to missing marketing data")
        return fallback_data



class CampaignInventoryCoordinator:
    """
    Campaign-Inventory Coordination System (Phase 2 Enhancement)
    Coordinates marketing campaigns with inventory planning
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.upcoming_campaigns = []  # Will be populated from campaign calendar
    
    def add_campaign(self, campaign_info: Dict[str, Any]):
        """Add upcoming campaign to coordination system"""
        self.upcoming_campaigns.append(campaign_info)
    
    def get_campaign_inventory_requirements(self, product_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate inventory requirements for upcoming campaigns"""
        campaign_reqs = product_data.copy()
        
        # Initialize campaign flags (Phase 2 enhancement from Phase 1 placeholders)
        campaign_reqs['has_upcoming_campaign'] = 0
        campaign_reqs['campaign_priority'] = 'none'
        campaign_reqs['campaign_inventory_boost'] = 0
        
        # For now, simulate upcoming campaigns based on marketing performance
        # In production, this would integrate with actual campaign calendar
        
        # High-performing products likely to have campaigns
        high_performers = (
            (campaign_reqs.get('facebook_roas_7d', 0) > 3.0) |
            (campaign_reqs.get('email_efficiency_3d', 0) > 1.0) |
            (campaign_reqs.get('marketing_mix_type', '') == 'multi_channel_star')
        )
        
        campaign_reqs.loc[high_performers, 'has_upcoming_campaign'] = 1
        campaign_reqs.loc[high_performers, 'campaign_priority'] = 'high'
        
        # Calculate campaign inventory boost
        base_demand = campaign_reqs['shopify_units_sold'] / 30
        campaign_reqs.loc[high_performers, 'campaign_inventory_boost'] = base_demand * 7 * 0.3  # 30% lift for 7 days
        
        return campaign_reqs