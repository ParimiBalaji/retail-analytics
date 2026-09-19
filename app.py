import streamlit as st
import pandas as pd
import json
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from agent.graph_hybrid import app as agent_app

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Retail Analytics Copilot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. Session State Initialization
# ---------------------------------------------------------
if "active_view" not in st.session_state:
    st.session_state.active_view = "overview"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "id": "msg_default_user",
            "role": "user",
            "content": "Which were the top 5 products by revenue last month?",
            "timestamp": "10:14 AM"
        },
        {
            "id": "msg_default_bot",
            "role": "bot",
            "title": "Top 5 products by revenue",
            "answer_type": "table",
            "content": [
                {"Rank": "1", "Product": "Wireless Headphones", "Category": "Electronics", "Revenue": "₹ 1.2M", "Units": "4,832", "Growth": "↑ 28%"},
                {"Rank": "2", "Product": "Smart Watch", "Category": "Electronics", "Revenue": "₹ 1.0M", "Units": "3,942", "Growth": "↑ 18%"},
                {"Rank": "3", "Product": "Running Shoes", "Category": "Fashion", "Revenue": "₹ 842K", "Units": "2,984", "Growth": "↑ 14%"},
                {"Rank": "4", "Product": "Denim Jacket", "Category": "Fashion", "Revenue": "₹ 620K", "Units": "2,201", "Growth": "↑ 12%"},
                {"Rank": "5", "Product": "Face Serum", "Category": "Beauty", "Revenue": "₹ 580K", "Units": "3,110", "Growth": "↑ 9%"}
            ],
            "route": "SQL",
            "confidence": 94,
            "sql": "SELECT p.ProductName, c.CategoryName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) AS Revenue\nFROM Products p\nJOIN Categories c ON p.CategoryID = c.CategoryID\nJOIN [Order Details] od ON p.ProductID = od.ProductID\nGROUP BY p.ProductID\nORDER BY Revenue DESC\nLIMIT 5;",
            "citations": ["Orders", "Order Details", "Products", "Categories"],
            "trace": {
                "router": "Decision: SQL · Numeric KPI ranking query",
                "planner": "Constraints: Last 30 days · All categories",
                "nl2sql": "Generated SQLite query with JOIN & aggregate SUM",
                "executor": "609,283 rows scanned · Execution time: 42 ms",
                "synthesizer": "Formatted output as typed list[dict]",
                "validation": "Format and confidence validation passed (94%)"
            },
            "timestamp": "10:14 AM"
        }
    ]

if "query_history" not in st.session_state:
    st.session_state.query_history = [
        {"question": "Top 5 products by revenue", "path": "SQL", "confidence": "94%", "status": "✓ Success", "time": "10:14 AM"},
        {"question": "What is the return policy for unopened beverages?", "path": "RAG", "confidence": "88%", "status": "✓ Success", "time": "09:42 AM"},
        {"question": "Why did sales drop in Store 12?", "path": "Hybrid", "confidence": "91%", "status": "✓ Success", "time": "09:15 AM"},
        {"question": "Show customer churn risk summary", "path": "SQL", "confidence": "96%", "status": "✓ Success", "time": "08:50 AM"}
    ]

if "current_trace" not in st.session_state:
    st.session_state.current_trace = st.session_state.messages[1]["trace"]
    st.session_state.current_sql = st.session_state.messages[1]["sql"]

if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""

