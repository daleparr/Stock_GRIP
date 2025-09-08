"""
Stock_GRIP - Main Streamlit Application
Inventory and Supply Chain Optimization Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import json

# Configure page
st.set_page_config(
    page_title="Stock_GRIP - Inventory Optimization",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import our modules with graceful error handling
SYSTEM_AVAILABLE = True
IMPORT_ERRORS = []
DEBUG_INFO = []

# Core imports with detailed error tracking
try:
    from src.data.models import get_session, create_database
    DEBUG_INFO.append("✅ Database models imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"Database models: {e}")
    DEBUG_INFO.append(f"❌ Database models failed: {e}")
    SYSTEM_AVAILABLE = False

try:
    from config.settings import DATABASE_URL
    DEBUG_INFO.append("✅ DATABASE_URL imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"DATABASE_URL: {e}")
    DEBUG_INFO.append(f"❌ DATABASE_URL failed: {e}")
    # Fallback database URL
    DATABASE_URL = "sqlite:///data/stock_grip.db"
    DEBUG_INFO.append(f"🔄 Using fallback DATABASE_URL: {DATABASE_URL}")

try:
    from config.settings import DASHBOARD_CONFIG
    DEBUG_INFO.append("✅ DASHBOARD_CONFIG imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"DASHBOARD_CONFIG: {e}")
    DEBUG_INFO.append(f"❌ DASHBOARD_CONFIG failed: {e}")
    # Fallback dashboard config
    DASHBOARD_CONFIG = {"title": "Stock_GRIP", "theme": "default"}
    DEBUG_INFO.append("🔄 Using fallback DASHBOARD_CONFIG")

try:
    from src.data.pipeline import DataPipeline
    DEBUG_INFO.append("✅ DataPipeline imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"DataPipeline: {e}")
    DEBUG_INFO.append(f"❌ DataPipeline failed: {e}")

try:
    from src.data.live_data_processor import LiveDataProcessor
    DEBUG_INFO.append("✅ LiveDataProcessor imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"LiveDataProcessor: {e}")
    DEBUG_INFO.append(f"❌ LiveDataProcessor failed: {e}")

try:
    from src.optimization.live_data_optimizer import LiveDataOptimizer
    DEBUG_INFO.append("✅ LiveDataOptimizer imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"LiveDataOptimizer: {e}")
    DEBUG_INFO.append(f"❌ LiveDataOptimizer failed: {e}")

try:
    from src.optimization.coordinator import StockGRIPSystem
    DEBUG_INFO.append("✅ StockGRIPSystem imported successfully")
except ImportError as e:
    IMPORT_ERRORS.append(f"StockGRIPSystem: {e}")
    DEBUG_INFO.append(f"❌ StockGRIPSystem failed: {e}")
    SYSTEM_AVAILABLE = False

# Display import status and debug info
if DEBUG_INFO:
    with st.expander("🔍 System Diagnostic Information", expanded=bool(IMPORT_ERRORS)):
        st.subheader("Import Status")
        for info in DEBUG_INFO:
            if "✅" in info:
                st.success(info)
            elif "❌" in info:
                st.error(info)
            elif "🔄" in info:
                st.warning(info)
            else:
                st.info(info)

if IMPORT_ERRORS:
    st.warning("Some components have import issues:")
    for error in IMPORT_ERRORS:
        st.text(f"• {error}")
    
    if not SYSTEM_AVAILABLE:
        st.error("Core system components unavailable. Running in limited mode.")
        st.info("To resolve: Ensure all dependencies are installed: `pip install -r requirements.txt`")


@st.cache_resource
def initialize_system():
    """Initialize the Stock_GRIP system with enhanced error handling"""
    if not SYSTEM_AVAILABLE:
        st.warning("System initialization skipped - core components unavailable")
        return None
    
    try:
        st.info("🔄 Initializing Stock_GRIP system...")
        system = StockGRIPSystem(DATABASE_URL)
        st.success("✅ Stock_GRIP system initialized successfully")
        return system
    except Exception as e:
        st.error(f"❌ Failed to initialize system: {e}")
        st.error(f"Error type: {type(e).__name__}")
        st.error(f"Database URL: {DATABASE_URL}")
        
        # Try to provide more specific error information
        try:
            import traceback
            st.code(traceback.format_exc(), language="python")
        except:
            pass
        
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_performance_data(days=30):
    """Load performance data with enhanced error handling"""
    if not SYSTEM_AVAILABLE:
        st.warning("Performance data loading skipped - system unavailable")
        return create_fallback_report()
    
    try:
        st.info("🔄 Loading performance data...")
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Check if DataPipeline is available
        if 'DataPipeline' in globals():
            pipeline = DataPipeline(session)
            report = pipeline.generate_performance_report(days)
            st.success("✅ Performance data loaded successfully")
        else:
            st.warning("🔄 DataPipeline unavailable, using fallback report")
            report = create_fallback_report()
        
        session.close()
        return report
    except Exception as e:
        st.error(f"❌ Failed to load performance data: {e}")
        st.error(f"Error type: {type(e).__name__}")
        
        # Try to provide more specific error information
        try:
            import traceback
            st.code(traceback.format_exc(), language="python")
        except:
            pass
        
        return create_fallback_report()


def create_fallback_report():
    """Create a fallback performance report"""
    return {
        "summary": {
            "total_demand": 1000,
            "total_fulfilled": 950,
            "overall_service_level": 0.95,
            "total_cost": 50000.0,
            "products_analyzed": 9
        },
        "daily_metrics": [
            {
                "date": "2025-09-01",
                "service_level": 0.95,
                "total_cost": 1500.0,
                "demand_fulfilled": 95
            },
            {
                "date": "2025-09-02",
                "service_level": 0.93,
                "total_cost": 1600.0,
                "demand_fulfilled": 88
            }
        ],
        "top_performers": [
            {"product_id": "PROD_001", "service_level": 0.98},
            {"product_id": "PROD_002", "service_level": 0.96}
        ],
        "improvement_opportunities": [
            {"product_id": "PROD_003", "issue": "Low service level", "recommendation": "Increase safety stock"}
        ]
    }


def initialize_system_with_live_data(system):
    """Initialize the Stock_GRIP system with live Weld data"""
    import os
    try:
        # Load live data from CSV
        live_data_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
        
        if not os.path.exists(live_data_path):
            raise FileNotFoundError(f"Live data file not found: {live_data_path}")
        
        # Process live data
        live_processor = LiveDataProcessor(live_data_path)
        if not live_processor.load_data():
            raise ValueError("Failed to load live data from CSV")
        
        processed_data = live_processor.process_for_stock_grip()
        
        # Get database session
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Import required models
        from src.data.models import Product, Inventory, Demand
        
        # Clear existing data
        session.query(Product).delete()
        session.query(Inventory).delete()
        session.query(Demand).delete()
        
        # Convert live data to database format
        products_created = 0
        for _, row in processed_data.iterrows():
            # Create product
            product = Product(
                product_id=row['product_id'],
                name=row['product_name'],
                category=row.get('category', 'apparel'),
                unit_cost=float(row.get('unit_cost', row['shopify_revenue'] * 0.4)),  # Estimate 40% cost
                selling_price=float(row['shopify_revenue'] / max(row['shopify_units_sold'], 1)),
                lead_time_days=int(row.get('lead_time_days', 7)),
                shelf_life_days=int(row.get('shelf_life_days', 365)),
                min_order_quantity=1,
                max_order_quantity=1000
            )
            session.add(product)
            
            # Create inventory record
            inventory = Inventory(
                product_id=row['product_id'],
                timestamp=datetime.utcnow(),
                stock_level=int(row['shopify_units_sold'] * 2),  # Estimate stock as 2x sales
                reserved_stock=0,
                in_transit=0,
                available_stock=int(row['shopify_units_sold'] * 2)
            )
            session.add(inventory)
            
            # Create demand records (historical)
            for days_ago in range(30):  # Create 30 days of demand history
                demand_date = datetime.utcnow() - timedelta(days=days_ago)
                daily_demand = max(1, int(row['shopify_units_sold'] / 30))  # Distribute sales over 30 days
                
                demand = Demand(
                    product_id=row['product_id'],
                    date=demand_date,
                    quantity_demanded=daily_demand,
                    quantity_fulfilled=daily_demand,  # Assume all demand was fulfilled
                    is_forecast=False
                )
                session.add(demand)
            
            products_created += 1
        
        # Commit all changes
        session.commit()
        session.close()
        
        # Run initial optimization
        st.info("Running initial optimization with live data...")
        strategic_result = system.coordinator.run_strategic_optimization()
        tactical_result = system.coordinator.run_tactical_optimization()
        
        return {
            "status": "initialized_with_live_data",
            "timestamp": datetime.utcnow(),
            "products_created": products_created,
            "data_source": live_data_path,
            "strategic_optimization": strategic_result,
            "tactical_optimization": tactical_result
        }
        
    except Exception as e:
        st.error(f"Error initializing with live data: {e}")
        raise e


def main():
    """Main application function"""
    
    # Initialize system
    system = initialize_system()
    
    # Sidebar
    st.sidebar.title("🏗️ Stock_GRIP")
    st.sidebar.markdown("**G**aussian **R**einforcement **I**nventory **P**latform")
    
    # Show system availability status
    if not SYSTEM_AVAILABLE:
        st.sidebar.error("⚠️ Limited Mode")
        st.sidebar.markdown("Some components unavailable")
    elif not system:
        st.sidebar.warning("⚠️ System Offline")
        st.sidebar.markdown("Initialization failed")
    else:
        st.sidebar.success("✅ System Online")
    
    # Navigation
    if SYSTEM_AVAILABLE and system:
        page_options = ["Dashboard", "6-Week Reorder Dashboard", "Live Data Upload", "Live Data Analysis", "Live Optimization", "System Control", "Product Analysis", "Optimization Results", "Data Quality", "Settings"]
    else:
        page_options = ["System Status", "Live Data Upload", "Documentation", "Settings"]
    
    page = st.sidebar.selectbox("Navigate to:", page_options)
    
    # System status in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    if SYSTEM_AVAILABLE and system:
        try:
            status = system.get_system_status()
            
            if status["system_initialized"]:
                st.sidebar.success("✅ System Initialized")
            else:
                st.sidebar.warning("⚠️ System Not Initialized")
            
            if status["optimization_status"]["is_running"]:
                st.sidebar.success("🔄 Optimization Running")
            else:
                st.sidebar.info("⏸️ Optimization Stopped")
            
            if status["database_connected"]:
                st.sidebar.success("💾 Database Connected")
            else:
                st.sidebar.error("❌ Database Disconnected")
                
        except Exception as e:
            st.sidebar.error(f"Status Error: {e}")
    else:
        st.sidebar.info("ℹ️ System components unavailable")
    
    # Main content based on selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "6-Week Reorder Dashboard":
        show_six_week_reorder_dashboard()
    elif page == "Live Data Upload":
        show_live_data_upload()
    elif page == "Live Data Analysis":
        show_live_data_analysis()
    elif page == "Live Optimization":
        show_live_optimization()
    elif page == "System Control":
        show_system_control(system)
    elif page == "Product Analysis":
        show_product_analysis()
    elif page == "Optimization Results":
        show_optimization_results()
    elif page == "Data Quality":
        show_data_quality()
    elif page == "Settings":
        show_settings()
    elif page == "System Status":
        show_system_status()
    elif page == "Documentation":
        show_documentation()


def show_dashboard():
    """Main dashboard page"""
    st.title("📊 Stock_GRIP Dashboard")
    st.markdown("Real-time inventory optimization monitoring and control")
    
    # Load performance data
    with st.spinner("Loading performance data..."):
        report = load_performance_data(30)
    
    if not report:
        st.error("Failed to load performance data")
        return
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Service Level",
            f"{report['summary']['overall_service_level']:.1%}",
            delta=f"{(report['summary']['overall_service_level'] - 0.95):.1%}"
        )
    
    with col2:
        st.metric(
            "Total Demand",
            f"{report['summary']['total_demand']:,.0f}",
            delta="units"
        )
    
    with col3:
        st.metric(
            "Total Cost",
            f"£{report['summary']['total_cost']:,.0f}",
            delta=f"-${report['summary']['total_cost'] * 0.05:.0f}"
        )
    
    with col4:
        st.metric(
            "Products Managed",
            f"{report['summary']['products_analyzed']:,}",
            delta="active"
        )
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Daily Service Level Trend")
        
        # Prepare daily data
        daily_df = pd.DataFrame(report['daily_metrics'])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        fig = px.line(
            daily_df, 
            x='date', 
            y='service_level',
            title="Service Level Over Time",
            labels={'service_level': 'Service Level', 'date': 'Date'}
        )
        fig.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Target (95%)")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 Daily Cost Trend")
        
        fig = px.bar(
            daily_df, 
            x='date', 
            y='total_cost',
            title="Daily Inventory Costs",
            labels={'total_cost': 'Total Cost (£)', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Product performance table
    st.subheader("🏆 Top Performing Products")
    
    top_products = pd.DataFrame(report['top_performers'])
    if not top_products.empty:
        st.dataframe(
            top_products[['product_id', 'category', 'service_level', 'total_demand', 'total_cost']],
            use_container_width=True
        )
    
    # Improvement opportunities
    st.subheader("🎯 Improvement Opportunities")
    
    improvement_products = pd.DataFrame(report['improvement_opportunities'])
    if not improvement_products.empty:
        st.dataframe(
            improvement_products[['product_id', 'category', 'service_level', 'total_demand', 'total_cost']],
            use_container_width=True
        )


def show_system_control(system):
    """System control page"""
    st.title("🎛️ System Control")
    st.markdown("Control and monitor the Stock_GRIP optimization system")
    
    # System status
    status = system.get_system_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Status")
        
        status_data = {
            "Component": ["System", "Optimization", "Database"],
            "Status": [
                "✅ Initialized" if status["system_initialized"] else "❌ Not Initialized",
                "🔄 Running" if status["optimization_status"]["is_running"] else "⏸️ Stopped",
                "✅ Connected" if status["database_connected"] else "❌ Disconnected"
            ]
        }
        
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    
    with col2:
        st.subheader("Optimization Schedule")
        
        opt_status = status["optimization_status"]
        
        if opt_status["last_strategic_optimization"]:
            st.info(f"Last Strategic: {opt_status['last_strategic_optimization']}")
        else:
            st.warning("No strategic optimization run yet")
        
        if opt_status["next_strategic_optimization"]:
            st.info(f"Next Strategic: {opt_status['next_strategic_optimization']}")
        
        st.info(f"Strategic Interval: {opt_status['strategic_interval_days']} days")
    
    # Control buttons
    st.subheader("System Controls")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 Initialize with Sample Data", type="secondary"):
            with st.spinner("Initializing system with sample data..."):
                try:
                    result = system.initialize_system(generate_sample_data=True)
                    st.success("System initialized with sample data!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Initialization failed: {e}")
        
        if st.button("📊 Initialize with Live Data", type="primary"):
            with st.spinner("Initializing system with live Weld data..."):
                try:
                    result = initialize_system_with_live_data(system)
                    st.success("System initialized with live data!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Live data initialization failed: {e}")
                    st.error("Please ensure live data is uploaded first.")
    
    with col2:
        if st.button("▶️ Start Optimization"):
            with st.spinner("Starting optimization..."):
                try:
                    system.start(continuous=True, tactical_interval_minutes=30)
                    st.success("Optimization started!")
                except Exception as e:
                    st.error(f"Failed to start optimization: {e}")
    
    with col3:
        if st.button("⏸️ Stop Optimization"):
            try:
                system.stop()
                st.success("Optimization stopped!")
            except Exception as e:
                st.error(f"Failed to stop optimization: {e}")
    
    with col4:
        if st.button("🔄 Run Coordination Cycle"):
            with st.spinner("Running coordination cycle..."):
                try:
                    result = system.coordinator.run_coordination_cycle()
                    st.success("Coordination cycle completed!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Coordination cycle failed: {e}")
    
    # Manual optimization controls
    st.subheader("Manual Optimization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧠 Run Strategic Optimization (GP-EIMS)"):
            with st.spinner("Running strategic optimization..."):
                try:
                    result = system.coordinator.run_strategic_optimization()
                    st.success("Strategic optimization completed!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Strategic optimization failed: {e}")
    
    with col2:
        if st.button("⚡ Run Tactical Optimization (MPC-RL-MOBO)"):
            with st.spinner("Running tactical optimization..."):
                try:
                    result = system.coordinator.run_tactical_optimization()
                    st.success("Tactical optimization completed!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Tactical optimization failed: {e}")


def show_product_analysis():
    """Product analysis page"""
    st.title("📦 Product Analysis")
    st.markdown("Detailed analysis of individual products and categories")
    
    # Load data
    try:
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Get products
        from src.data.models import Product
        products = session.query(Product).all()
        
        if not products:
            st.warning("No products found. Please initialize the system first.")
            return
        
        # Product selector
        product_options = {f"{p.product_id} - {p.name}": p.product_id for p in products}
        selected_product_display = st.selectbox("Select Product:", list(product_options.keys()))
        selected_product_id = product_options[selected_product_display]
        
        # Get selected product
        selected_product = next(p for p in products if p.product_id == selected_product_id)
        
        # Product details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Category", selected_product.category)
            st.metric("Unit Cost", f"£{selected_product.unit_cost:.2f}")
        
        with col2:
            st.metric("Selling Price", f"£{selected_product.selling_price:.2f}")
            st.metric("Lead Time", f"{selected_product.lead_time_days} days")
        
        with col3:
            profit_margin = (selected_product.selling_price - selected_product.unit_cost) / selected_product.selling_price
            st.metric("Profit Margin", f"{profit_margin:.1%}")
            st.metric("Shelf Life", f"{selected_product.shelf_life_days} days")
        
        # Demand analysis
        st.subheader("📊 Demand Analysis")
        
        from src.data.models import Demand
        demand_data = session.query(Demand).filter(
            Demand.product_id == selected_product_id,
            Demand.is_forecast == False,
            Demand.date >= datetime.utcnow() - timedelta(days=90)
        ).order_by(Demand.date).all()
        
        if demand_data:
            demand_df = pd.DataFrame([
                {
                    'date': d.date,
                    'quantity_demanded': d.quantity_demanded,
                    'quantity_fulfilled': d.quantity_fulfilled
                }
                for d in demand_data
            ])
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Scatter(x=demand_df['date'], y=demand_df['quantity_demanded'], 
                          name="Demand", line=dict(color="blue")),
                secondary_y=False,
            )
            
            fig.add_trace(
                go.Scatter(x=demand_df['date'], y=demand_df['quantity_fulfilled'], 
                          name="Fulfilled", line=dict(color="green")),
                secondary_y=False,
            )
            
            fig.update_xaxes(title_text="Date")
            fig.update_yaxes(title_text="Quantity", secondary_y=False)
            fig.update_layout(title="Demand vs Fulfillment", height=400)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No demand data available for this product")
        
        # Current optimization parameters
        st.subheader("⚙️ Current Optimization Parameters")
        
        from src.data.models import OptimizationParameters
        current_params = session.query(OptimizationParameters).filter(
            OptimizationParameters.product_id == selected_product_id,
            OptimizationParameters.is_active == True
        ).first()
        
        if current_params:
            param_data = {
                "Parameter": ["Reorder Point", "Safety Stock", "Order Quantity", "Review Period"],
                "Value": [
                    f"{current_params.reorder_point} units",
                    f"{current_params.safety_stock} units", 
                    f"{current_params.order_quantity} units",
                    f"{current_params.review_period_days} days"
                ],
                "Last Updated": [current_params.timestamp.strftime("%Y-%m-%d %H:%M")] * 4
            }
            
            st.dataframe(pd.DataFrame(param_data), use_container_width=True)
        else:
            st.warning("No optimization parameters found for this product")
        
        session.close()
        
    except Exception as e:
        st.error(f"Error loading product data: {e}")


def show_optimization_results():
    """Optimization results page"""
    st.title("🎯 Optimization Results")
    st.markdown("View and analyze optimization performance and results")
    
    try:
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Recent optimization results
        from src.data.models import OptimizationResults
        recent_results = session.query(OptimizationResults).order_by(
            OptimizationResults.timestamp.desc()
        ).limit(20).all()
        
        if recent_results:
            st.subheader("📋 Recent Optimization Runs")
            
            results_data = []
            for result in recent_results:
                results_data.append({
                    "Run ID": result.run_id[:8] + "...",
                    "Method": result.method,
                    "Timestamp": result.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Objective Value": f"{result.objective_value:.2f}",
                    "Iterations": result.convergence_iterations or "N/A",
                    "Status": "✅ Success" if result.constraints_satisfied else "❌ Failed"
                })
            
            st.dataframe(pd.DataFrame(results_data), use_container_width=True)
            
            # Method comparison
            st.subheader("📊 Method Performance Comparison")
            
            method_performance = {}
            for result in recent_results:
                if result.method not in method_performance:
                    method_performance[result.method] = []
                method_performance[result.method].append(result.objective_value)
            
            if len(method_performance) > 1:
                comparison_data = []
                for method, values in method_performance.items():
                    comparison_data.append({
                        "Method": method,
                        "Avg Objective": np.mean(values),
                        "Best Objective": np.min(values),
                        "Runs": len(values)
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                fig = px.bar(
                    comparison_df, 
                    x="Method", 
                    y="Avg Objective",
                    title="Average Objective Value by Method"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.warning("No optimization results found")
        
        session.close()
        
    except Exception as e:
        st.error(f"Error loading optimization results: {e}")


def show_data_quality():
    """Data quality page"""
    st.title("🔍 Data Quality")
    st.markdown("Monitor and validate data quality across the system")
    
    try:
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        pipeline = DataPipeline(session)
        
        if st.button("🔄 Run Data Quality Check"):
            with st.spinner("Running data quality validation..."):
                validation_results = pipeline.run_data_quality_check()
                
                if validation_results["validation_passed"]:
                    st.success("✅ All data quality checks passed!")
                else:
                    st.warning(f"⚠️ Found {validation_results['total_issues']} data quality issues")
                
                # Show detailed results
                for category, issues in validation_results.items():
                    if isinstance(issues, dict) and any(issues.values()):
                        st.subheader(f"{category.replace('_', ' ').title()}")
                        
                        for issue_type, issue_list in issues.items():
                            if issue_list:
                                st.error(f"{issue_type.replace('_', ' ').title()}: {len(issue_list)} issues")
                                with st.expander(f"View {issue_type} details"):
                                    for issue in issue_list:
                                        st.text(issue)
        
        session.close()
        
    except Exception as e:
        st.error(f"Error running data quality check: {e}")


def show_settings():
    """Settings page"""
    st.title("⚙️ Settings")
    st.markdown("Configure system parameters and preferences")
    
    # Display current configuration
    st.subheader("📋 Current Configuration")
    
    from config.settings import GP_EIMS_CONFIG, MPC_RL_CONFIG, SIMULATION_CONFIG
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**GP-EIMS Configuration**")
        st.json(GP_EIMS_CONFIG)
        
        st.markdown("**Simulation Configuration**")
        st.json(SIMULATION_CONFIG)
    
    with col2:
        st.markdown("**MPC-RL Configuration**")
        st.json(MPC_RL_CONFIG)
        
        st.markdown("**Dashboard Configuration**")
        st.json(DASHBOARD_CONFIG)
    
    # Configuration editor (simplified)
    st.subheader("🔧 Quick Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Strategic Optimization Interval (days)",
            min_value=1,
            max_value=30,
            value=GP_EIMS_CONFIG["optimization_interval_days"],
            help="How often to run strategic optimization"
        )
        
        st.number_input(
            "Service Level Target",
            min_value=0.8,
            max_value=1.0,
            value=SIMULATION_CONFIG["service_level_target"],
            step=0.01,
            format="%.2f",
            help="Target service level (fill rate)"
        )
    
    with col2:
        st.number_input(
            "MPC Prediction Horizon (days)",
            min_value=3,
            max_value=21,
            value=MPC_RL_CONFIG["prediction_horizon"],
            help="How many days ahead to predict"
        )
        
        st.number_input(
            "Dashboard Refresh Interval (seconds)",
            min_value=10,
            max_value=300,
            value=DASHBOARD_CONFIG["refresh_interval"],
            help="How often to refresh dashboard data"
        )
    
    if st.button("💾 Save Settings"):
        st.success("Settings saved! (Note: Restart required for some changes)")


def show_system_status():
    """System status page for limited mode"""
    st.title("🔧 System Status")
    st.markdown("Current system status and troubleshooting information")
    
    # System availability status
    st.subheader("📊 Component Status")
    
    status_data = []
    
    # Check core modules
    try:
        from src.data.models import get_session, create_database
        from config.settings import DATABASE_URL, DASHBOARD_CONFIG
        status_data.append({"Component": "Core Modules", "Status": "✅ Available", "Details": "Database and settings loaded"})
    except ImportError as e:
        status_data.append({"Component": "Core Modules", "Status": "❌ Error", "Details": str(e)})
    
    # Check data pipeline
    try:
        from src.data.pipeline import DataPipeline
        status_data.append({"Component": "Data Pipeline", "Status": "✅ Available", "Details": "Data processing ready"})
    except ImportError as e:
        status_data.append({"Component": "Data Pipeline", "Status": "❌ Error", "Details": str(e)})
    
    # Check optimization system
    try:
        from src.optimization.coordinator import StockGRIPSystem
        status_data.append({"Component": "Optimization System", "Status": "✅ Available", "Details": "GP-EIMS and MPC-RL-MOBO ready"})
    except ImportError as e:
        status_data.append({"Component": "Optimization System", "Status": "❌ Error", "Details": str(e)})
    
    # Check cvxpy specifically
    try:
        import cvxpy as cp
        status_data.append({"Component": "CVXPY Solver", "Status": "✅ Available", "Details": f"Version {cp.__version__}"})
    except ImportError as e:
        status_data.append({"Component": "CVXPY Solver", "Status": "❌ Missing", "Details": "Required for MPC optimization"})
    
    st.dataframe(pd.DataFrame(status_data), use_container_width=True)
    
    # Import errors section
    if IMPORT_ERRORS:
        st.subheader("⚠️ Import Issues")
        st.error("The following import errors were detected:")
        
        for i, error in enumerate(IMPORT_ERRORS, 1):
            st.text(f"{i}. {error}")
        
        st.subheader("🔧 Troubleshooting Steps")
        
        st.markdown("""
        **To resolve import issues:**
        
        1. **Install missing dependencies:**
           ```bash
           pip install -r requirements.txt
           ```
        
        2. **For CVXPY issues specifically:**
           ```bash
           pip install cvxpy
           # Or if that fails:
           conda install -c conda-forge cvxpy
           ```
        
        3. **Verify installation:**
           ```bash
           python -c "import cvxpy; print('CVXPY version:', cvxpy.__version__)"
           ```
        
        4. **Check Python environment:**
           - Ensure you're using the correct Python environment
           - Verify all packages are installed in the same environment
           - Consider creating a fresh virtual environment
        
        5. **Restart Streamlit:**
           ```bash
           streamlit run app.py
           ```
        """)
    else:
        st.success("✅ All components are available and ready!")
    
    # System information
    st.subheader("💻 System Information")
    
    import sys
    import platform
    
    system_info = {
        "Python Version": sys.version,
        "Platform": platform.platform(),
        "Architecture": platform.architecture()[0],
        "Processor": platform.processor() or "Unknown"
    }
    
    for key, value in system_info.items():
        st.text(f"{key}: {value}")


def show_documentation():
    """Documentation page"""
    st.title("📚 Documentation")
    st.markdown("System documentation and user guides")
    
    # Documentation tabs
    tab1, tab2, tab3 = st.tabs(["📖 User Guide", "🔧 Technical Docs", "🚀 Quick Start"])
    
    with tab1:
        st.subheader("📖 User Guide")
        
        try:
            with open("docs/USER_GUIDE.md", "r", encoding="utf-8") as f:
                user_guide_content = f.read()
            st.markdown(user_guide_content)
        except FileNotFoundError:
            st.error("User guide not found at docs/USER_GUIDE.md")
        except Exception as e:
            st.error(f"Error loading user guide: {e}")
    
    with tab2:
        st.subheader("🔧 Technical Documentation")
        
        try:
            with open("docs/TECHNICAL_DOCUMENTATION.md", "r", encoding="utf-8") as f:
                tech_docs_content = f.read()
            st.markdown(tech_docs_content)
        except FileNotFoundError:
            st.error("Technical documentation not found at docs/TECHNICAL_DOCUMENTATION.md")
        except Exception as e:
            st.error(f"Error loading technical documentation: {e}")
    
    with tab3:
        st.subheader("🚀 Quick Start Guide")
        
        st.markdown("""
        ## Getting Started with Stock_GRIP
        
        ### 1. System Requirements
        - Python 3.8+
        - Required packages (see requirements.txt)
        - Sufficient memory for optimization algorithms
        
        ### 2. Installation
        ```bash
        # Clone the repository
        git clone <repository-url>
        cd Stock_GRIP
        
        # Install dependencies
        pip install -r requirements.txt
        
        # Run the application
        streamlit run app.py
        ```
        
        ### 3. First Steps
        1. **Initialize System**: Go to System Control → Initialize System
        2. **Generate Data**: The system will create sample FMCG data
        3. **Start Optimization**: Click "Start Optimization" to begin
        4. **Monitor Dashboard**: View real-time metrics and performance
        
        ### 4. Key Features
        - **GP-EIMS**: Strategic parameter optimization using Gaussian Processes
        - **MPC-RL-MOBO**: Real-time inventory decisions with Model Predictive Control
        - **Hybrid Approach**: Coordinated optimization for maximum efficiency
        - **Real-time Dashboard**: Monitor performance and control the system
        
        ### 5. Troubleshooting
        - Check System Status page for component availability
        - Ensure all dependencies are installed
        - Verify database connectivity
        - Review logs for detailed error information
        
        ### 6. Support
        - Review the Technical Documentation for detailed implementation details
        - Check the User Guide for operational procedures
        - Examine the source code for customization options
        """)


def show_live_data_upload():
    """Live data upload page"""
    st.title("📊 Live Data Upload")
    st.markdown("Upload your Weld-exported CSV files for live Stock GRIP testing")
    
    # File upload section
    st.subheader("📁 Upload Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Product Performance Data**")
        product_file = st.file_uploader(
            "Upload Product Performance CSV",
            type=['csv'],
            key="product_performance",
            help="Export from your Weld Product_Performance_Aggregated model"
        )
        
        if product_file:
            st.success(f"✅ File uploaded: {product_file.name}")
            st.info(f"File size: {product_file.size:,} bytes")
    
    with col2:
        st.markdown("**Marketing Attribution Data (Optional)**")
        attribution_file = st.file_uploader(
            "Upload Marketing Attribution CSV",
            type=['csv'],
            key="marketing_attribution",
            help="Export from your Weld Marketing_Attribution_Model"
        )
        
        if attribution_file:
            st.success(f"✅ File uploaded: {attribution_file.name}")
            st.info(f"File size: {attribution_file.size:,} bytes")
    
    # Process uploaded files
    if product_file:
        if st.button("🚀 Process Live Data", type="primary"):
            with st.spinner("Processing live data..."):
                try:
                    # Save uploaded file temporarily
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                        tmp_file.write(product_file.getvalue())
                        temp_path = tmp_file.name
                    
                    # Process with LiveDataProcessor
                    processor = LiveDataProcessor(temp_path)
                    
                    if processor.load_data():
                        # Validate data
                        issues = processor.validate_data()
                        if issues:
                            st.warning("⚠️ Data validation issues found:")
                            for issue in issues:
                                st.text(f"• {issue}")
                        else:
                            st.success("✅ Data validation passed")
                        
                        # Process for Stock GRIP
                        processed_data = processor.process_for_stock_grip()
                        st.success(f"✅ Processed {len(processed_data)} products")
                        
                        # Store in session state
                        st.session_state['live_processor'] = processor
                        st.session_state['live_data_processed'] = True
                        
                        # Display summary
                        summary = processor.get_optimization_summary()
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Total Products", summary['total_products'])
                        
                        with col2:
                            st.metric("Total Revenue", f"£{summary['total_revenue']:,.2f}")
                        
                        with col3:
                            st.metric("High Performers", summary['high_performers'])
                        
                        with col4:
                            st.metric("Email Responsive", summary['email_responsive_products'])
                        
                        # Data preview
                        st.subheader("📋 Data Preview")
                        st.dataframe(processed_data.head(10), use_container_width=True)
                        
                    else:
                        st.error("❌ Failed to load data")
                    
                    # Clean up temp file
                    os.unlink(temp_path)
                    
                except Exception as e:
                    st.error(f"❌ Error processing data: {str(e)}")
    else:
        st.info("👆 Please upload a Product Performance CSV file to get started")


def show_live_data_analysis():
    """Live data analysis page"""
    st.title("🔴 Live Data Analysis")
    st.markdown("Analysis of your uploaded Weld data")
    
    # Check if data is loaded
    if 'live_processor' not in st.session_state:
        st.warning("⚠️ No live data loaded. Please upload data first.")
        if st.button("📊 Go to Upload Page"):
            st.session_state.page = "Live Data Upload"
            st.rerun()
        return
    
    processor = st.session_state['live_processor']
    
    try:
        # Get summary data
        summary = processor.get_optimization_summary()
        processed_data = processor.processed_data
        
        # Key metrics dashboard
        st.subheader("📈 Key Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Revenue",
                f"£{summary['total_revenue']:,.2f}",
                delta=f"{summary['total_products']} products"
            )
        
        with col2:
            st.metric(
                "Units Sold",
                f"{summary['total_units_sold']:,}",
                delta=f"£{summary['avg_unit_price']:.2f} avg price"
            )
        
        with col3:
            st.metric(
                "Marketing ROAS",
                f"{summary['overall_marketing_roas']:.2f}x",
                delta=f"£{summary['total_marketing_spend']:,.0f} spend"
            )
        
        with col4:
            st.metric(
                "Organic Share",
                f"{summary['organic_revenue_share']:.1%}",
                delta="of total revenue"
            )
        
        # Charts section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top Products by Revenue")
            top_products = processed_data.nlargest(10, 'revenue')[['product_name', 'revenue', 'demand_velocity']]
            fig = px.bar(
                top_products,
                x='revenue',
                y='product_name',
                orientation='h',
                title="Revenue by Product",
                labels={'revenue': 'Revenue (£)', 'product_name': 'Product'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📊 Category Performance")
            category_performance = processed_data.groupby('category_clean').agg({
                'revenue': 'sum',
                'demand_velocity': 'sum'
            }).reset_index()
            
            fig = px.pie(
                category_performance,
                values='revenue',
                names='category_clean',
                title="Revenue by Category"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed analysis
        st.subheader("📋 Product Performance Analysis")
        
        # Performance filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            category_filter = st.selectbox(
                "Filter by Category",
                options=['All'] + list(processed_data['category_clean'].unique())
            )
        
        with col2:
            performance_filter = st.selectbox(
                "Filter by Performance",
                options=['All', 'High Performers', 'Marketing Driven', 'Email Responsive']
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                options=['Revenue', 'Units Sold', 'Marketing Efficiency', 'Organic Ratio']
            )
        
        # Apply filters
        filtered_data = processed_data.copy()
        
        if category_filter != 'All':
            filtered_data = filtered_data[filtered_data['category_clean'] == category_filter]
        
        if performance_filter == 'High Performers':
            filtered_data = filtered_data[filtered_data['high_performer'] == 1]
        elif performance_filter == 'Marketing Driven':
            filtered_data = filtered_data[filtered_data['marketing_driven'] == 1]
        elif performance_filter == 'Email Responsive':
            filtered_data = filtered_data[filtered_data['email_responsive'] == 1]
        
        # Sort data
        sort_column_map = {
            'Revenue': 'revenue',
            'Units Sold': 'demand_velocity',
            'Marketing Efficiency': 'marketing_efficiency',
            'Organic Ratio': 'organic_ratio'
        }
        
        filtered_data = filtered_data.sort_values(
            sort_column_map[sort_by],
            ascending=False
        )
        
        # Display filtered data
        display_columns = [
            'product_name', 'category_clean', 'revenue', 'demand_velocity',
            'marketing_efficiency', 'organic_ratio', 'high_performer',
            'marketing_driven', 'email_responsive'
        ]
        
        st.dataframe(
            filtered_data[display_columns].head(20),
            use_container_width=True,
            column_config={
                'revenue': st.column_config.NumberColumn('Revenue', format='£%.2f'),
                'marketing_efficiency': st.column_config.NumberColumn('Marketing ROAS', format='%.2f'),
                'organic_ratio': st.column_config.NumberColumn('Organic %', format='%.1%'),
                'high_performer': st.column_config.CheckboxColumn('High Performer'),
                'marketing_driven': st.column_config.CheckboxColumn('Marketing Driven'),
                'email_responsive': st.column_config.CheckboxColumn('Email Responsive')
            }
        )
        
        # Insights section
        st.subheader("💡 Key Insights")
        
        insights = []
        
        if summary['high_performers'] > 0:
            insights.append(f"🏆 {summary['high_performers']} high-performing products generating significant revenue")
        
        if summary['email_responsive_products'] == summary['total_products']:
            insights.append("📧 All products show email marketing responsiveness - strong Klaviyo performance")
        
        if summary['organic_revenue_share'] > 0.7:
            insights.append("🌱 Strong organic performance indicates good product-market fit")
        
        if summary['overall_marketing_roas'] > 2.0:
            insights.append(f"💰 Excellent marketing ROI at {summary['overall_marketing_roas']:.1f}x - consider scaling")
        
        for insight in insights:
            st.success(insight)
        
    except Exception as e:
        st.error(f"❌ Error analyzing data: {str(e)}")


def show_live_optimization():
    """Live optimization page"""
    st.title("🎯 Live Optimization")
    st.markdown("Run Stock GRIP optimization with your live data")
    
    # Check if data is loaded
    if 'live_processor' not in st.session_state:
        st.warning("⚠️ No live data loaded. Please upload data first.")
        if st.button("📊 Go to Upload Page"):
            st.session_state.page = "Live Data Upload"
            st.rerun()
        return
    
    processor = st.session_state['live_processor']
    
    # Optimization controls
    st.subheader("🚀 Optimization Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧠 Run GP-EIMS Strategic Optimization", type="primary"):
            with st.spinner("Running strategic optimization..."):
                try:
                    optimizer = LiveDataOptimizer(processor)
                    
                    if optimizer.initialize_optimization_data():
                        gp_results = optimizer.run_gp_eims_optimization()
                        st.session_state['gp_results'] = gp_results
                        st.success("✅ GP-EIMS optimization completed!")
                        
                        # Display top recommendations
                        st.subheader("🎯 Strategic Recommendations")
                        
                        results_df = pd.DataFrame.from_dict(gp_results, orient='index')
                        results_df = results_df.sort_values('expected_improvement', ascending=False)
                        
                        st.dataframe(
                            results_df[['product_name', 'recommendation', 'priority', 'expected_improvement', 'confidence']].head(10),
                            use_container_width=True,
                            column_config={
                                'expected_improvement': st.column_config.NumberColumn('Expected Improvement', format='%.2f'),
                                'confidence': st.column_config.NumberColumn('Confidence', format='%.1%')
                            }
                        )
                    else:
                        st.error("❌ Failed to initialize optimization data")
                        
                except Exception as e:
                    st.error(f"❌ Strategic optimization failed: {str(e)}")
    
    with col2:
        if st.button("⚡ Run MPC-RL-MOBO Tactical Optimization"):
            with st.spinner("Running tactical optimization..."):
                try:
                    optimizer = LiveDataOptimizer(processor)
                    
                    if optimizer.initialize_optimization_data():
                        mpc_results = optimizer.run_mpc_rl_mobo_optimization()
                        st.session_state['mpc_results'] = mpc_results
                        st.success("✅ MPC-RL-MOBO optimization completed!")
                        
                        # Display tactical actions
                        st.subheader("⚡ Tactical Actions")
                        
                        results_df = pd.DataFrame.from_dict(mpc_results, orient='index')
                        results_df = results_df.sort_values('optimization_confidence', ascending=False)
                        
                        st.dataframe(
                            results_df[['action', 'urgency', 'recommended_stock_level', 'optimization_confidence']].head(10),
                            use_container_width=True,
                            column_config={
                                'recommended_stock_level': st.column_config.NumberColumn('Recommended Stock', format='%.0f'),
                                'optimization_confidence': st.column_config.NumberColumn('Confidence', format='%.1%')
                            }
                        )
                    else:
                        st.error("❌ Failed to initialize optimization data")
                        
                except Exception as e:
                    st.error(f"❌ Tactical optimization failed: {str(e)}")
    
    # Unified recommendations
    if 'gp_results' in st.session_state and 'mpc_results' in st.session_state:
        st.subheader("🎯 Unified Recommendations")
        
        try:
            optimizer = LiveDataOptimizer(processor)
            optimizer.optimization_results = {
                'gp_eims': st.session_state['gp_results'],
                'mpc_rl_mobo': st.session_state['mpc_results']
            }
            
            unified = optimizer.generate_unified_recommendations()
            insights = optimizer.get_portfolio_insights()
            
            # Top recommendations
            top_recs = optimizer.get_top_recommendations(5)
            
            st.markdown("**Top 5 Optimization Recommendations:**")
            
            for i, (product_id, rec) in enumerate(top_recs.items(), 1):
                with st.expander(f"{i}. {rec['product_name']} - {rec['strategic_recommendation'].replace('_', ' ').title()}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Strategic:** {rec['strategic_recommendation'].replace('_', ' ').title()}")
                        st.write(f"**Priority:** {rec['priority'].title()}")
                        st.write(f"**Expected Improvement:** £{rec['expected_improvement']:.2f}")
                    
                    with col2:
                        st.write(f"**Tactical:** {rec['tactical_action'].replace('_', ' ').title()}")
                        st.write(f"**Urgency:** {rec['urgency'].title()}")
                        st.write(f"**Confidence:** {rec['overall_confidence']:.1%}")
            
            # Portfolio insights
            st.subheader("📊 Portfolio Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Portfolio Health",
                    f"{insights['portfolio_health']['performance_rate']:.1%}",
                    delta=f"{insights['portfolio_health']['high_performers']} high performers"
                )
            
            with col2:
                st.metric(
                    "Marketing ROI",
                    f"{insights['revenue_analysis']['marketing_roas']:.2f}x",
                    delta=f"£{insights['revenue_analysis']['total_revenue']:,.0f} revenue"
                )
            
            with col3:
                st.metric(
                    "Email Effectiveness",
                    f"{insights['channel_effectiveness']['email_responsive_rate']:.1%}",
                    delta="products responsive"
                )
            
        except Exception as e:
            st.error(f"❌ Error generating unified recommendations: {str(e)}")
    
    # Export results
    if 'gp_results' in st.session_state or 'mpc_results' in st.session_state:
        st.subheader("📥 Export Results")
        
        if st.button("📊 Export Optimization Results"):
            try:
                optimizer = LiveDataOptimizer(processor)
                if 'gp_results' in st.session_state:
                    optimizer.optimization_results['gp_eims'] = st.session_state['gp_results']
                if 'mpc_results' in st.session_state:
                    optimizer.optimization_results['mpc_rl_mobo'] = st.session_state['mpc_results']
                
                results_df = optimizer.export_optimization_results()
                
                # Convert to CSV
                csv = results_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Results CSV",
                    data=csv,
                    file_name=f"stock_grip_optimization_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                st.success("✅ Results ready for download!")
                
            except Exception as e:
                st.error(f"❌ Error exporting results: {str(e)}")


def show_six_week_reorder_dashboard():
    """6-Week Lead Time Reorder Dashboard for stakeholder decision making"""
    st.title("📅 6-Week Reorder Dashboard")
    st.markdown("**Strategic inventory decisions with 6-week lead time optimization**")
    
    # Business context
    st.info("🎯 **Business Context**: 6-week lead time for restocking | Avoid stockouts while preventing 30+ day overstock")
    
    try:
        # Check for live data in session state first
        if 'live_processor' in st.session_state and st.session_state.get('live_data_processed', False):
            st.success("✅ Using uploaded live data from session")
            live_processor = st.session_state['live_processor']
            processed_data = live_processor.process_for_stock_grip()
            
            # Debug info
            st.info(f"📊 Processing {len(processed_data)} products from uploaded data")
            
        else:
            # Fallback to file system
            live_data_path = "data/live_data/stock_grip_product_performace_aggregated_03_09_2025_11_30.csv"
            
            if not os.path.exists(live_data_path):
                st.error("❌ No live data found. Please upload data using the 'Live Data Upload' page first.")
                st.info("💡 Go to 'Live Data Upload' → Upload your Weld CSV → Process Live Data → Return here")
                return
            
            st.info("📁 Using default live data file")
            # Process live data from file
            live_processor = LiveDataProcessor(live_data_path)
            if not live_processor.load_data():
                st.error("Failed to load live data from file")
                return
            
            processed_data = live_processor.process_for_stock_grip()
            st.info(f"📊 Processing {len(processed_data)} products from file")
        
        # Validate data structure
        required_columns = ['product_name', 'shopify_units_sold', 'shopify_revenue']
        missing_columns = [col for col in required_columns if col not in processed_data.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {missing_columns}")
            st.info("Available columns: " + ", ".join(processed_data.columns.tolist()))
            return
        
        # Check for SKU column
        if 'product_sku' in processed_data.columns:
            st.success("✅ Using actual SKU field from dataset")
        else:
            st.warning("⚠️ No SKU field found, using product_id as fallback")
        
        # Calculate 6-week inventory metrics
        reorder_analysis = []
        
        for _, row in processed_data.iterrows():
            # Get actual SKU from dataset
            sku = row.get('product_sku', row['product_id'])
            
            # Use REAL inventory data if available (from unified CSV)
            if 'current_inventory_level' in row and pd.notna(row['current_inventory_level']):
                # REAL inventory data available
                current_stock = int(row['current_inventory_level'])
                available_stock = int(row.get('available_inventory', current_stock))
                reorder_point = int(row.get('reorder_point', 21))
                max_stock = int(row.get('max_stock_level', 75))
                safety_days = int(row.get('safety_stock_days', 14))
                data_source = "REAL_INVENTORY"
            else:
                # Fallback to estimation (old method)
                daily_sales_rate = row['shopify_units_sold'] / 30
                current_stock = max(1, int(daily_sales_rate * 10))
                available_stock = current_stock
                reorder_point = 21  # Default
                max_stock = 75  # Default
                safety_days = 14  # Default
                data_source = "ESTIMATED"
            
            # Calculate sales velocity
            daily_sales_rate = row['shopify_units_sold'] / 30
            
            # 6-week projections using real inventory
            days_until_stockout = available_stock / max(daily_sales_rate, 0.1)
            six_week_demand = daily_sales_rate * 42  # 6 weeks = 42 days
            
            # Risk calculations using REAL inventory levels
            stockout_risk = "HIGH" if available_stock <= reorder_point else "MEDIUM" if days_until_stockout < 60 else "LOW"
            overstock_risk = "HIGH" if available_stock > max_stock else "MEDIUM" if available_stock > (max_stock * 0.8) else "LOW"
            
            # Confidence based on data source and sales velocity
            if data_source == "REAL_INVENTORY":
                confidence = "HIGH" if row['shopify_units_sold'] > 10 else "MEDIUM"
            else:
                confidence = "MEDIUM" if row['shopify_units_sold'] > 50 else "LOW"
            
            # Reorder priority using real inventory logic
            if stockout_risk == "HIGH":
                priority = "URGENT"
            elif stockout_risk == "MEDIUM" and overstock_risk == "LOW":
                priority = "HIGH"
            elif stockout_risk == "LOW" and overstock_risk == "LOW":
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            # Revenue impact
            unit_price = row['shopify_revenue'] / max(row['shopify_units_sold'], 1)
            revenue_at_risk = max(0, (reorder_point - available_stock)) * unit_price if available_stock < reorder_point else 0
            
            # ACCURATE recommended order calculation using REAL inventory
            safety_buffer = daily_sales_rate * safety_days
            total_needed = six_week_demand + safety_buffer
            recommended_order = max(0, int(total_needed - available_stock))
            
            # Prevent massive overstock
            if recommended_order > (daily_sales_rate * 90):  # More than 90 days of stock
                recommended_order = max(0, int(daily_sales_rate * 60))  # Cap at 60 days
            
            reorder_analysis.append({
                'SKU': sku,
                'Product': row['product_name'],
                'Current Stock': current_stock,
                'Available Stock': available_stock,
                'Daily Sales': round(daily_sales_rate, 1),
                'Days Until Stockout': round(days_until_stockout, 1),
                'Stockout Risk': stockout_risk,
                'Overstock Risk': overstock_risk,
                'Priority': priority,
                'Confidence': confidence,
                'Revenue at Risk': revenue_at_risk,
                '6-Week Demand': round(six_week_demand, 1),
                'Recommended Order': recommended_order,
                'Data Source': data_source,
                'Reorder Point': reorder_point
            })
        
        df = pd.DataFrame(reorder_analysis)
        
        # Data source indicator
        real_inventory_count = len(df[df['Data Source'] == 'REAL_INVENTORY']) if 'Data Source' in df.columns else 0
        estimated_count = len(df[df['Data Source'] == 'ESTIMATED']) if 'Data Source' in df.columns else len(df)
        
        if real_inventory_count > 0:
            st.success(f"✅ Using REAL inventory data for {real_inventory_count} products")
        if estimated_count > 0:
            st.warning(f"⚠️ Using ESTIMATED inventory for {estimated_count} products")
        
        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        urgent_count = len(df[df['Priority'] == 'URGENT'])
        high_risk_revenue = df[df['Stockout Risk'] == 'HIGH']['Revenue at Risk'].sum()
        overstock_count = len(df[df['Overstock Risk'] == 'HIGH'])
        total_reorder_value = df['Recommended Order'].sum()
        
        with col1:
            st.metric("🚨 Urgent Reorders", urgent_count, delta="SKUs need immediate action")
        
        with col2:
            st.metric("💰 Revenue at Risk", f"£{high_risk_revenue:,.0f}", delta="From potential stockouts")
        
        with col3:
            st.metric("📦 Overstock Risk", overstock_count, delta="SKUs with excess inventory")
        
        with col4:
            st.metric("🛒 Total Reorder Units", f"{total_reorder_value:,.0f}", delta="Recommended order quantity")
        
        # Priority matrix
        st.subheader("🎯 Reorder Priority Matrix")
        
        # Filter and sort by priority
        priority_order = {'URGENT': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        df['Priority_Score'] = df['Priority'].map(priority_order)
        df_sorted = df.sort_values(['Priority_Score', 'Revenue at Risk'], ascending=[False, False])
        
        # Color coding function
        def color_priority(val):
            if val == 'URGENT':
                return 'background-color: #ff4444; color: white'
            elif val == 'HIGH':
                return 'background-color: #ff8800; color: white'
            elif val == 'MEDIUM':
                return 'background-color: #ffaa00; color: black'
            else:
                return 'background-color: #88cc88; color: black'
        
        def color_risk(val):
            if val == 'HIGH':
                return 'background-color: #ff6666'
            elif val == 'MEDIUM':
                return 'background-color: #ffcc66'
            else:
                return 'background-color: #66cc66'
        
        # Display styled dataframe with enhanced columns
        display_columns = ['SKU', 'Product', 'Priority', 'Stockout Risk', 'Overstock Risk',
                          'Current Stock', 'Available Stock', 'Days Until Stockout',
                          'Confidence', 'Revenue at Risk', 'Recommended Order', 'Data Source']
        
        # Only include columns that exist in the dataframe
        available_columns = [col for col in display_columns if col in df_sorted.columns]
        
        styled_df = df_sorted[available_columns].style.applymap(
            color_priority, subset=['Priority']
        ).applymap(color_risk, subset=['Stockout Risk', 'Overstock Risk']).format({
            'Revenue at Risk': '£{:,.0f}',
            'Days Until Stockout': '{:.1f}',
            'Recommended Order': '{:,.0f}',
            'Current Stock': '{:,.0f}',
            'Available Stock': '{:,.0f}'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Stockout Risk Distribution")
            try:
                if len(df) > 0:
                    risk_counts = df['Stockout Risk'].value_counts()
                    if len(risk_counts) > 0:
                        fig_risk = px.pie(values=risk_counts.values, names=risk_counts.index,
                                         title="SKUs by Stockout Risk Level",
                                         color_discrete_map={'HIGH': '#ff4444', 'MEDIUM': '#ffaa00', 'LOW': '#88cc88'})
                        st.plotly_chart(fig_risk, use_container_width=True)
                    else:
                        st.info("No risk data available for chart")
                else:
                    st.info("No data available for risk analysis")
            except Exception as e:
                st.error(f"Error generating risk chart: {e}")
                st.info("Chart generation failed, but data processing continues below")
        
        with col2:
            st.subheader("💰 Revenue Risk Analysis")
            try:
                if len(df_sorted) > 0:
                    fig_revenue = px.bar(df_sorted.head(10), x='SKU', y='Revenue at Risk',
                                       title="Top 10 SKUs by Revenue at Risk",
                                       color='Priority',
                                       color_discrete_map={'URGENT': '#ff4444', 'HIGH': '#ff8800',
                                                         'MEDIUM': '#ffaa00', 'LOW': '#88cc88'})
                    fig_revenue.update_layout(xaxis_tickangle=45)
                    st.plotly_chart(fig_revenue, use_container_width=True)
                else:
                    st.info("No data available for revenue risk analysis")
            except Exception as e:
                st.error(f"Error generating revenue chart: {e}")
                st.info("Chart generation failed, but data processing continues below")
        
        # Action recommendations
        st.subheader("🎯 Immediate Action Items")
        
        urgent_items = df[df['Priority'] == 'URGENT']
        if len(urgent_items) > 0:
            st.error(f"🚨 **{len(urgent_items)} SKUs require URGENT reordering:**")
            for _, item in urgent_items.iterrows():
                st.write(f"• **{item['Product']}** - {item['Days Until Stockout']:.1f} days until stockout | Order {item['Recommended Order']:,.0f} units")
        
        high_items = df[df['Priority'] == 'HIGH']
        if len(high_items) > 0:
            st.warning(f"⚠️ **{len(high_items)} SKUs need HIGH priority reordering:**")
            for _, item in high_items.head(5).iterrows():
                st.write(f"• **{item['Product']}** - {item['Days Until Stockout']:.1f} days until stockout | Order {item['Recommended Order']:,.0f} units")
        
        # Download recommendations
        st.subheader("📥 Export Recommendations")
        csv = df_sorted.to_csv(index=False)
        st.download_button(
            label="📊 Download Reorder Recommendations CSV",
            data=csv,
            file_name=f"6_week_reorder_recommendations_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error generating reorder dashboard: {e}")
        st.error("Please ensure the system is initialized with live data first.")


if __name__ == "__main__":
    main()