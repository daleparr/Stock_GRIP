"""
Localization Configuration for Stock GRIP
Customize currency, locations, and regional settings
"""

# Currency Settings
CURRENCY_SYMBOL = "£"  # Change from "$" to "£"
CURRENCY_FORMAT = "{symbol}{amount:,.2f}"  # Format: £1,234.56

# Location Names - Customize these for your business
WAREHOUSE_LOCATIONS = [
    "warehouse_london",
    "warehouse_manchester", 
    "warehouse_birmingham",
    "distribution_centre_uk"
]

STORE_LOCATIONS = [
    "store_oxford_street",
    "store_covent_garden", 
    "store_canary_wharf",
    "store_westfield",
    "store_kings_road"
]

# All locations combined
ALL_LOCATIONS = WAREHOUSE_LOCATIONS + STORE_LOCATIONS

# Store Display Names (for dashboards)
STORE_DISPLAY_NAMES = {
    "store_oxford_street": "Oxford Street",
    "store_covent_garden": "Covent Garden",
    "store_canary_wharf": "Canary Wharf", 
    "store_westfield": "Westfield",
    "store_kings_road": "King's Road",
    "warehouse_london": "London Warehouse",
    "warehouse_manchester": "Manchester Warehouse",
    "warehouse_birmingham": "Birmingham Warehouse",
    "distribution_centre_uk": "UK Distribution Centre"
}

# Fulfillment Methods
FULFILLMENT_METHODS = [
    'warehouse',
    'store_pickup', 
    'click_collect',
    'home_delivery',
    'next_day_delivery'
]

# Regional Settings
REGION = "UK"
TIMEZONE = "Europe/London"
DATE_FORMAT = "%d/%m/%Y"  # UK date format: DD/MM/YYYY
TIME_FORMAT = "%H:%M"     # 24-hour format

# Business Settings
BUSINESS_HOURS = {
    "store_open": "09:00",
    "store_close": "21:00",
    "warehouse_open": "06:00", 
    "warehouse_close": "22:00"
}

# Sample UK Store Names for Demo Data
UK_STORE_NAMES = [
    "London Central",
    "Manchester Arndale", 
    "Birmingham Bullring",
    "Leeds Trinity",
    "Glasgow Buchanan",
    "Edinburgh Princes",
    "Bristol Cabot",
    "Liverpool One",
    "Newcastle Eldon",
    "Cardiff Queen Street"
]

def format_currency(amount: float) -> str:
    """Format amount with configured currency symbol"""
    return CURRENCY_FORMAT.format(symbol=CURRENCY_SYMBOL, amount=amount)

def get_location_display_name(location_id: str) -> str:
    """Get display name for location"""
    return STORE_DISPLAY_NAMES.get(location_id, location_id.replace('_', ' ').title())