# ---------------------------------------------------------
# 3. Targeted CSS Fixes (Ensuring 100% Text Visibility & Crisp Layout)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;500;600&display=swap');

    /* Force Light Theme Base Canvas */
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background-color: #f4f7fc !important;
    }

    /* Hide standard Streamlit header and footer */
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }

    /* =========================================================
       1. SIDEBAR STYLING & BUTTON TEXT FIX
       ========================================================= */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
        width: 260px !important;
        padding-top: 0px !important;
    }

    .brand-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 20px 12px;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 16px;
    }
    
    .brand-logo {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        color: #ffffff;
        display: grid;
        place-items: center;
        font-size: 20px;
        font-weight: bold;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }
    
    .brand-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 16px;
        color: #ffffff !important;
        line-height: 1.25;
    }
    
    .brand-subtitle {
        font-size: 11px;
        color: #94a3b8 !important;
        font-weight: 500;
    }

    /* Target ALL text inside sidebar buttons explicitly so icons AND labels render in white/grey */
    section[data-testid="stSidebar"] .stButton button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }

    section[data-testid="stSidebar"] .stButton button p,
    section[data-testid="stSidebar"] .stButton button span,
    section[data-testid="stSidebar"] .stButton button div {
        color: #94a3b8 !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: #1e293b !important;
    }

    section[data-testid="stSidebar"] .stButton button:hover p,
    section[data-testid="stSidebar"] .stButton button:hover span,
    section[data-testid="stSidebar"] .stButton button:hover div {
        color: #ffffff !important;
    }

    /* Active primary button in sidebar */
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #2563eb !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
    }

    section[data-testid="stSidebar"] .stButton button[kind="primary"] p,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] span,
    section[data-testid="stSidebar"] .stButton button[kind="primary"] div {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    .sidebar-cta-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e293b 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 14px;
        padding: 18px;
        color: #ffffff;
        margin-top: 30px;
        margin-bottom: 12px;
    }
    
    .sidebar-cta-title {
        font-size: 13px;
        font-weight: 700;
        line-height: 1.4;
        color: #ffffff !important;
    }

    /* =========================================================
       2. MAIN CANVAS BUTTONS & PROMPT BUTTON FIX
       ========================================================= */
    div[data-testid="stMainBlockContainer"] .stButton button,
    .main .stButton button {
        background-color: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        text-align: left !important;
        width: 100% !important;
        transition: all 0.15s ease !important;
    }

    div[data-testid="stMainBlockContainer"] .stButton button p,
    div[data-testid="stMainBlockContainer"] .stButton button span,
    div[data-testid="stMainBlockContainer"] .stButton button div,
    .main .stButton button p,
    .main .stButton button span,
    .main .stButton button div {
        color: #1d4ed8 !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMainBlockContainer"] .stButton button:hover,
    .main .stButton button:hover {
        background-color: #dbeafe !important;
        border-color: #2563eb !important;
    }

    div[data-testid="stMainBlockContainer"] .stButton button[kind="primary"],
    .main .stButton button[kind="primary"] {
        background-color: #2563eb !important;
        border: none !important;
    }

    div[data-testid="stMainBlockContainer"] .stButton button[kind="primary"] p,
    div[data-testid="stMainBlockContainer"] .stButton button[kind="primary"] span,
    div[data-testid="stMainBlockContainer"] .stButton button[kind="primary"] div,
    .main .stButton button[kind="primary"] p,
    .main .stButton button[kind="primary"] span,
    .main .stButton button[kind="primary"] div {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* =========================================================
       3. SELECTBOX / DROPDOWN FIX (Date Range Filter)
       ========================================================= */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] p,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #0f172a !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="popover"] ul {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
    }

    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * {
        color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* =========================================================
       4. TOPBAR & HEADERS
       ========================================================= */
    .topbar {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        padding: 12px 32px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: -60px;
        margin-left: -4rem;
        margin-right: -4rem;
        margin-bottom: 24px;
        position: sticky;
        top: 0;
        z-index: 99;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    }

    .search-box {
        width: 480px;
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 9px 16px;
        color: #64748b;
        font-size: 13.5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .profile-box {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
    }

    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #2563eb;
        color: #ffffff;
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 14px;
    }

    .view-title-main {
        font-family: 'Outfit', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #0f172a !important;
        margin: 0;
    }

    .view-subtitle-main {
        color: #64748b !important;
        font-size: 13.5px;
        margin-top: 4px;
    }

    /* =========================================================
       5. WHITE CARDS & KPI METRICS (MATCHING REFERENCE IMAGE 1)
       ========================================================= */
    .white-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03);
        margin-bottom: 16px;
    }

    .white-card h3 {
        font-family: 'Outfit', sans-serif;
        font-size: 16px;
        font-weight: 750;
        color: #0f172a !important;
        margin-bottom: 14px;
        margin-top: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .white-card h3 span {
        font-size: 12px;
        color: #2563eb;
        cursor: pointer;
    }

    .reference-kpi {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.03);
    }

    .reference-kpi-top {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }

    .reference-kpi-icon {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: #eff6ff;
        color: #2563eb;
        display: grid;
        place-items: center;
        font-size: 18px;
        font-weight: bold;
    }

    .reference-kpi-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 600;
    }

    .reference-kpi-val {
        font-family: 'Outfit', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: #0f172a !important;
    }

    .reference-kpi-change {
        font-size: 11.5px;
        color: #10b981;
        font-weight: 650;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
    }

    /* Copilot Right Side Panel Drawer */
    .copilot-panel {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
    }

    .copilot-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 12px;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 14px;
    }

    .code-block {
        background: #0b1220;
        color: #93c5fd;
        border-radius: 12px;
        padding: 16px;
        font-family: 'Fira Code', monospace;
        font-size: 12px;
        line-height: 1.6;
        overflow-x: auto;
        border: 1px solid #1e293b;
    }

    /* Dataframe Overrides */
    div[data-testid="stDataFrame"] {
        background: #ffffff !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Database Helper Functions
# ---------------------------------------------------------
DB_PATH = "data/northwind.sqlite"

@st.cache_data(ttl=60)
def load_app_data():
    if not os.path.exists(DB_PATH):
        return {
            "revenue": 12400000, "orders": 48329, "customers": 18942, "aov": 25.7,
            "monthly_df": pd.DataFrame(), "cat_df": pd.DataFrame(), "prod_df": pd.DataFrame(), "cust_df": pd.DataFrame()
        }
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Monthly Revenue & Orders Trend
        monthly_df = pd.read_sql_query("""
            SELECT strftime('%Y-%m', o.OrderDate) as Month,
                   ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue,
                   COUNT(DISTINCT o.OrderID) as Orders
            FROM Orders o
            JOIN [Order Details] od ON o.OrderID = od.OrderID
            WHERE o.OrderDate IS NOT NULL
            GROUP BY Month
            ORDER BY Month ASC
            LIMIT 12;
        """, conn)
        
        # Categories breakdown
        cat_df = pd.read_sql_query("""
            SELECT c.CategoryName,
                   ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
            FROM Categories c
            JOIN Products p ON c.CategoryID = p.CategoryID
            JOIN [Order Details] od ON p.ProductID = od.ProductID
            GROUP BY c.CategoryName
            ORDER BY Revenue DESC;
        """, conn)
        if not cat_df.empty:
            tot = cat_df['Revenue'].sum()
            cat_df['Share'] = (cat_df['Revenue'] / tot * 100).round(1)

        # Products catalog
        prod_df = pd.read_sql_query("""
            SELECT p.ProductID, p.ProductName as Product, c.CategoryName as Category,
                   p.UnitPrice as Price, p.UnitsInStock as Stock, p.UnitsOnOrder as OnOrder,
                   ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue,
                   SUM(od.Quantity) as UnitsSold
            FROM Products p
            JOIN Categories c ON p.CategoryID = c.CategoryID
            JOIN [Order Details] od ON p.ProductID = od.ProductID
            GROUP BY p.ProductID
            ORDER BY Revenue DESC;
        """, conn)

        # Customers list
        cust_df = pd.read_sql_query("""
            SELECT c.CustomerID, c.CompanyName as Customer, c.ContactName as Contact,
                   c.City as Location, c.Country,
                   COUNT(DISTINCT o.OrderID) as Orders,
                   ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as TotalSpend
            FROM Customers c
            JOIN Orders o ON c.CustomerID = o.CustomerID
            JOIN [Order Details] od ON o.OrderID = od.OrderID
            GROUP BY c.CustomerID
            ORDER BY TotalSpend DESC;
        """, conn)

        conn.close()
        return {
            "revenue": 12400000, "orders": 48329, "customers": 18942, "aov": 25.7,
            "monthly_df": monthly_df, "cat_df": cat_df, "prod_df": prod_df, "cust_df": cust_df
        }
    except Exception as e:
        return {
            "revenue": 12400000, "orders": 48329, "customers": 18942, "aov": 25.7,
            "monthly_df": pd.DataFrame(), "cat_df": pd.DataFrame(), "prod_df": pd.DataFrame(), "cust_df": pd.DataFrame()
        }

app_data = load_app_data()

# ---------------------------------------------------------
# 5. Topbar Header Component (Matching Reference Topbar)
# ---------------------------------------------------------
st.markdown("""
<div class="topbar">
    <div class="search-box">
        <span>🔍 &nbsp; Search for insights, products, customers, policies...</span>
        <span style="background: #e2e8f0; padding: 2px 7px; border-radius: 6px; font-size: 11px; font-weight: 700; color: #475569;">Ctrl K</span>
    </div>
    <div class="profile-box">
        <span style="color:#2563eb; font-size:18px;">🔔</span>
        <div class="avatar">SG</div>
        <div>
            <b style="color: #0f172a; font-weight:750;">Sneha Sharma</b><br>
            <small style="color: #64748b; font-weight:500;">Retail Manager</small>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. Dark Sidebar Navigation (Explicit Icon + Text Rendering)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand-container">
        <div class="brand-logo">🛍️</div>
        <div>
            <div class="brand-title">Retail Analytics<br>Copilot</div>
            <div class="brand-subtitle">AI-Powered Retail Insights</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    def nav_btn(label, icon, view_id):
        is_active = (st.session_state.active_view == view_id)
        btn_kind = "primary" if is_active else "secondary"
        if st.button(f"{icon} &nbsp; {label}", key=f"nav_{view_id}", use_container_width=True, type=btn_kind):
            st.session_state.active_view = view_id
            st.rerun()

    nav_btn("Overview", "🏠", "overview")
    nav_btn("AI Copilot", "💬", "copilot")
    nav_btn("Analytics", "📊", "analytics")
    nav_btn("Products", "📦", "products")
    nav_btn("Customers", "👥", "customers")
    nav_btn("Knowledge Base", "📖", "sources")
    nav_btn("Data Sources", "🗄️", "datasources")
    nav_btn("Query History", "🕒", "history")
    nav_btn("Settings", "⚙️", "settings")

    st.markdown("""
    <div class="sidebar-cta-card">
        <div class="sidebar-cta-title">Turn your retail data into smarter decisions with AI.</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. VIEW 1: OVERVIEW (MATCHING REFERENCE IMAGE 1 PERFECTLY)
# ---------------------------------------------------------
if st.session_state.active_view == "overview":
    # Header Title & Filter
    v_col1, v_col2 = st.columns([3, 1])
    with v_col1:
        st.markdown("""
        <div>
            <h1 class="view-title-main">Good morning, Sneha! 👋</h1>
            <div class="view-subtitle-main">Here's what's happening in your retail business today. &nbsp; <i style="color:#64748b;">"Smarter data. Happier customers. Stronger retail."</i></div>
        </div>
        """, unsafe_allow_html=True)
    with v_col2:
        st.selectbox("Date Range", ["Last 30 days", "Last 90 days", "This Year"], index=0, label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3-Column Layout: Dashboard Grid (Left 72%) + Copilot Drawer (Right 28%)
    dash_col, copilot_drawer_col = st.columns([2.5, 1])

    with dash_col:
        # Top 4 KPI Cards
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown("""
            <div class="reference-kpi">
                <div class="reference-kpi-top">
                    <div class="reference-kpi-icon">₹</div>
                    <div>
                        <div class="reference-kpi-label">Total Revenue</div>
                        <div class="reference-kpi-val">₹ 12.4M</div>
                    </div>
                </div>
                <div class="reference-kpi-change">↑ 12.5% vs previous period</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown("""
            <div class="reference-kpi">
                <div class="reference-kpi-top">
                    <div class="reference-kpi-icon">🛒</div>
                    <div>
                        <div class="reference-kpi-label">Total Orders</div>
                        <div class="reference-kpi-val">48,329</div>
                    </div>
                </div>
                <div class="reference-kpi-change">↑ 8.3% vs previous period</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown("""
            <div class="reference-kpi">
                <div class="reference-kpi-top">
                    <div class="reference-kpi-icon">👥</div>
                    <div>
                        <div class="reference-kpi-label">Active Customers</div>
                        <div class="reference-kpi-val">18,942</div>
                    </div>
                </div>
                <div class="reference-kpi-change">↑ 14.2% vs previous period</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown("""
            <div class="reference-kpi">
                <div class="reference-kpi-top">
                    <div class="reference-kpi-icon">%</div>
                    <div>
                        <div class="reference-kpi-label">Conversion Rate</div>
                        <div class="reference-kpi-val">4.8%</div>
                    </div>
                </div>
                <div class="reference-kpi-change">↑ 0.6% vs previous period</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sales Trend + Category Performance
        c_left, c_right = st.columns([1.5, 1])
        with c_left:
            st.markdown('<div class="white-card"><h3>Sales Trend</h3>', unsafe_allow_html=True)
            m_df = app_data['monthly_df']
            if not m_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=m_df['Month'], y=m_df['Revenue'], name='Revenue', marker_color='#93c5fd', opacity=0.85))
                fig.add_trace(go.Scatter(x=m_df['Month'], y=m_df['Revenue'] * 1.1, name='Orders', line=dict(color='#2563eb', width=3, shape='spline')))
                fig.update_layout(height=180, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1, x=1, font=dict(color='#0f172a')))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="white-card"><h3>Revenue by Category</h3>', unsafe_allow_html=True)
            fig_pie = px.pie(
                values=[28, 22, 18, 12, 10, 10],
                names=['Electronics', 'Fashion', 'Home & Living', 'Beauty & Personal Care', 'Groceries', 'Others'],
                hole=0.6, color_discrete_sequence=['#2563eb', '#7c3aed', '#ec4899', '#f59e0b', '#10b981', '#94a3b8']
            )
            fig_pie.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', showlegend=True, legend=dict(font=dict(size=10, color='#0f172a')))
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Top Products + Top Stores
        t_left, t_right = st.columns([1.2, 1])
        with t_left:
            st.markdown('<div class="white-card"><h3>Top Performing Products <span>View all</span></h3>', unsafe_allow_html=True)
            top_p_data = pd.DataFrame([
                {"#": 1, "Product": "🎧 Wireless Headphones", "Revenue": "₹ 1.2M", "Units Sold": "4,832", "Growth": "↑ 28%"},
                {"#": 2, "Product": "⌚ Smart Watch", "Revenue": "₹ 1.0M", "Units Sold": "3,942", "Growth": "↑ 18%"},
                {"#": 3, "Product": "👟 Running Shoes", "Revenue": "₹ 842K", "Units Sold": "2,984", "Growth": "↑ 14%"},
                {"#": 4, "Product": "🧥 Denim Jacket", "Revenue": "₹ 620K", "Units Sold": "2,201", "Growth": "↑ 12%"},
                {"#": 5, "Product": "🧴 Face Serum", "Revenue": "₹ 580K", "Units Sold": "3,110", "Growth": "↑ 9%"}
            ])
            st.dataframe(top_p_data, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with t_right:
            st.markdown('<div class="white-card"><h3>Top Stores by Revenue <span>View all</span></h3>', unsafe_allow_html=True)
            top_s_data = pd.DataFrame([
                {"#": 1, "Store": "Mumbai - BKC", "Revenue": "₹ 2.1M", "Growth": "↑ 18%"},
                {"#": 2, "Store": "Delhi - CP", "Revenue": "₹ 1.8M", "Growth": "↑ 14%"},
                {"#": 3, "Store": "Bangalore - MG Rd", "Revenue": "₹ 1.6M", "Growth": "↑ 12%"},
                {"#": 4, "Store": "Hyderabad - Hitech", "Revenue": "₹ 1.2M", "Growth": "↑ 10%"},
                {"#": 5, "Store": "Chennai - T Nagar", "Revenue": "₹ 1.0M", "Growth": "↑ 8%"}
            ])
            st.dataframe(top_s_data, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Quick Insights Row
        st.markdown("""
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; margin-top:8px;">
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:12px; padding:12px; font-size:12px; color:#047857;">
                📊 <b>Revenue is 12.5% higher</b><br>than the previous period.
            </div>
            <div style="background:#faf5ff; border:1px solid #e9d5ff; border-radius:12px; padding:12px; font-size:12px; color:#6b21a8;">
                👑 <b>Electronics is your top</b><br>performing category.
            </div>
            <div style="background:#fdf2f8; border:1px solid #fbcfe8; border-radius:12px; padding:12px; font-size:12px; color:#be185d;">
                👥 <b>New customer sign-ups</b><br>increased by 22%.
            </div>
            <div style="background:#fffbe6; border:1px solid #ffe58f; border-radius:12px; padding:12px; font-size:12px; color:#b45309;">
                ⚠️ <b>3 products are at risk</b><br>of stockout.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Right Copilot Panel (Matching Reference Image 1 Right Side)
    with copilot_drawer_col:
        st.markdown("""
        <div class="copilot-panel">
            <div class="copilot-header">
                <div>
                    <b style="font-size:15px; color:#0f172a; font-weight:800;">✦ Retail Copilot</b>
                </div>
                <span style="color:#10b981; font-size:12px; font-weight:700;">● Online</span>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:14px; font-size:13px; color:#0f172a; margin-bottom:16px; line-height:1.5;">
                Hello Sneha! 👋<br>
                I'm your <b>Retail Analytics Copilot</b>.<br><br>
                You can ask me questions about your sales, customers, products, inventory or company policies.
            </div>
            <b style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase;">TRY ASKING:</b>
            <div style="margin-top:10px;">
        """, unsafe_allow_html=True)

        prompts = [
            "What were the top 5 products by revenue last month?",
            "Why did sales drop in Store 12?",
            "Which category is growing the fastest?",
            "Show customer churn risk summary.",
            "Compare this quarter's performance with last year."
        ]

        for p in prompts:
            if st.button(p, key=f"copilot_drawer_{p}", use_container_width=True):
                st.session_state.pending_question = p
                st.session_state.active_view = "copilot"
                st.rerun()

        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. VIEW 2: AI COPILOT WORKSPACE
# ---------------------------------------------------------
elif st.session_state.active_view == "copilot":
    st.markdown("""
    <div>
        <h1 class="view-title-main">💬 AI Copilot Workspace</h1>
        <div class="view-subtitle-main">Ask questions across your database, analytics and markdown policies.</div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    c_left, c_right = st.columns([2.5, 1])

    with c_left:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div style="background:#2563eb; color:#ffffff; padding:12px 16px; border-radius:14px 14px 2px 14px; max-width:80%; margin-left:auto; font-size:13px; margin-bottom:14px;">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                conf = msg.get("confidence", 85)
                route = msg.get("route", "hybrid").upper()
                st.markdown(f"""
                <div style="background:#ffffff; border:1px solid #cbd5e1; padding:16px; border-radius:14px 14px 14px 2px; max-width:90%; font-size:13px; margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <b style="font-size:15px; color:#0f172a;">{msg.get('title', 'Answer')}</b>
                        <span style="background:#eff6ff; color:#1d4ed8; padding:3px 8px; border-radius:6px; font-weight:700; font-size:11px;">{route}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                content = msg.get("content")
                if isinstance(content, list):
                    st.dataframe(pd.DataFrame(content), use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"<div style='color:#0f172a;'>{content}</div>", unsafe_allow_html=True)

                st.markdown(f"""
                    <div style="margin-top:12px; font-size:12px; color:#64748b;">Confidence: <b style="color:#10b981;">{conf}%</b></div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Composer Input
        with st.form("copilot_form", clear_on_submit=True):
            f1, f2 = st.columns([5, 1])
            with f1:
                q_in = st.text_input("Question", value=st.session_state.pending_question, placeholder="Ask me anything...", label_visibility="collapsed")
            with f2:
                q_sub = st.form_submit_button("Send ➤", type="primary", use_container_width=True)

        if q_sub and q_in.strip():
            q = q_in.strip()
            st.session_state.pending_question = ""
            st.session_state.messages.append({"id": f"u_{datetime.now().timestamp()}", "role": "user", "content": q, "timestamp": "Now"})
            
            with st.spinner("🤖 Copilot processing query..."):
                try:
                    res = agent_app.invoke({"question": q, "format_hint": "", "router_decision": "", "retrieved_docs": [], "sql_query": "", "sql_result": "", "sql_error": None, "retry_count": 0, "final_answer": "", "explanation": "", "citations": []})
                    st.session_state.messages.append({
                        "id": f"b_{datetime.now().timestamp()}", "role": "bot", "title": q,
                        "content": res.get("final_answer", "Completed"), "route": res.get("router_decision", "hybrid").upper(),
                        "confidence": 92, "sql": res.get("sql_query", ""), "citations": res.get("citations", []),
                        "trace": {"router": "Decision executed", "planner": "Docs retrieved", "synthesizer": "Output parsed"}
                    })
                except Exception as e:
                    st.error(f"Error: {e}")
            st.rerun()

    with c_right:
        st.markdown("""
        <div class="white-card">
            <h3>Suggested Questions</h3>
        """, unsafe_allow_html=True)
        sugs = [
            "What were the top 5 products by revenue last month?",
            "Why did sales drop in Store 12?",
            "Which category is growing the fastest?",
            "Show customer churn risk summary.",
            "Compare this quarter's performance with last year."
        ]
        for s in sugs:
            if st.button(s, key=f"sug_cop_{s}", use_container_width=True):
                st.session_state.pending_question = s
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. VIEW 3: ANALYTICS (MATCHING REFERENCE IMAGE 2)
# ---------------------------------------------------------
elif st.session_state.active_view == "analytics":
    v_col1, v_col2 = st.columns([3, 1])
    with v_col1:
        st.markdown("""
        <div>
            <h1 class="view-title-main">📊 Analytics Dashboard</h1>
            <div class="view-subtitle-main">Explore key metrics and trends across your retail business.</div>
        </div>
        """, unsafe_allow_html=True)
    with v_col2:
        st.button("📥 Export Report", type="primary", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">₹</div>
                <div>
                    <div class="reference-kpi-label">Total Revenue</div>
                    <div class="reference-kpi-val">₹ 12.4M</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 12.5% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">🛒</div>
                <div>
                    <div class="reference-kpi-label">Total Orders</div>
                    <div class="reference-kpi-val">48,329</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 8.3% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">👥</div>
                <div>
                    <div class="reference-kpi-label">Active Customers</div>
                    <div class="reference-kpi-val">18,942</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 14.2% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">🏷️</div>
                <div>
                    <div class="reference-kpi-label">Average Order Value</div>
                    <div class="reference-kpi-val">₹ 25.7</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 4.1% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    a1, a2, a3 = st.columns([1.5, 1, 1])
    with a1:
        st.markdown('<div class="white-card"><h3>Sales Trend</h3>', unsafe_allow_html=True)
        m_df = app_data['monthly_df']
        if not m_df.empty:
            fig = px.line(m_df, x='Month', y='Revenue', markers=True)
            fig.update_traces(line_color='#2563eb', line_width=3)
            fig.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with a2:
        st.markdown('<div class="white-card"><h3>Category Performance</h3>', unsafe_allow_html=True)
        fig_pie = px.pie(values=[28, 22, 18, 12, 10, 10], names=['Electronics', 'Fashion', 'Home & Living', 'Beauty & Personal Care', 'Groceries', 'Others'], hole=0.55)
        fig_pie.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with a3:
        st.markdown('<div class="white-card"><h3>Sales by Region</h3>', unsafe_allow_html=True)
        regions_df = pd.DataFrame([
            {"#": 1, "Region": "Maharashtra", "Share": "28%"},
            {"#": 2, "Region": "Delhi", "Share": "18%"},
            {"#": 3, "Region": "Karnataka", "Share": "14%"},
            {"#": 4, "Region": "Telangana", "Share": "12%"},
            {"#": 5, "Region": "Tamil Nadu", "Share": "10%"}
        ])
        st.dataframe(regions_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 10. VIEW 4: PRODUCTS (MATCHING REFERENCE IMAGE 3)
# ---------------------------------------------------------
elif st.session_state.active_view == "products":
    v_col1, v_col2 = st.columns([3, 1])
    with v_col1:
        st.markdown("""
        <div>
            <h1 class="view-title-main">📦 Products</h1>
            <div class="view-subtitle-main">Explore product performance, inventory levels, and category insights.</div>
        </div>
        """, unsafe_allow_html=True)
    with v_col2:
        st.button("+ Add Product", type="primary", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">📦</div>
                <div>
                    <div class="reference-kpi-label">Total Products</div>
                    <div class="reference-kpi-val">1,284</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 12.5% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">🏷️</div>
                <div>
                    <div class="reference-kpi-label">Active Products</div>
                    <div class="reference-kpi-val">1,176</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 8.3% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon" style="color:#b45309; background:#fffbe6;">⚠️</div>
                <div>
                    <div class="reference-kpi-label">Low Stock Products</div>
                    <div class="reference-kpi-val">24</div>
                </div>
            </div>
            <div class="reference-kpi-change" style="color:#b45309;">↑ 60% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon" style="color:#dc2626; background:#fef2f2;">🚫</div>
                <div>
                    <div class="reference-kpi-label">Out of Stock</div>
                    <div class="reference-kpi-val">8</div>
                </div>
            </div>
            <div class="reference-kpi-change" style="color:#dc2626;">↑ 33% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    p_table_col, p_detail_col = st.columns([1.8, 1])

    with p_table_col:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        catalog_items = pd.DataFrame([
            {"#": 1, "Product": "🎧 Wireless Headphones", "Category": "Electronics", "Price": "₹ 12,999", "Units Sold": "4,832", "Revenue": "₹ 1,24,0382", "Stock Status": "In Stock"},
            {"#": 2, "Product": "⌚ Smart Watch", "Category": "Electronics", "Price": "₹ 8,999", "Units Sold": "3,942", "Revenue": "₹ 1,01,2450", "Stock Status": "In Stock"},
            {"#": 3, "Product": "👟 Running Shoes", "Category": "Fashion", "Price": "₹ 5,999", "Units Sold": "2,984", "Revenue": "₹ 842,391", "Stock Status": "In Stock"},
            {"#": 4, "Product": "🧥 Denim Jacket", "Category": "Fashion", "Price": "₹ 4,999", "Units Sold": "2,201", "Revenue": "₹ 620,112", "Stock Status": "Low Stock"},
            {"#": 5, "Product": "🧴 Face Serum", "Category": "Beauty", "Price": "₹ 2,499", "Units Sold": "3,110", "Revenue": "₹ 580,221", "Stock Status": "In Stock"}
        ])

        st.dataframe(catalog_items, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with p_detail_col:
        st.markdown("""
        <div class="white-card">
            <div style="font-size:48px; text-align:center; margin-bottom:10px;">🎧</div>
            <h3 style="margin:0; font-size:18px; color:#0f172a;">Wireless Headphones</h3>
            <div style="color:#64748b; font-size:12px; margin-top:2px;">Premium noise-canceling headphones</div>
            <div style="margin-top:14px; font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; color:#0f172a;">
                ₹ 12,999 <span style="font-size:12px; color:#f59e0b; font-weight:600;">★ 4.6 (1,248 reviews)</span>
            </div>
            <hr style="border:none; border-top:1px solid #f1f5f9; margin:14px 0;">
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; text-align:center;">
                <div style="background:#f8fafc; padding:8px; border-radius:8px;">
                    <div style="font-size:10px; color:#64748b;">Units Sold</div>
                    <div style="font-size:14px; font-weight:800; color:#0f172a;">4,832</div>
                </div>
                <div style="background:#f8fafc; padding:8px; border-radius:8px;">
                    <div style="font-size:10px; color:#64748b;">Revenue</div>
                    <div style="font-size:14px; font-weight:800; color:#0f172a;">₹ 1.24M</div>
                </div>
                <div style="background:#f8fafc; padding:8px; border-radius:8px;">
                    <div style="font-size:10px; color:#64748b;">Margin</div>
                    <div style="font-size:14px; font-weight:800; color:#0f172a;">32%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 11. VIEW 5: CUSTOMERS (MATCHING REFERENCE IMAGE 4)
# ---------------------------------------------------------
elif st.session_state.active_view == "customers":
    v_col1, v_col2 = st.columns([3, 1])
    with v_col1:
        st.markdown("""
        <div>
            <h1 class="view-title-main">👥 Customers</h1>
            <div class="view-subtitle-main">Analyze customer behavior, segments, and lifetime value.</div>
        </div>
        """, unsafe_allow_html=True)
    with v_col2:
        st.button("+ Add Customer", type="primary", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon">👥</div>
                <div>
                    <div class="reference-kpi-label">Total Customers</div>
                    <div class="reference-kpi-val">18,942</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 14.2% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon" style="color:#7c3aed; background:#faf5ff;">👤</div>
                <div>
                    <div class="reference-kpi-label">New Customers</div>
                    <div class="reference-kpi-val">3,281</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 22% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon" style="color:#10b981; background:#ecfdf5;">🔄</div>
                <div>
                    <div class="reference-kpi-label">Repeat Customers</div>
                    <div class="reference-kpi-val">15,661</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 10.8% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown("""
        <div class="reference-kpi">
            <div class="reference-kpi-top">
                <div class="reference-kpi-icon" style="color:#f59e0b; background:#fffbe6;">🏷️</div>
                <div>
                    <div class="reference-kpi-label">Average Order Value</div>
                    <div class="reference-kpi-val">₹ 25.7</div>
                </div>
            </div>
            <div class="reference-kpi-change">↑ 4.1% vs previous period</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    top_cust_data = pd.DataFrame([
        {"#": 1, "Customer": "Amit Verma", "Location": "Bangalore", "Orders": 24, "Total Spend": "₹ 1,24,350", "Segment": "Loyal"},
        {"#": 2, "Customer": "Priya Sharma", "Location": "Delhi", "Orders": 18, "Total Spend": "₹ 1,02,310", "Segment": "Loyal"},
        {"#": 3, "Customer": "Rahul Mehta", "Location": "Mumbai", "Orders": 16, "Total Spend": "₹ 98,420", "Segment": "Regular"}
    ])
    st.markdown('<div class="white-card"><h3>Top Customers by Revenue</h3>', unsafe_allow_html=True)
    st.dataframe(top_cust_data, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 12. OTHER VIEWS (Sources, Data Sources, History, Trace, Settings)
# ---------------------------------------------------------
elif st.session_state.active_view in ["sources", "datasources"]:
    st.markdown('<div><h1 class="view-title-main">📖 Knowledge Base & Data Sources</h1></div><br>', unsafe_allow_html=True)
    st.markdown('<div class="white-card"><b>product_policy.md</b><br>Return window policies.<br><br><b>northwind.sqlite</b><br>Retail transactions database.</div>', unsafe_allow_html=True)

elif st.session_state.active_view == "history":
    st.markdown('<div><h1 class="view-title-main">🕒 Query History</h1></div><br>', unsafe_allow_html=True)
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    hist_df = pd.DataFrame(st.session_state.query_history)
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.active_view == "trace":
    st.markdown('<div><h1 class="view-title-main">⌁ Agent Trace Observability</h1></div><br>', unsafe_allow_html=True)
    st.markdown('<div class="white-card"><h3>Generated SQL Query</h3>', unsafe_allow_html=True)
    sql_code = st.session_state.current_sql or "SELECT * FROM Products LIMIT 5;"
    st.markdown(f'<div class="code-block">{sql_code}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.active_view == "settings":
    st.markdown('<div><h1 class="view-title-main">⚙️ Settings</h1></div><br>', unsafe_allow_html=True)
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.text_input("LLM Model Endpoint", value="Phi-3.5 3.8B Mini (Ollama Local)")
    st.text_input("SQLite Database Path", value="data/northwind.sqlite")
    st.markdown('</div>', unsafe_allow_html=True)
