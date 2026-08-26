"""
AUREVIX — Page 5: Regional & Geographic Analytics
"""
import os
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.charts import create_regional_bar_chart

st.set_page_config(page_title="Regional Analytics — AUREVIX", page_icon="🗺️", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()
loader = DashboardDataLoader()

st.title("Regional Analytics")
st.caption("State-Level Geographical Performance & Logistics Efficiency")

col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("Geographic Locations", "19,019", "dim_location zip codes")
with col2:
    render_kpi_card("Top State (SP)", "41.7%", "Share of total orders")
with col3:
    render_kpi_card("Quarantined Outliers", "29", "0.0019% isolated by DQ Firewall")

st.markdown("<br>", unsafe_allow_html=True)
df_reg = loader.get_regional_sales()
if not df_reg.empty:
    fig = create_regional_bar_chart(df_reg, top_n=15)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_reg, use_container_width=True)
