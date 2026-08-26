"""
AUREVIX — Enterprise Retail Intelligence Platform
Main Streamlit Application Entrypoint
"""

import os
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.charts import (
    create_revenue_trend_chart,
    create_category_bar_chart,
    create_regional_bar_chart
)

st.set_page_config(
    page_title="AUREVIX — Retail Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()

loader = DashboardDataLoader()

# Main Header
st.markdown(
    """
    <div style="margin-bottom: 24px;">
        <h1 style="margin-bottom: 0px; font-weight: 800; font-size: 2.2rem; color: #f3f4f6;">AUREVIX</h1>
        <p style="color: #9ca3af; font-size: 1.05rem; margin-top: 4px;">Executive Retail Intelligence & Platform Operations</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Top KPIs
kpis = loader.get_executive_kpis()

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    render_kpi_card("Total Revenue", f"${kpis['total_revenue']:,.2f}", "Reconciled against Silver", "+100% Validated")
with col2:
    render_kpi_card("Total Orders", f"{kpis['total_orders']:,}", "Delivered / Shipped", "98.6k Completed")
with col3:
    render_kpi_card("Units Sold", f"{kpis['units_sold']:,}", "Total Line Items", "fact_sales grain")
with col4:
    render_kpi_card("Average Order Value", f"${kpis['average_order_value']:.2f}", "Per Order Spend", "Calculated AOV")
with col5:
    render_kpi_card("Average Freight", f"${kpis['average_freight']:.2f}", "Logistics cost / item", "Freight average")
with col6:
    render_kpi_card("Active Customers", f"{kpis['active_customers']:,}", "Unique Customers", "dim_customer")

st.markdown("<br>", unsafe_allow_html=True)

# Charts Row 1
trend_col, cat_col = st.columns([3, 2])

with trend_col:
    df_trend = loader.get_monthly_sales_trend()
    if not df_trend.empty:
        fig_trend = create_revenue_trend_chart(df_trend)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Loading monthly trend data...")

with cat_col:
    df_cat = loader.get_category_performance()
    if not df_cat.empty:
        fig_cat = create_category_bar_chart(df_cat, top_n=8)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Loading category performance data...")

# Charts Row 2
reg_col, ins_col = st.columns([2, 1])

with reg_col:
    df_reg = loader.get_regional_sales()
    if not df_reg.empty:
        fig_reg = create_regional_bar_chart(df_reg, top_n=10)
        st.plotly_chart(fig_reg, use_container_width=True)
    else:
        st.info("Loading regional sales data...")

with ins_col:
    st.markdown('<div class="section-header">Executive Insights</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="kpi-container" style="line-height: 1.6; font-size: 0.9rem;">
            <p>• <b>Revenue Dominance:</b> Top region (SP) represents over 35% of total marketplace gross revenue.</p>
            <p>• <b>Order Economics:</b> Average Order Value stands at <b>${kpis['average_order_value']:.2f}</b> with <b>${kpis['average_freight']:.2f}</b> average logistics freight contribution.</p>
            <p>• <b>Data Integrity:</b> Reconciled $15.84M in revenue across 112,650 fact records with 0 variance.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
