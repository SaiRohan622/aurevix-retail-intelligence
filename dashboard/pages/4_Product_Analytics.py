"""
AUREVIX — Page 4: Product & Dimensional Analytics
SKU catalog intelligence, category volume rankings, and interactive dimensional drill-downs.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.components.charts import create_category_bar_chart
from dashboard.components.filter_bar import render_global_filter_bar
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.chart_engine import ChartEngine

st.set_page_config(page_title="Product Analytics — AUREVIX", page_icon="📦", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
schema = res.get("schema", {})
kpis = res.get("kpis", {})

domain_name = schema.get("domain", "Retail & E-Commerce")
dim_label = "Department" if "HR" in domain_name else ("Channel" if "Marketing" in domain_name else "Product / Category")

render_html(
    f"""
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">📦</div>
            <div>
                <div class="header-title-text">{dim_label} Analytics & Drill-Down</div>
                <div class="header-title-sub">Dimensional volume rankings, contribution share, and interactive segment inspection</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> {domain_name.upper()}</span>
        </div>
    </div>
    """
)

render_global_filter_bar()

cat_col = kpis.get("category_col") or kpis.get("product_col")
metric_col = kpis.get("primary_metric_col")

if user_active:
    if cat_col and cat_col in active_df.columns and metric_col and metric_col in active_df.columns:
        uniq_cats = active_df[cat_col].nunique()
        top_cat_grp = active_df.groupby(cat_col)[metric_col].sum().sort_values(ascending=False)
        top_cat_name = str(top_cat_grp.index[0]) if not top_cat_grp.empty else "N/A"
        top_cat_val = float(top_cat_grp.iloc[0]) if not top_cat_grp.empty else 0.0

        col1, col2, col3 = st.columns(3)
        with col1:
            render_kpi_card("DISTINCT SEGMENTS", f"{uniq_cats:,}", f"Column `{cat_col}`", "↑ Identified", True, icon="📦", color="blue", raw_value=f"Field: {cat_col}")
        with col2:
            render_kpi_card("TOP CONTRIBUTOR", top_cat_name[:15], f"${top_cat_val:,.2f} Total", "↑ Leader", True, icon="🏆", color="purple", raw_value="Leading Segment")
        with col3:
            render_kpi_card("AVG / SEGMENT", f"${float(kpis.get('total_revenue', 0.0))/max(1, uniq_cats):,.2f}", "Mean segment density", "↑ Calculated", True, icon="🌐", color="emerald", raw_value="Distribution")

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        render_html(
            f"""
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Ranked {cat_col} Volume Distribution</div>
                        <div class="ref-panel-subtitle">Primary volume contribution ranked by `{cat_col}` from active dataset</div>
                    </div>
                </div>
            </div>
            """
        )
        fig = ChartEngine.create_dimension_bar_chart(active_df, cat_col, metric_col, top_n=10)
        st.plotly_chart(fig, use_container_width=True)

        # ----------------------------------------------------------------------
        # INTERACTIVE DIMENSIONAL DRILL-DOWN
        # ----------------------------------------------------------------------
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_html(
            f"""
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">🔍 Interactive Drill-Down Explorer ({cat_col})</div>
                        <div class="ref-panel-subtitle">Select a segment to inspect underlying distribution, volume share, and source records</div>
                    </div>
                </div>
            </div>
            """
        )
        all_segments = sorted(list(active_df[cat_col].dropna().unique().astype(str)))
        sel_segment = st.selectbox(f"Select a {cat_col} to drill into:", all_segments)

        if sel_segment:
            df_drill = active_df[active_df[cat_col].astype(str) == sel_segment]
            tot_seg_val = float(df_drill[metric_col].sum())
            tot_overall_val = float(active_df[metric_col].sum())
            seg_share = (tot_seg_val / max(1.0, tot_overall_val)) * 100.0

            d1, d2, d3 = st.columns(3)
            with d1:
                st.metric(label=f"Selected Segment Volume ({metric_col})", value=f"${tot_seg_val:,.2f}")
            with d2:
                st.metric(label="Contribution Share", value=f"{seg_share:.1f}%")
            with d3:
                st.metric(label="Underlying Records", value=f"{len(df_drill):,} rows")

            with st.expander(f"📋 View all underlying records for `{sel_segment}` ({len(df_drill)} rows)", expanded=False):
                st.dataframe(df_drill, use_container_width=True)
    else:
        st.markdown(
            """
            <div style="padding: 24px; border-radius: 8px; background: rgba(22, 32, 53, 0.6); border: 1px solid #192338; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📦</div>
                <div style="font-size: 1rem; font-weight: 700; color: #ffffff;">Dimension Column Not Detected</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 6px;">
                    Dimensional analytics are unavailable because no category, department, or product column was detected in the active dataset.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    loader = DashboardDataLoader()
    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card("CATALOG SKUs", "32,951", "dim_product unique items", "↑ Cataloged", True, icon="📦", color="blue", raw_value="Active Products")
    with col2:
        render_kpi_card("TOP CATEGORY", "beleza_saude", "$1.44M Gross Revenue", "↑ Leader", True, icon="🏆", color="purple", raw_value="Health & Beauty")
    with col3:
        render_kpi_card("STANDARDIZED CATEGORIES", "74", "Standardized translations", "↑ Mapped", True, icon="🌐", color="emerald", raw_value="Full Catalog")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    df_cat = loader.get_category_performance()
    if not df_cat.empty:
        render_html(
            """
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Top 15 Categories by Sales Volume</div>
                        <div class="ref-panel-subtitle">Revenue volume ranked by product category</div>
                    </div>
                </div>
            </div>
            """
        )
        fig = create_category_bar_chart(df_cat, top_n=15)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_cat, use_container_width=True)
