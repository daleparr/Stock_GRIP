"""
Synthetic data generator for FMCG e-commerce scenarios
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import string
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from .models import Product, Inventory, Demand, create_database, get_session
from config.settings import PRODUCT_CATEGORIES, SIMULATION_CONFIG


class FMCGDataGenerator:
    """Generate realistic FMCG e-commerce data for testing and simulation"""
    
    def __init__(self, database_url: str):
        self.engine = create_database(database_url)
        self.session = get_session(self.engine)
        self.random_seed = 42
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)
    
    def generate_product_id(self, category: str, index: int) -> str:
        """Generate unique product ID"""
        category_code = category[:3].upper()
        return f"{category_code}-{index:04d}"
    
    def generate_product_name(self, category: str, index: int) -> str:
        """Generate realistic product names based on category"""
        name_templates = {
            "personal_care": [
                "Premium {} Shampoo", "Organic {} Soap", "Natural {} Lotion",
                "Advanced {} Cream", "Essential {} Oil", "Luxury {} Serum"
            ],
            "food_beverage": [
                "Artisan {} Coffee", "Organic {} Tea", "Premium {} Juice",
                "Natural {} Snacks", "Gourmet {} Sauce", "Fresh {} Smoothie"
            ],
            "household": [
                "Eco {} Cleaner", "Multi-Purpose {} Spray", "Heavy-Duty {} Detergent",
                "Natural {} Polish", "Professional {} Wipes", "Ultra {} Freshener"
            ],
            "electronics": [
                "Wireless {} Charger", "Bluetooth {} Speaker", "Smart {} Cable",
                "Portable {} Battery", "High-Speed {} Adapter", "Premium {} Case"
            ]
        }
        
        adjectives = ["Ultra", "Pro", "Max", "Plus", "Elite", "Prime", "Super", "Mega"]
        template = random.choice(name_templates[category])
        adjective = random.choice(adjectives)
        
        return template.format(adjective)
    
    def generate_products(self, num_products: int = None) -> List[Product]:
        """Generate product catalog"""
        if num_products is None:
            num_products = SIMULATION_CONFIG["num_products"]
        
        products = []
        products_per_category = num_products // len(PRODUCT_CATEGORIES)
        
        for category, config in PRODUCT_CATEGORIES.items():
            for i in range(products_per_category):
                product_id = self.generate_product_id(category, i)
                name = self.generate_product_name(category, i)
                
                # Generate costs based on category ranges
                unit_cost = np.random.uniform(*config["unit_cost_range"])
                selling_price = unit_cost * np.random.uniform(1.3, 2.5)  # 30-150% markup
                
                # Generate lead times
                lead_time = np.random.randint(*config["lead_time_range"])
                
                product = Product(
                    product_id=product_id,
                    name=name,
                    category=category,
                    unit_cost=round(unit_cost, 2),
                    selling_price=round(selling_price, 2),
                    lead_time_days=lead_time,
                    shelf_life_days=config["shelf_life_days"],
                    min_order_quantity=np.random.randint(1, 10),
                    max_order_quantity=np.random.randint(500, 2000)
                )
                
                products.append(product)
        
        return products
    
    def generate_demand_pattern(self, product: Product, start_date: datetime, 
                              num_days: int) -> List[Tuple[datetime, int]]:
        """Generate realistic demand patterns with seasonality and trends"""
        category_config = PRODUCT_CATEGORIES[product.category]
        base_demand = np.random.uniform(10, 100)  # Base daily demand
        
        demand_data = []
        
        for day in range(num_days):
            current_date = start_date + timedelta(days=day)
            
            # Seasonal component (weekly and yearly)
            day_of_week = current_date.weekday()
            day_of_year = current_date.timetuple().tm_yday
            
            # Weekly seasonality (higher on weekends for some categories)
            weekly_factor = 1.0
            if product.category in ["food_beverage", "personal_care"]:
                weekly_factor = 1.2 if day_of_week >= 5 else 0.9
            
            # Yearly seasonality
            yearly_factor = 1 + 0.3 * np.sin(2 * np.pi * day_of_year / 365) * category_config["seasonality_factor"]
            
            # Trend component (slight growth over time)
            trend_factor = 1 + 0.001 * day  # 0.1% daily growth
            
            # Random noise
            noise_factor = np.random.normal(1, category_config["demand_volatility"])
            
            # Promotional spikes (5% chance of 2-3x demand)
            promo_factor = 1.0
            if np.random.random() < 0.05:
                promo_factor = np.random.uniform(2, 3)
            
            # Calculate final demand
            daily_demand = base_demand * weekly_factor * yearly_factor * trend_factor * noise_factor * promo_factor
            daily_demand = max(0, int(daily_demand))  # Ensure non-negative integer
            
            demand_data.append((current_date, daily_demand))
        
        return demand_data
    
    def generate_initial_inventory(self, products: List[Product]) -> List[Inventory]:
        """Generate initial inventory levels"""
        inventory_records = []
        
        for product in products:
            # Initial stock level based on expected demand
            base_stock = np.random.randint(50, 500)
            
            reserved_stock = np.random.randint(0, base_stock // 10)
            inventory = Inventory(
                product_id=product.product_id,
                timestamp=datetime.utcnow(),
                stock_level=base_stock,
                reserved_stock=reserved_stock,
                in_transit=np.random.randint(0, base_stock // 5),
                available_stock=base_stock - reserved_stock  # Correct calculation
            )
            
            inventory_records.append(inventory)
        
        return inventory_records
    
    def simulate_demand_fulfillment(self, demand_data: List[Tuple[datetime, int]], 
                                  initial_stock: int) -> List[Tuple[datetime, int, int]]:
        """Simulate demand fulfillment given initial stock"""
        current_stock = initial_stock
        fulfillment_data = []
        
        for date, demand in demand_data:
            fulfilled = min(demand, current_stock)
            current_stock = max(0, current_stock - fulfilled)
            
            # Simple reorder logic (reorder when stock < 20% of initial)
            if current_stock < initial_stock * 0.2:
                reorder_quantity = initial_stock
                current_stock += reorder_quantity
            
            fulfillment_data.append((date, demand, fulfilled))
        
        return fulfillment_data
    
    def populate_database(self, num_products: int = None, simulation_days: int = None):
        """Populate database with synthetic data"""
        if num_products is None:
            num_products = SIMULATION_CONFIG["num_products"]
        if simulation_days is None:
            simulation_days = SIMULATION_CONFIG["simulation_days"]
        
        print(f"Generating {num_products} products...")
        
        # Generate products
        products = self.generate_products(num_products)
        
        # Add products to database
        for product in products:
            self.session.merge(product)
        self.session.commit()
        
        print(f"Generated {len(products)} products")
        
        # Generate initial inventory
        print("Generating initial inventory...")
        inventory_records = self.generate_initial_inventory(products)
        
        for inventory in inventory_records:
            self.session.merge(inventory)
        self.session.commit()
        
        print(f"Generated inventory for {len(inventory_records)} products")
        
        # Generate demand data
        print(f"Generating {simulation_days} days of demand data...")
        start_date = datetime.utcnow() - timedelta(days=simulation_days)
        
        for i, product in enumerate(products):
            if i % 10 == 0:
                print(f"Processing product {i+1}/{len(products)}")
            
            # Generate demand pattern
            demand_pattern = self.generate_demand_pattern(product, start_date, simulation_days)
            
            # Get initial stock for this product
            initial_stock = next(inv.stock_level for inv in inventory_records 
                               if inv.product_id == product.product_id)
            
            # Simulate fulfillment
            fulfillment_data = self.simulate_demand_fulfillment(demand_pattern, initial_stock)
            
            # Add demand records to database
            for date, demand, fulfilled in fulfillment_data:
                demand_record = Demand(
                    product_id=product.product_id,
                    date=date,
                    quantity_demanded=demand,
                    quantity_fulfilled=fulfilled,
                    is_forecast=False
                )
                self.session.add(demand_record)
        
        self.session.commit()
        print("Database population completed!")
    
    def generate_forecast_data(self, product_id: str, forecast_days: int = 30) -> List[Demand]:
        """Generate forecast data for a specific product"""
        # Get historical demand for the product
        historical_demand = self.session.query(Demand).filter(
            Demand.product_id == product_id,
            Demand.is_forecast == False
        ).order_by(Demand.date.desc()).limit(90).all()
        
        if not historical_demand:
            return []
        
        # Calculate average demand and trend
        recent_demand = [d.quantity_demanded for d in historical_demand[:30]]
        avg_demand = np.mean(recent_demand)
        trend = np.polyfit(range(len(recent_demand)), recent_demand, 1)[0]
        
        # Generate forecasts
        forecasts = []
        last_date = historical_demand[0].date
        
        for i in range(1, forecast_days + 1):
            forecast_date = last_date + timedelta(days=i)
            
            # Simple trend + noise forecast
            forecast_demand = avg_demand + trend * i + np.random.normal(0, avg_demand * 0.1)
            forecast_demand = max(0, int(forecast_demand))
            
            forecast = Demand(
                product_id=product_id,
                date=forecast_date,
                quantity_demanded=forecast_demand,
                quantity_fulfilled=0,  # Not yet fulfilled
                is_forecast=True,
                confidence_interval=0.8  # 80% confidence
            )
            
            forecasts.append(forecast)
        
        return forecasts
    
    def close(self):
        """Close database session"""
        self.session.close()


def main():
    """Main function for testing data generation"""
    from config.settings import DATABASE_URL
    
    generator = FMCGDataGenerator(DATABASE_URL)
    generator.populate_database()
    generator.close()


if __name__ == "__main__":
    main()