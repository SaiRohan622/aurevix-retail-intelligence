"""
AUREVIX — Universal Business Intelligence & Executive Command Center
Dynamic, Domain-Aware, Target-Tracking, Forecasting, and Explainable BI Platform.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.charts import (
    create_revenue_trend_chart,
    create_category_donut_chart,
    create_regional_bar_chart
)
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.components.filter_bar import render_global_filter_bar
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.forecast_engine import ForecastEngine
from dashboard.analytics.story_engine import DataStoryEngine
from dashboard.analytics.recommendation_engine import RecommendationEngine
from dashboard.analytics.kpi_explainer import KPIExplainer

st.set_page_config(
    page_title="Executive Command Center — AUREVIX BI",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

from dashboard.analytics.auth_manager import AuthManager
AuthManager.render_top_auth_bar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
schema = res.get("schema", {})
prof = res.get("profile", {})
kpis = res.get("kpis", {})
active_filters = st.session_state.get("active_filters", {})

domain_name = schema.get("domain", "Retail & E-Commerce")
status_label = f"USER DATASET: {res.get('dataset_name', 'Active')[:18]}" if user_active else "DEMO MODE (OLIST PRODUCTION)"

# ==============================================================================
# PERSISTENT GLOBAL ANALYSIS CONTEXT BANNER
# ==============================================================================
filter_tag = ", ".join([f"{k}: {v}" for k, v in active_filters.items() if v]) if active_filters else "None (Full Dataset)"
date_tag = str(active_filters.get("date_range", "All Dates")) if active_filters.get("date_range") else "Full Timeline"
q_score = float(prof.get("quality_score", 99.998)) if user_active else 99.9981

render_html(
    f"""
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">🌌</div>
            <div>
                <div class="header-title-text">AUREVIX Universal Business Intelligence</div>
                <div class="header-title-sub">Multi-Domain Analytics, Statistical Forecasting, Goal Tracking & Autonomous Insights</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> {status_label}</span>
        </div>
    </div>
    """
)

# Global Analysis Context Pill
render_html(
    f"""
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; background: rgba(15, 23, 42, 0.6); padding: 8px 14px; border-radius: 8px; border: 1px solid #1e293b; font-size: 0.78rem; color: #94a3b8; align-items: center;">
        <div>📁 <b>DATASET:</b> <span style="color: #38bdf8;">{res.get('dataset_name', 'Olist Production Gold') if user_active else 'Olist Gold Lakehouse'}</span></div>
        <div style="color: #475569;">|</div>
        <div>🔢 <b>RECORDS:</b> <span style="color: #f8fafc;">{len(active_df):,} rows</span></div>
        <div style="color: #475569;">|</div>
        <div>🏷️ <b>DOMAIN:</b> <span style="color: #a855f7;">{domain_name}</span></div>
        <div style="color: #475569;">|</div>
        <div>🔍 <b>ACTIVE FILTERS:</b> <span style="color: #f59e0b;">{filter_tag}</span></div>
        <div style="color: #475569;">|</div>
        <div>🛡️ <b>DQ SCORE:</b> <span style="color: #10b981;">{q_score:.1f}%</span></div>
    </div>
    """
)

if user_active:
    render_global_filter_bar()

# ------------------------------------------------------------------------------
# DASHBOARD VIEW VS CUSTOMIZER TOGGLE & TOP FINDINGS
# ------------------------------------------------------------------------------
tb1, tb2 = st.columns([1.6, 1.0])
with tb1:
    top_findings_btn = st.button("💡 Analyze My Dataset (Top Findings)", use_container_width=True)
with tb2:
    edit_mode = st.toggle("🛠️ Edit Dashboard Layout", value=False)

if top_findings_btn and user_active:
    findings = RecommendationEngine.get_top_findings(res, active_df)
    if findings:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        render_html(
            """
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">⚡ Autonomous Top Findings ("What Should I Look At?")</div>
                        <div class="ref-panel-subtitle">Key statistical highlights and dominant drivers discovered from active data</div>
                    </div>
                </div>
            </div>
            """
        )
        f_cols = st.columns(len(findings))
        for idx, f in enumerate(findings):
            with f_cols[idx]:
                st.markdown(
                    f"""
                    <div style="padding: 12px; background: rgba(30, 41, 59, 0.5); border: 1px solid #334155; border-radius: 8px; height: 100%;">
                        <span style="font-size: 0.65rem; background: #0284c7; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 700;">{f['badge']}</span>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 0.85rem; margin-top: 6px;">{f['title']}</div>
                        <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px; line-height: 1.4;">{f['description']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

