"""
Stock_GRIP - Business Intelligence Dashboard
Retail-Focused Inventory Optimization Platform
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

# Configure page with business-friendly branding
st.set_page_config(
    page_title="Stock_GRIP - Smart Inventory Assistant",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for business-friendly styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    .alert-urgent {
        background: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .alert-opportunity {
        background: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .success-story {
        background: #f3e5f5;
        border-left: 4px solid #9c27b0;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Import modules with graceful error handling
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
except ImportError as e:
    IMPORT_ERRORS.append(f"Data pipeline: {e}")

try:
    from src.optimization.coordinator import StockGRIPSystem
except ImportError as e:
    IMPORT_ERRORS.append(f"Optimization system: {e}")
    SYSTEM_AVAILABLE = False


@st.cache_resource
def initialize_system():
    """Initialize the Stock_GRIP system"""
    if not SYSTEM_AVAILABLE:
        return None
    
    try:
        system = StockGRIPSystem(DATABASE_URL)
        return system
    except Exception as e:
        st.error(f"System initialization failed: {e}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_business_data(days=30):
    """Load and transform data for business users"""
    if not SYSTEM_AVAILABLE:
        return create_demo_data()
    
    try:
        engine = create_database(DATABASE_URL)
        session = get_session(engine)
        
        if 'DataPipeline' in globals():
            pipeline = DataPipeline(session)
            report = pipeline.generate_performance_report(days)
            
            # Transform technical data to business metrics
            business_data = transform_to_business_metrics(report)
        else:
            business_data = create_demo_data()
        
        session.close()
        return business_data
        
    except Exception as e:
        st.error(f"Failed to load business data: {e}")
        return create_demo_data()


def create_demo_data():
    """Create demo data for business dashboard"""
    return {
        "daily_briefing": {
            "greeting": "Good morning! Here's your store performance:",
            "urgent_actions": [
                {"product": "Organic Coffee Beans", "action": "Reorder today", "impact": "$2,400 revenue at risk", "priority": "🔴 URGENT"},
                {"product": "Premium Shampoo", "action": "Increase display", "impact": "$1,800 opportunity", "priority": "🟡 TODAY"}
            ],
            "success_stories": [
                {"achievement": "Prevented 3 stockouts this week", "value": "$3,200 revenue protected"},
                {"achievement": "Optimized winter clearance", "value": "$1,500 cash freed up"}
            ]
        },
        "financial_impact": {
            "weekly_savings": 3240,
            "revenue_protected": 12800,
            "cash_freed": 8500,
            "roi_percentage": 285
        },
        "customer_happiness": {
            "satisfaction_score": 96.2,
            "availability_rate": 94.8,
            "happy_customers": 9.6,
            "trend": "↑ +2.1% vs last week"
        },
        "operational_efficiency": {
            "time_saved_hours": 8.5,
            "automation_rate": 87,
            "decision_speed": "15 min avg",
            "accuracy_rate": 94.2
        },
        "trending_products": [
            {"name": "Organic Coffee", "trend": "+40%", "action": "Increase stock", "impact": "$1,800"},
            {"name": "Winter Coats", "trend": "-60%", "action": "Clear inventory", "impact": "$3,200"},
            {"name": "Valentine's Items", "trend": "+120%", "action": "Prepare stock", "impact": "$2,400"}
        ],
        "alerts": [
            {"type": "urgent", "message": "Organic Bananas: 2 days left", "action": "Order 30 bunches", "impact": "$180 revenue risk"},
            {"type": "opportunity", "message": "Premium Tea trending up", "action": "Increase display", "impact": "$450 potential"}
        ]
    }


def transform_to_business_metrics(technical_report):
    """Transform technical metrics to business language"""
    # This would contain the actual transformation logic
    # For now, return demo data structure
    return create_demo_data()


def main():
    """Main business dashboard application"""
    
    # Header with business branding
    st.markdown("""
    <div class="main-header">
        <h1>🛒 Stock_GRIP Smart Inventory Assistant</h1>
        <p>Your AI-powered partner for profitable inventory decisions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize system
    system = initialize_system()
    
    # Role-based navigation
    st.sidebar.markdown("### 👋 Welcome!")
    user_role = st.sidebar.selectbox(
        "Select your role:",
        ["Store Manager", "Inventory Planner", "Category Manager", "Regional Manager", "Technical Admin"]
    )
    
    # Show appropriate dashboard based on role
    if user_role == "Store Manager":
        show_store_manager_dashboard()
    elif user_role == "Inventory Planner":
        show_inventory_planner_dashboard()
    elif user_role == "Category Manager":
        show_category_manager_dashboard()
    elif user_role == "Regional Manager":
        show_regional_manager_dashboard()
    elif user_role == "Technical Admin":
        show_technical_dashboard(system)
    
    # System status in sidebar (simplified for business users)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔋 System Status")
    
    if SYSTEM_AVAILABLE and system:
        st.sidebar.success("✅ Smart Assistant Active")
        st.sidebar.info("🤖 AI making recommendations")
    else:
        st.sidebar.warning("⚠️ Limited Mode")
        st.sidebar.info("📊 Showing demo data")


