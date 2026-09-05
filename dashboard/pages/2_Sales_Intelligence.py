"""
AUREVIX — Page 2: Sales Intelligence
Powered by AnalyticsManager: Supports Demo Mode & User Mode.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.components.charts import create_revenue_trend_chart
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.chart_engine import ChartEngine

st.set_page_config(page_title="Sales Intelligence — AUREVIX", page_icon="📈", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
kpis = res.get("kpis", {})

mode_text = f"USER DATA ({res.get('dataset_name', 'Custom')[:15]})" if user_active else "RECONCILED (DEMO)"
render_html(
    f"""
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">📈</div>
            <div>
                <div class="header-title-text">Sales Intelligence & Commercial Performance</div>
                <div class="header-title-sub">Granular transactional analytics and monthly order distributions</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> {mode_text}</span>
        </div>
    </div>
    """
)

col1, col2, col3 = st.columns(3)
with col1:
    rev = float(kpis.get('total_revenue', 15843553.24))
    render_kpi_card("COMMERCIAL REVENUE", f"${rev:,.2f}", "Total Transactional Metric", "↑ Realized", True, icon="💰", color="purple", raw_value="Active Metrics")
with col2:
    orders_cnt = int(kpis.get('total_transactions', len(active_df)))
    render_kpi_card("TRANSACTION VOLUME", f"{orders_cnt:,}", "Recorded volume", "↑ Done", True, icon="🛍️", color="blue", raw_value="Transactions")
with col3:
    aov = float(kpis.get('average_transaction_value', 160.58))
    render_kpi_card("AVERAGE VALUE / TRANSACTION", f"${aov:.2f}", "Net average spend", "↑ Calculated Mean", True, icon="📈", color="gold", raw_value="Revenue / Trans")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

if user_active:
    date_col = kpis.get("date_col")
    metric_col = kpis.get("primary_metric_col")
    if date_col and metric_col:
        c1, c2 = st.columns([1.6, 1.0])
        with c1:
            render_html(
                """
                <div class="ref-panel">
                    <div class="ref-panel-header">
                        <div>
                            <div class="ref-panel-title">Revenue / Metric Trend</div>
                            <div class="ref-panel-subtitle">Aggregated timeline progression from active dataset</div>
                        </div>
                    </div>
                </div>
                """
            )
            fig_trend = ChartEngine.create_time_series_chart(active_df, date_col, metric_col, granularity="Monthly")
            st.plotly_chart(fig_trend, use_container_width=True)
        with c2:
            render_html(
                """
                <div class="ref-panel">
                    <div class="ref-panel-header">
                        <div>
                            <div class="ref-panel-title">Volume Distribution</div>
                            <div class="ref-panel-subtitle">Period frequency breakdown</div>
                        </div>
                    </div>
                </div>
                """
            )
            df_work = active_df[[date_col, metric_col]].dropna().copy()
            df_work["_dt"] = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work = df_work.dropna(subset=["_dt"]).set_index("_dt")
            df_work["_val"] = pd.to_numeric(df_work[metric_col], errors="coerce").fillna(0.0)
            df_ts = df_work["_val"].resample("MS").sum().reset_index()
            if not df_ts.empty:
                df_ts["label"] = df_ts["_dt"].dt.strftime("%b %Y")
                fig_bar = px.bar(df_ts, x="label", y="_val", color_discrete_sequence=["#38bdf8"])
                fig_bar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#CBD5E1", family="Inter, sans-serif", size=12),
                    xaxis=dict(showgrid=False, tickfont=dict(color="#E8EEF7", size=11)), yaxis=dict(showgrid=True, gridcolor="rgba(34, 47, 73, 0.45)", tickfont=dict(color="#CBD5E1", size=11)),
                    margin=dict(l=5, r=5, t=5, b=5), height=240
                )
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No date or numeric metric column found in uploaded dataset.")
else:
    loader = DashboardDataLoader()
    df_trend = loader.get_monthly_sales_trend()
    if not df_trend.empty:
        c1, c2 = st.columns([1.6, 1.0])
        with c1:
            render_html(
                """
                <div class="ref-panel">
                    <div class="ref-panel-header">
                        <div>
                            <div class="ref-panel-title">Monthly Gross Revenue Trend</div>
                            <div class="ref-panel-subtitle">Revenue progression across 24 operational months</div>
                        </div>
                    </div>
                </div>
                """
            )
            fig_trend = create_revenue_trend_chart(df_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

        with c2:
            render_html(
                """
                <div class="ref-panel">
                    <div class="ref-panel-header">
                        <div>
                            <div class="ref-panel-title">Monthly Order Volume</div>
                            <div class="ref-panel-subtitle">Order frequency distribution</div>
                        </div>
                    </div>
                </div>
                """
            )
            df_plot = df_trend.copy()
            if "orders" in df_plot.columns:
                df_plot["orders"] = df_plot["orders"].astype(int)
            fig_bar = px.bar(
                df_plot,
                x="order_year_month",
                y="orders",
                color_discrete_sequence=["#38bdf8"]
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#CBD5E1", family="Inter, sans-serif", size=12),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                margin=dict(l=5, r=5, t=5, b=5),
                height=240
            )
            st.plotly_chart(fig_bar, use_container_width=True)
