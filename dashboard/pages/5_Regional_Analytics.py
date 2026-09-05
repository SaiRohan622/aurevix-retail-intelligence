"""
AUREVIX — Page 5: Regional & Geographic Analytics
State-level marketplace performance, geographic density, and interactive territory drill-downs.
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
from dashboard.components.charts import create_regional_bar_chart
from dashboard.components.filter_bar import render_global_filter_bar
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.chart_engine import ChartEngine

st.set_page_config(page_title="Regional Analytics — AUREVIX", page_icon="🗺️", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
schema = res.get("schema", {})
kpis = res.get("kpis", {})

render_html(
    """
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">🗺️</div>
            <div>
                <div class="header-title-text">Regional & Geographic Analytics</div>
                <div class="header-title-sub">Geographic density, regional performance distribution, and territory inspection</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> GEOGRAPHY ACTIVE</span>
        </div>
    </div>
    """
)

render_global_filter_bar()

reg_col = kpis.get("region_col")
metric_col = kpis.get("primary_metric_col")

if user_active:
    if reg_col and reg_col in active_df.columns and metric_col and metric_col in active_df.columns:
        uniq_regs = active_df[reg_col].nunique()
        top_reg_grp = active_df.groupby(reg_col)[metric_col].sum().sort_values(ascending=False)
        top_reg_name = str(top_reg_grp.index[0]) if not top_reg_grp.empty else "N/A"
        top_reg_val = float(top_reg_grp.iloc[0]) if not top_reg_grp.empty else 0.0

        col1, col2, col3 = st.columns(3)
        with col1:
            render_kpi_card("DISTINCT REGIONS", f"{uniq_regs:,}", f"From `{reg_col}`", "↑ Mapped", True, icon="📍", color="cyan", raw_value=f"Field: {reg_col}")
        with col2:
            render_kpi_card("TOP TERRITORY", top_reg_name[:15], f"${top_reg_val:,.2f}", "↑ Hub Leader", True, icon="🏙️", color="emerald", raw_value="Regional Lead")
        with col3:
            render_kpi_card("TOTAL VOLUME", f"${float(kpis.get('total_revenue', 0.0)):,.2f}", "Sum of Regional Volume", "↑ Evaluated", True, icon="🛡️", color="gold", raw_value="Realized Volume")

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        render_html(
            f"""
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Regional Volume Distribution ({reg_col})</div>
                        <div class="ref-panel-subtitle">Ranked volume by geography from active dataset</div>
                    </div>
                </div>
            </div>
            """
        )
        fig = ChartEngine.create_dimension_bar_chart(active_df, reg_col, metric_col, top_n=10)
        st.plotly_chart(fig, use_container_width=True)

        # ----------------------------------------------------------------------
        # INTERACTIVE REGIONAL DRILL-DOWN
        # ----------------------------------------------------------------------
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_html(
            f"""
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">🔍 Interactive Territory Drill-Down ({reg_col})</div>
                        <div class="ref-panel-subtitle">Select a territory to inspect localized volume and underlying records</div>
                    </div>
                </div>
            </div>
            """
        )
        all_regions = sorted(list(active_df[reg_col].dropna().unique().astype(str)))
        sel_region = st.selectbox(f"Select a {reg_col} to drill into:", all_regions)

        if sel_region:
            df_reg_drill = active_df[active_df[reg_col].astype(str) == sel_region]
            tot_reg_drill_val = float(df_reg_drill[metric_col].sum())
            tot_overall_val = float(active_df[metric_col].sum())
            reg_share = (tot_reg_drill_val / max(1.0, tot_overall_val)) * 100.0

            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric(label=f"Territory Volume ({metric_col})", value=f"${tot_reg_drill_val:,.2f}")
            with r2:
                st.metric(label="Territory Share", value=f"{reg_share:.1f}%")
            with r3:
                st.metric(label="Recorded Records", value=f"{len(df_reg_drill):,} rows")

            with st.expander(f"📋 View all records for `{sel_region}` ({len(df_reg_drill)} rows)", expanded=False):
                st.dataframe(df_reg_drill, use_container_width=True)
    else:
        st.markdown(
            """
            <div style="padding: 24px; border-radius: 8px; background: rgba(22, 32, 53, 0.6); border: 1px solid #192338; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🗺️</div>
                <div style="font-size: 1rem; font-weight: 700; color: #ffffff;">Geographical Dimension Not Detected</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 6px;">
                    Geographical analysis is unavailable because no region, state, city, or location column was detected in the active dataset.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    loader = DashboardDataLoader()
    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card("POSTAL NODES", "19,019", "dim_location zip codes", "↑ Mapped", True, icon="📍", color="cyan", raw_value="Unique Zip Codes")
    with col2:
        render_kpi_card("TOP STATE (SP)", "41.7%", "Share of total orders", "↑ Market Leader", True, icon="🏙️", color="emerald", raw_value="São Paulo Hub")
    with col3:
        render_kpi_card("QUARANTINED OUTLIERS", "29", "0.0019% isolated by DQ Firewall", "↑ Isolated", True, icon="🛡️", color="gold", raw_value="Data Firewall")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    df_reg = loader.get_regional_sales()
    if not df_reg.empty:
        render_html(
            """
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Top 15 States by Sales Volume</div>
                        <div class="ref-panel-subtitle">Gross revenue distribution across Brazilian states</div>
                    </div>
                </div>
            </div>
            """
        )
        fig = create_regional_bar_chart(df_reg, top_n=15)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_reg, use_container_width=True)