if edit_mode and user_active:
    st.info("🛠️ **Dashboard Layout Customizer**: Select components to render on the command center.")
    current_layout = AnalyticsManager.get_dashboard_layout()
    opt_map = {
        "kpis": "Smart KPI Row",
        "target": "Goal / Target Attainment Tracker",
        "trend": "Time-Series Performance Trend & Forecasting",
        "donut": "Dimension Donut Breakdown",
        "bar": "Ranked Dimension Bar Chart",
        "story": "Autonomous Data Story / Business Narrative",
        "anomalies": "Statistical Anomaly Center",
        "quality": "Data Quality Summary"
    }
    sel_layout = st.multiselect(
        "Active Dashboard Components:",
        options=list(opt_map.keys()),
        default=current_layout,
        format_func=lambda x: opt_map.get(x, x)
    )
    if sel_layout != current_layout:
        AnalyticsManager.set_dashboard_layout(sel_layout)
        st.rerun()

layout_elements = AnalyticsManager.get_dashboard_layout() if user_active else ["kpis", "trend", "donut", "bar"]

# ------------------------------------------------------------------------------
# 1. SMART KPI ROW (WITH EXPLAINABILITY)
# ------------------------------------------------------------------------------
if "kpis" in layout_elements:
    if user_active:
        rev_val = float(kpis.get("total_revenue", 0.0))
        tx_count = int(kpis.get("total_transactions", len(active_df)))
        aov_val = float(kpis.get("average_transaction_value", 0.0))
        growth = kpis.get("growth_pct")

        m_label = "TOTAL PAYROLL / SALARY" if "HR" in domain_name else ("TOTAL AD SPEND" if "Marketing" in domain_name else "GROSS VOLUME / REVENUE")
        c_label = "HEADCOUNT" if "HR" in domain_name else ("CAMPAIGNS" if "Marketing" in domain_name else "TRANSACTION VOLUME")
        a_label = "AVERAGE COMPENSATION" if "HR" in domain_name else ("COST PER CAMPAIGN" if "Marketing" in domain_name else "AVERAGE SPEND / TICKET")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_kpi_card(m_label, f"${rev_val:,.2f}", f"Field: `{kpis.get('primary_metric_col', 'N/A')}`", f"{'+' if growth and growth >= 0 else ''}{growth:.1f}% Growth" if growth is not None else "↑ Active Data", True, icon="💎", color="purple", raw_value=f"${rev_val:,.2f}")
        with col2:
            render_kpi_card(c_label, f"{tx_count:,}", f"From {len(active_df):,} rows", "↑ Reconciled", True, icon="🛍️", color="blue", raw_value=f"{tx_count:,} items")
        with col3:
            render_kpi_card(a_label, f"${aov_val:,.2f}", "Metric / Record", "↑ Calculated Mean", True, icon="📈", color="emerald", raw_value=f"${aov_val:.2f}")
        with col4:
            top_c = kpis.get("top_category_name", "N/A")
            render_kpi_card("TOP DOMAIN SEGMENT", str(top_c)[:15], f"${kpis.get('top_category_val', 0.0):,.2f} Total", "↑ Leader", True, icon="🏆", color="gold", raw_value=str(top_c))

        with st.expander("ℹ️ How are these KPIs calculated? (KPI Explainability)", expanded=False):
            ex1 = KPIExplainer.explain_kpi(m_label, kpis.get("primary_metric_col"), f"SUM({kpis.get('primary_metric_col')})", len(active_df), active_filters)
            ex2 = KPIExplainer.explain_kpi(a_label, kpis.get("primary_metric_col"), f"SUM({kpis.get('primary_metric_col')}) / COUNT(*)", len(active_df), active_filters)
            st.markdown(f"- **{ex1['kpi_name']}**: {ex1['explanation']}")
            st.markdown(f"- **{ex2['kpi_name']}**: {ex2['explanation']}")
    else:
        loader = DashboardDataLoader()
        kpi_data = loader.get_executive_kpis()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_kpi_card("NET REALIZED REVENUE", f"${float(kpi_data.get('total_revenue', 15843553.24)):,.2f}", "Total Gross Settlement", "↑ 102.4% Target", True, icon="💎", color="purple", raw_value="$15,843,553.24")
        with col2:
            render_kpi_card("TOTAL ORDERS", f"{int(kpi_data.get('total_orders', 98666)):,}", "Reconciled Transactions", "↑ 98,666 Gold Orders", True, icon="🛍️", color="blue", raw_value="98,666")
        with col3:
            render_kpi_card("AVERAGE ORDER VALUE", f"${float(kpi_data.get('aov', 160.58)):.2f}", "Net basket average", "↑ Reconciled mean", True, icon="📈", color="emerald", raw_value="$160.58")
        with col4:
            render_kpi_card("DATA QUALITY SCORE", f"{float(kpi_data.get('data_quality_score', 99.9981)):.4f}%", "12/12 Automated Rules", "↑ 0 Quarantine Leakage", True, icon="🛡️", color="gold", raw_value="99.9981%")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. GOAL / TARGET TRACKING SECTION
