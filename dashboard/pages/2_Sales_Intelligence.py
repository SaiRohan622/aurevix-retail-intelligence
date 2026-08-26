"""
AUREVIX — Page 2: Sales Intelligence
"""
import os
import sys
from pathlib import Path
import streamlit as st
import plotly.express as px

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card

st.set_page_config(page_title="Sales Intelligence — AUREVIX", page_icon="📈", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()
loader = DashboardDataLoader()

st.title("Sales Intelligence")
st.caption("Deep-Dive Commercial Performance & Granular Order Breakdown")

kpis = loader.get_executive_kpis()
col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("Marketplace Revenue", f"${kpis['total_revenue']:,.2f}", "Total product + freight value")
with col2:
    render_kpi_card("Order Volume", f"{kpis['total_orders']:,}", "Completed transactions")
with col3:
    render_kpi_card("Calculated AOV", f"${kpis['average_order_value']:.2f}", "Net average cart value")

st.markdown("<br>", unsafe_allow_html=True)
df_trend = loader.get_monthly_sales_trend()
if not df_trend.empty:
    fig = px.bar(df_trend, x="order_year_month", y="orders", title="Monthly Order Volume Distribution", color="orders", color_continuous_scale="Blues")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9ca3af"))
    st.plotly_chart(fig, use_container_width=True)
