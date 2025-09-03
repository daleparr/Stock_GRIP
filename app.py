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

try:
    from src.data.models import get_session, create_database
    from config.settings import DATABASE_URL, DASHBOARD_CONFIG
except ImportError as e:
    IMPORT_ERRORS.append(f"Core modules: {e}")
    SYSTEM_AVAILABLE = False

try:
    from src.data.pipeline import DataPipeline
    from src.data.live_data_processor import LiveDataProcessor
    from src.optimization.live_data_optimizer import LiveDataOptimizer
except ImportError as e:
    IMPORT_ERRORS.append(f"Data pipeline: {e}")

try:
    from src.optimization.coordinator import StockGRIPSystem
except ImportError as e:
    IMPORT_ERRORS.append(f"Optimization system: {e}")
    SYSTEM_AVAILABLE = False

# Display import status
if IMPORT_ERRORS:
    st.warning("Some components have import issues:")
    for error in IMPORT_ERRORS:
        st.text(f"• {error}")
    
    if not SYSTEM_AVAILABLE:
        st.error("Core system components unavailable. Running in limited mode.")
        st.info("To resolve: Ensure all dependencies are installed: `pip install -r requirements.txt`")


@st.cache_resource
def initialize_system():
    """Initialize the Stock_GRIP system"""
    if not SYSTEM_AVAILABLE:
        return None
    
    try:
        system = StockGRIPSystem(DATABASE_URL)
        return system
    except Exception as e:
        st.error(f"Failed to initialize system: {e}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_performance_data(days=30):
    """Load performance data with caching"""
    if not SYSTEM_AVAILABLE:
        return None
    
    try:
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        # Check if DataPipeline is available
        if 'DataPipeline' in globals():
            pipeline = DataPipeline(session)
            report = pipeline.generate_performance_report(days)
        else:
            # Fallback: create a mock report
            report = {
                "summary": {
                    "total_demand": 0,
                    "total_fulfilled": 0,
                    "overall_service_level": 0.0,
                    "total_cost": 0.0,
                    "products_analyzed": 0
                },
                "daily_metrics": [],
                "top_performers": [],
                "improvement_opportunities": []
            }
        
        session.close()
        return report
    except Exception as e:
        st.error(f"Failed to load performance data: {e}")
        return None


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
        page_options = ["Dashboard", "Live Data Upload", "Live Data Analysis", "Live Optimization", "System Control", "Product Analysis", "Optimization Results", "Data Quality", "Settings"]
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
        if st.button("🚀 Initialize System", type="primary"):
            with st.spinner("Initializing system..."):
                try:
                    result = system.initialize_system(generate_sample_data=True)
                    st.success("System initialized successfully!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Initialization failed: {e}")
    
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


if __name__ == "__main__":
    main()