# ------------------------------------------------------------------------------
if "target" in layout_elements and user_active:
    targets = AnalyticsManager.get_targets()
    curr_rev = float(kpis.get("total_revenue", 0.0))
    tgt_val = targets.get("revenue", 0.0)

    if tgt_val > 0:
        tgt_eval = TargetEngine.evaluate_target(curr_rev, tgt_val, "Revenue / Volume")
        pct = min(100.0, tgt_eval["attainment_pct"])
        status_color = "#10b981" if tgt_eval["status"] == "EXCEEDED" else ("#38bdf8" if tgt_eval["status"] == "ON TRACK" else "#f59e0b")

        render_html(
            f"""
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 0.95rem;">🎯 Business Target Attainment: <span style="color: {status_color};">{tgt_eval['status']}</span></div>
                    <div style="font-size: 0.85rem; color: #94a3b8;">Target: <b>${tgt_val:,.2f}</b> | Actual: <b>${curr_rev:,.2f}</b> ({pct:.1f}%)</div>
                </div>
                <div style="background: #1e293b; height: 10px; border-radius: 5px; margin-top: 8px; overflow: hidden;">
                    <div style="background: {status_color}; width: {pct}%; height: 100%;"></div>
                </div>
            </div>
            """
        )

# ------------------------------------------------------------------------------
# 3. TIME-SERIES PERFORMANCE TREND & FORECASTING
# ------------------------------------------------------------------------------
if "trend" in layout_elements:
    c_trend, c_donut = st.columns([1.6, 1.0])
    with c_trend:
        render_html(
            """
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Performance Trend & Statistical Forecasting</div>
                        <div class="ref-panel-subtitle">Historical progression over time with projected trajectory</div>
                    </div>
                </div>
            </div>
            """
        )
        if user_active:
            date_col = kpis.get("date_col")
            metric_col = kpis.get("primary_metric_col")
            if date_col and metric_col and date_col in active_df.columns and metric_col in active_df.columns:
                fore_res = ForecastEngine.generate_forecast(active_df, date_col, metric_col, horizon=3)
                if fore_res.get("available"):
                    st.plotly_chart(fore_res["figure"], use_container_width=True)
                    st.caption(f"🔮 **Forecast Summary**: {fore_res['summary']}")
                else:
                    fig_trend = ChartEngine.create_time_series_chart(active_df, date_col, metric_col, granularity="Monthly")
                    st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style="padding: 30px; text-align: center; color: #94a3b8; background: rgba(30,41,59,0.3); border-radius: 8px;">
                        📅 <b>Date Intelligence Unavailable</b><br>
                        No recognizable datetime column detected in the uploaded dataset.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            df_trend = loader.get_monthly_sales_trend()
            fig_trend = create_revenue_trend_chart(df_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

    with c_donut:
        render_html(
            """
            <div class="ref-panel">
                <div class="ref-panel-header">
                    <div>
                        <div class="ref-panel-title">Segment Share & Distribution</div>
                        <div class="ref-panel-subtitle">Proportional breakdown by key dimension</div>
                    </div>
                </div>
            </div>
            """
        )
        if user_active:
            cat_col = kpis.get("category_col")
            metric_col = kpis.get("primary_metric_col")
            fig_donut = None
            if cat_col and metric_col and cat_col in active_df.columns and metric_col in active_df.columns:
                try:
                    fig_donut = ChartEngine.create_dimension_donut_chart(active_df, cat_col, metric_col, top_n=6)
                except Exception as e:
                    logger.warning(f"Failed to create dimension donut chart: {e}")
                    fig_donut = None

            if fig_donut is not None:
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style="padding: 30px; text-align: center; color: #94a3b8; background: rgba(30,41,59,0.3); border-radius: 8px;">
                        📦 <b>No suitable categorical metric available for this visualization.</b><br>
                        <span style="font-size: 0.8rem;">Upload or select a dataset with categorical and numeric columns.</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            df_cat = loader.get_category_performance()
            fig_donut = create_category_donut_chart(df_cat)
            st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 4. AUTONOMOUS DATA STORY & BUSINESS NARRATIVE
# ------------------------------------------------------------------------------
if "story" in layout_elements and user_active:
    render_html(
        """
        <div class="ref-panel">
            <div class="ref-panel-header">
                <div>
                    <div class="ref-panel-title">📖 Autonomous Data Story & Executive Narrative</div>
                    <div class="ref-panel-subtitle">Dynamically computed storyline reflecting current dataset and active filter context</div>
                </div>
            </div>
        </div>
        """
    )
    story_chapters = DataStoryEngine.generate_story(res, active_df, active_filters)
    if story_chapters:
        for ch in story_chapters:
            st.markdown(
                f"""
                <div style="margin-bottom: 8px; padding: 10px 14px; background: rgba(15, 23, 42, 0.5); border-left: 3px solid #38bdf8; border-radius: 4px;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 0.85rem;">{ch['icon']} {ch['title']}</div>
                    <div style="color: #cbd5e1; font-size: 0.8rem; margin-top: 4px; line-height: 1.5;">{ch['narrative']}</div>
                    <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 2px; font-style: italic;">👉 <b>Impact</b>: {ch['takeaway']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