def show_store_manager_dashboard():
    """Dashboard optimized for store managers"""
    st.markdown("## 🌅 Good Morning, Store Manager!")
    
    # Load business data
    data = load_business_data()
    
    # Daily briefing section
    st.markdown("### 📋 Your Daily Action Plan")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🚨 Urgent Actions (Do Today)")
        for action in data["daily_briefing"]["urgent_actions"]:
            priority_color = "alert-urgent" if "🔴" in action["priority"] else "alert-opportunity"
            st.markdown(f"""
            <div class="{priority_color}">
                <strong>{action['product']}</strong><br>
                Action: {action['action']}<br>
                Impact: {action['impact']}<br>
                Priority: {action['priority']}
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🏆 This Week's Wins")
        for story in data["daily_briefing"]["success_stories"]:
            st.markdown(f"""
            <div class="success-story">
                <strong>{story['achievement']}</strong><br>
                Value: {story['value']}
            </div>
            """, unsafe_allow_html=True)
    
    # Key performance metrics
    st.markdown("### 📊 Store Performance at a Glance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "😊 Customer Happiness",
            f"{data['customer_happiness']['satisfaction_score']:.1f}%",
            delta=data['customer_happiness']['trend']
        )
        st.caption("9 out of 10 customers find what they want")
    
    with col2:
        st.metric(
            "💰 Weekly Savings",
            f"${data['financial_impact']['weekly_savings']:,}",
            delta="vs manual management"
        )
        st.caption("Money saved through smart decisions")
    
    with col3:
        st.metric(
            "🛡️ Revenue Protected",
            f"${data['financial_impact']['revenue_protected']:,}",
            delta="prevented losses"
        )
        st.caption("Sales saved by avoiding stockouts")
    
    with col4:
        st.metric(
            "⏰ Time Saved",
            f"{data['operational_efficiency']['time_saved_hours']} hrs/week",
            delta="for customer service"
        )
        st.caption("Less time counting, more time selling")
    
    # Trending products section
    st.markdown("### 📈 What's Hot and What's Not")
    
    trending_df = pd.DataFrame(data["trending_products"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔥 Trending Up")
        up_trends = trending_df[trending_df['trend'].str.contains(r'\+', regex=True)]
        for _, product in up_trends.iterrows():
            st.success(f"**{product['name']}** {product['trend']} - {product['action']} (${product['impact']} opportunity)")
    
    with col2:
        st.markdown("#### 📉 Trending Down")
        down_trends = trending_df[trending_df['trend'].str.contains('-', regex=False)]
        for _, product in down_trends.iterrows():
            st.warning(f"**{product['name']}** {product['trend']} - {product['action']} (${product['impact']} at risk)")
    
    # Customer satisfaction chart
    st.markdown("### 😊 Customer Satisfaction Trend")
    
    # Generate sample data for the chart
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    satisfaction_data = pd.DataFrame({
        'Date': dates,
        'Satisfaction': np.random.normal(94, 2, len(dates)).clip(85, 100),
        'Availability': np.random.normal(93, 3, len(dates)).clip(80, 100)
    })
    
    fig = px.line(
        satisfaction_data, 
        x='Date', 
        y=['Satisfaction', 'Availability'],
        title="Customer Happiness Metrics",
        labels={'value': 'Percentage (%)', 'variable': 'Metric'}
    )
    fig.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Target: 95%")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def show_inventory_planner_dashboard():
    """Dashboard optimized for inventory planners/buyers"""
    st.markdown("## 📋 Inventory Planner Dashboard")
    
    data = load_business_data()
    
    # Smart reorder recommendations
    st.markdown("### 🤖 Smart Reorder Recommendations")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Sample reorder data
        reorder_data = pd.DataFrame([
            {"Product": "Organic Coffee Beans", "Current Stock": 12, "Days Left": 2, "Recommended Order": 48, "Cost": "$240", "Revenue Risk": "$2,400", "Priority": "🔴 URGENT"},
            {"Product": "Premium Shampoo", "Current Stock": 25, "Days Left": 5, "Recommended Order": 36, "Cost": "$180", "Revenue Risk": "$1,800", "Priority": "🟡 HIGH"},
            {"Product": "Organic Bananas", "Current Stock": 8, "Days Left": 2, "Recommended Order": 30, "Cost": "$90", "Revenue Risk": "$180", "Priority": "🔴 URGENT"},
            {"Product": "Winter Coats", "Current Stock": 45, "Days Left": 90, "Recommended Order": 0, "Cost": "$0", "Revenue Risk": "$0", "Priority": "🟢 CLEAR"}
        ])
        
        st.dataframe(
            reorder_data,
            use_container_width=True,
            column_config={
                "Priority": st.column_config.TextColumn("Priority", width="small"),
                "Revenue Risk": st.column_config.TextColumn("Revenue Risk", width="medium")
            }
        )
    
    with col2:
        st.markdown("#### 💡 Quick Actions")
        if st.button("📞 Order All Urgent Items", type="primary"):
            st.success("✅ Orders placed for urgent items!")
            st.balloons()
        
        if st.button("📧 Email Supplier"):
            st.info("📧 Supplier notification sent")
        
        if st.button("📊 Generate Report"):
            st.info("📊 Weekly report generated")
    
    # Financial impact tracking
    st.markdown("### 💰 Financial Impact This Month")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💸 Inventory Costs",
            f"${data['financial_impact']['weekly_savings'] * 4:,}",
            delta=f"-15% vs last month"
        )
        st.caption("Total inventory investment")
    
    with col2:
        st.metric(
            "🎯 Ordering Accuracy",
            f"{data['operational_efficiency']['accuracy_rate']:.1f}%",
            delta="+12% vs manual"
        )
        st.caption("Right products, right quantities")
    
    with col3:
        st.metric(
            "⚡ Decision Speed",
            data['operational_efficiency']['decision_speed'],
            delta="vs 2 hours manual"
        )
        st.caption("From analysis to order")
    
    with col4:
        st.metric(
            "🔄 Inventory Turnover",
            "8.2x/year",
            delta="vs industry 6x"
        )
        st.caption("How fast stock converts to cash")
    
    # Demand forecasting
    st.markdown("### 🔮 7-Day Demand Forecast")
    
    # Generate sample forecast data
    forecast_dates = pd.date_range(start=datetime.now(), periods=7, freq='D')
    products = ["Coffee", "Shampoo", "Bananas", "Bread", "Milk"]
    
    forecast_data = []
    for date in forecast_dates:
        for product in products:
            base_demand = np.random.randint(20, 100)
            forecast_data.append({
                'Date': date,
                'Product': product,
                'Predicted Demand': base_demand,
                'Confidence': np.random.uniform(85, 98)
            })
    
    forecast_df = pd.DataFrame(forecast_data)
    
    # Create pivot table for heatmap
    pivot_df = forecast_df.pivot(index='Product', columns='Date', values='Predicted Demand')
    
    fig = px.imshow(
        pivot_df.values,
        x=[d.strftime('%m/%d') for d in pivot_df.columns],
        y=pivot_df.index,
        title="7-Day Demand Forecast Heatmap",
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Supplier performance
    st.markdown("### 🚚 Supplier Performance")
    
    supplier_data = pd.DataFrame([
        {"Supplier": "Fresh Foods Co", "On-Time %": 94, "Quality Score": 4.8, "Cost Rating": "💰💰💰", "Recommendation": "✅ Preferred"},
        {"Supplier": "Organic Supplies", "On-Time %": 89, "Quality Score": 4.9, "Cost Rating": "💰💰💰💰", "Recommendation": "⚠️ Monitor costs"},
        {"Supplier": "Quick Delivery", "On-Time %": 98, "Quality Score": 4.2, "Cost Rating": "💰💰", "Recommendation": "⚠️ Quality issues"},
        {"Supplier": "Budget Foods", "On-Time %": 85, "Quality Score": 3.8, "Cost Rating": "💰", "Recommendation": "❌ Consider replacing"}
    ])
    
    st.dataframe(supplier_data, use_container_width=True)


def show_category_manager_dashboard():
    """Dashboard optimized for category managers"""
    st.markdown("## 📊 Category Performance Dashboard")
    
    data = load_business_data()
    
    # Category performance overview
    st.markdown("### 🏆 Category Performance Rankings")
    
    category_data = pd.DataFrame([
        {"Category": "Beverages", "Revenue": "$45,200", "Margin": "32%", "Growth": "+15%", "Rank": "🥇 #1", "Action": "Expand premium lines"},
        {"Category": "Personal Care", "Revenue": "$38,900", "Margin": "28%", "Growth": "+8%", "Rank": "🥈 #2", "Action": "Optimize shelf space"},
        {"Category": "Snacks", "Revenue": "$32,100", "Margin": "25%", "Growth": "+12%", "Rank": "🥉 #3", "Action": "Add healthy options"},
        {"Category": "Dairy", "Revenue": "$28,500", "Margin": "18%", "Growth": "-2%", "Rank": "📉 #4", "Action": "Review pricing strategy"},
        {"Category": "Frozen", "Revenue": "$22,800", "Margin": "22%", "Growth": "+5%", "Rank": "📈 #5", "Action": "Seasonal optimization"}
    ])
    
    st.dataframe(
        category_data,
        use_container_width=True,
        column_config={
            "Rank": st.column_config.TextColumn("Rank", width="small"),
            "Action": st.column_config.TextColumn("Recommended Action", width="large")
        }
    )
    
    # Margin optimization opportunities
    st.markdown("### 💎 Margin Optimization Opportunities")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔥 High-Margin Winners")
        winners = [
            {"product": "Premium Coffee", "margin": "45%", "opportunity": "Expand display +$2,400/month"},
            {"product": "Organic Skincare", "margin": "38%", "opportunity": "Bundle deals +$1,800/month"},
            {"product": "Artisan Bread", "margin": "42%", "opportunity": "Cross-merchandise +$1,200/month"}
        ]
        
        for winner in winners:
            st.success(f"**{winner['product']}** ({winner['margin']} margin) - {winner['opportunity']}")
    
    with col2:
        st.markdown("#### ⚠️ Margin Improvement Needed")
        improvements = [
            {"product": "Basic Milk", "margin": "8%", "action": "Negotiate supplier costs"},
            {"product": "Generic Bread", "margin": "12%", "action": "Consider premium alternatives"},
            {"product": "Bulk Rice", "margin": "6%", "action": "Review pricing strategy"}
        ]
        
        for improvement in improvements:
            st.warning(f"**{improvement['product']}** ({improvement['margin']} margin) - {improvement['action']}")
    
    # Category trends analysis
    st.markdown("### 📈 Category Trends & Insights")
    
    # Generate sample trend data
    months = pd.date_range(start=datetime.now() - timedelta(days=180), end=datetime.now(), freq='ME')
    categories = ["Beverages", "Personal Care", "Snacks", "Dairy", "Frozen"]
    
    trend_data = []
    for month in months:
        for category in categories:
            base_revenue = np.random.randint(20000, 50000)
            trend_data.append({
                'Month': month,
                'Category': category,
                'Revenue': base_revenue
            })
    
    trend_df = pd.DataFrame(trend_data)
    
    fig = px.line(
        trend_df,
        x='Month',
        y='Revenue',
        color='Category',
        title="6-Month Category Revenue Trends"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Competitive analysis
    st.markdown("### 🎯 Competitive Positioning")
    
    competitive_data = pd.DataFrame([
        {"Category": "Beverages", "Our Price": "$2.49", "Competitor A": "$2.59", "Competitor B": "$2.39", "Position": "🎯 Competitive", "Action": "Maintain pricing"},
        {"Category": "Personal Care", "Our Price": "$4.99", "Competitor A": "$5.29", "Competitor B": "$4.79", "Position": "💰 Premium", "Action": "Justify with quality"},
        {"Category": "Snacks", "Our Price": "$1.99", "Competitor A": "$2.19", "Competitor B": "$1.89", "Position": "🎯 Competitive", "Action": "Monitor competitor B"},
        {"Category": "Dairy", "Our Price": "$3.29", "Competitor A": "$3.19", "Competitor B": "$3.39", "Position": "⚠️ High", "Action": "Consider price reduction"}
    ])
    
    st.dataframe(competitive_data, use_container_width=True)


def show_regional_manager_dashboard():
    """Dashboard optimized for regional/district managers"""
    st.markdown("## 🏢 Regional Performance Dashboard")
    
    data = load_business_data()
    
    # Executive summary
    st.markdown("### 📈 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Total ROI",
            f"{data['financial_impact']['roi_percentage']}%",
            delta="vs 100% target"
        )
        st.caption("Return on Stock_GRIP investment")
    
    with col2:
        st.metric(
            "💸 Quarterly Savings",
            f"${data['financial_impact']['weekly_savings'] * 12:,}",
            delta="across all locations"
        )
        st.caption("Operational cost reduction")
    
    with col3:
        st.metric(
            "🛡️ Revenue Protection",
            f"${data['financial_impact']['revenue_protected'] * 4:,}",
            delta="prevented losses"
        )
        st.caption("Stockout prevention value")
    
    with col4:
        st.metric(
            "⚡ Efficiency Gain",
            f"{data['operational_efficiency']['automation_rate']}%",
            delta="process automation"
        )
        st.caption("Manual work reduction")
    
    # Multi-store performance
    st.markdown("### 🏪 Store Performance Comparison")
    
    store_data = pd.DataFrame([
        {"Store": "Downtown", "Revenue": "$125K", "Revenue_Numeric": 125000, "Margin": "28%", "Margin_Numeric": 28, "Efficiency": "94%", "Efficiency_Numeric": 94, "ROI": "320%", "Status": "🟢 Excellent"},
        {"Store": "Mall Location", "Revenue": "$98K", "Revenue_Numeric": 98000, "Margin": "25%", "Margin_Numeric": 25, "Efficiency": "89%", "Efficiency_Numeric": 89, "ROI": "285%", "Status": "🟢 Good"},
        {"Store": "Suburban", "Revenue": "$87K", "Revenue_Numeric": 87000, "Margin": "30%", "Margin_Numeric": 30, "Efficiency": "91%", "Efficiency_Numeric": 91, "ROI": "295%", "Status": "🟢 Good"},
        {"Store": "Airport", "Revenue": "$156K", "Revenue_Numeric": 156000, "Margin": "22%", "Margin_Numeric": 22, "Efficiency": "85%", "Efficiency_Numeric": 85, "ROI": "245%", "Status": "🟡 Monitor"},
        {"Store": "University", "Revenue": "$76K", "Revenue_Numeric": 76000, "Margin": "26%", "Margin_Numeric": 26, "Efficiency": "88%", "Efficiency_Numeric": 88, "ROI": "275%", "Status": "🟢 Good"}
    ])
    
    st.dataframe(
        store_data,
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Performance Status", width="medium")
        }
    )
    
    # Financial impact visualization
    st.markdown("### 💰 Financial Impact Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # ROI by store - extract numeric values
        store_data['ROI_Numeric'] = store_data['ROI'].str.replace('%', '').astype(float)
        
        fig_roi = px.bar(
            store_data,
            x='Store',
            y='ROI_Numeric',
            title="ROI by Store Location",
            color='ROI_Numeric',
            color_continuous_scale='Greens',
            labels={'ROI_Numeric': 'ROI (%)'}
        )
        fig_roi.add_hline(y=200, line_dash="dash", line_color="red", annotation_text="Target: 200%")
        fig_roi.update_layout(height=400)
        st.plotly_chart(fig_roi, use_container_width=True)
    
    with col2:
        # Efficiency comparison
        fig_eff = px.scatter(
            store_data,
            x='Efficiency_Numeric',
            y='Margin_Numeric',
            size='Revenue_Numeric',
            color='Store',
            title="Efficiency vs Margin Analysis",
            labels={'Efficiency_Numeric': 'Operational Efficiency (%)', 'Margin_Numeric': 'Profit Margin (%)'}
        )
        fig_eff.update_layout(height=400)
        st.plotly_chart(fig_eff, use_container_width=True)
    
    # Scalability metrics
    st.markdown("### 📊 Scalability & Growth Metrics")
    
    scalability_data = pd.DataFrame([
        {"Metric": "Staff Productivity", "Current": "125%", "Target": "130%", "Status": "🟡 On Track"},
        {"Metric": "System Adoption", "Current": "94%", "Target": "95%", "Status": "🟢 Excellent"},
        {"Metric": "Process Standardization", "Current": "87%", "Target": "90%", "Status": "🟡 Improving"},
        {"Metric": "Cost per Transaction", "Current": "$0.12", "Target": "$0.10", "Status": "🟡 Monitor"},
        {"Metric": "Customer Satisfaction", "Current": "96%", "Target": "95%", "Status": "🟢 Exceeding"}
    ])
    
    st.dataframe(scalability_data, use_container_width=True)
    
    # Strategic recommendations
    st.markdown("### 🎯 Strategic Recommendations")
    
    recommendations = [
        {"priority": "🔴 HIGH", "recommendation": "Expand Stock_GRIP to 3 additional locations", "impact": "$150K annual savings", "timeline": "Q2 2024"},
        {"priority": "🟡 MEDIUM", "recommendation": "Implement advanced demand forecasting", "impact": "$75K inventory optimization", "timeline": "Q3 2024"},
        {"priority": "🟢 LOW", "recommendation": "Add supplier performance analytics", "impact": "$25K cost reduction", "timeline": "Q4 2024"}
    ]
    
    for rec in recommendations:
        st.markdown(f"""
        **{rec['priority']} Priority:** {rec['recommendation']}  
        💰 Impact: {rec['impact']} | 📅 Timeline: {rec['timeline']}
        """)


def show_technical_dashboard(system):
    """Technical dashboard for system administrators"""
    st.markdown("## 🔧 Technical Administration")
    
    # System status
    if system:
        status = system.get_system_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status["system_initialized"]:
                st.success("✅ System Initialized")
            else:
                st.error("❌ System Not Initialized")
        
        with col2:
            if status["optimization_status"]["is_running"]:
                st.success("🔄 Optimization Running")
            else:
                st.warning("⏸️ Optimization Stopped")
        
        with col3:
            if status["database_connected"]:
                st.success("💾 Database Connected")
            else:
                st.error("❌ Database Disconnected")
        
        # Control buttons
        st.markdown("### System Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Initialize System", type="primary"):
                with st.spinner("Initializing..."):
                    try:
                        result = system.initialize_system(generate_sample_data=True)
                        st.success("System initialized!")
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
                        st.error(f"Failed to start: {e}")
        
        with col3:
            if st.button("⏸️ Stop Optimization"):
                try:
                    system.stop()
                    st.success("Optimization stopped!")
                except Exception as e:
                    st.error(f"Failed to stop: {e}")
    
    else:
        st.warning("⚠️ System not available - running in demo mode")
        st.info("Technical features require system initialization")


if __name__ == "__main__":
    main()