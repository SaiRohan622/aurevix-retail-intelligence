"""
AUREVIX — Page 4: Product & Category Analytics
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
from dashboard.components.charts import create_category_bar_chart

st.set_page_config(page_title="Product Analytics — AUREVIX", page_icon="📦", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()
loader = DashboardDataLoader()

st.title("Product & Category Analytics")
st.caption("SKU Catalog Optimization & Category Share Analysis")

col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("Catalog SKUs", "32,951", "dim_product unique items")
with col2:
    render_kpi_card("Top Category", "beleza_saude", "$1.44M Gross Revenue")
with col3:
    render_kpi_card("Category Count", "74", "Standardized English categories")

st.markdown("<br>", unsafe_allow_html=True)
df_cat = loader.get_category_performance()
if not df_cat.empty:
    fig = create_category_bar_chart(df_cat, top_n=15)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Product Category Data Mart</div>', unsafe_allow_html=True)
    st.dataframe(df_cat, use_container_width=True)
