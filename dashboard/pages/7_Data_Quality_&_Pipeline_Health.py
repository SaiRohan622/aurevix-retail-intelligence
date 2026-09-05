"""
AUREVIX — Page 7: Data Quality & Pipeline Health
Powered by AnalyticsManager: Supports Demo Mode & User Mode.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.analytics.data_cache import AnalyticsManager

st.set_page_config(page_title="Data Quality & Health — AUREVIX", page_icon="🛡️", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
prof = res.get("profile", {})
schema = res.get("schema", {})

render_html(
    """
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">🛡️</div>
            <div>
                <div class="header-title-text">Data Quality & Pipeline Health Console</div>
                <div class="header-title-sub">Automated Data Quality audits, schema integrity, and SLA health</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> SLA: GREEN</span>
        </div>
    </div>
    """
)

if user_active:
    q_score = float(prof.get("quality_score", 100.0))
    missing_pct = float(prof.get("missing_pct", 0.0))
    dup_rows = int(prof.get("duplicate_rows", 0))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("DATASET DQ SCORE", f"{q_score:.1f}%", f"{len(active_df):,} total records", "↑ Evaluated", True, icon="🛡️", color="emerald", raw_value="Quality Rating")
    with col2:
        render_kpi_card("MISSINGNESS RATE", f"{missing_pct:.2f}%", f"{prof.get('missing_cells', 0):,} null cells", "↑ Audited", True, icon="🥉", color="blue", raw_value="Null Checks")
    with col3:
        render_kpi_card("DUPLICATE ROWS", f"{dup_rows:,}", "Exact row duplicates", "↑ Audited", True, icon="🥇", color="purple", raw_value="Uniqueness")
    with col4:
        render_kpi_card("SCHEMA COLUMNS", f"{len(active_df.columns)}", "Detected column types", "↑ Verified", True, icon="🌪️", color="cyan", raw_value="Schema Match")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    render_html(
        """
        <div class="ref-panel">
            <div class="ref-panel-header">
                <div>
                    <div class="ref-panel-title">Column-Level Quality Profile & Status</div>
                    <div class="ref-panel-subtitle">Per-column null and uniqueness breakdown for uploaded dataset</div>
                </div>
            </div>
        </div>
        """
    )
    cols_meta = schema.get("columns", {})
    if cols_meta:
        rows = []
        for c, m in cols_meta.items():
            status = "GOOD" if m["null_pct"] == 0 else ("WARNING" if m["null_pct"] < 10 else "CRITICAL")
            rows.append({
                "Column Name": c,
                "Semantic Type": m["semantic_type"].upper(),
                "Data Type": m["dtype"],
                "Null %": f"{m['null_pct']:.2f}%",
                "Unique Values": f"{m['unique_count']:,}",
                "Quality Status": status
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    loader = DashboardDataLoader()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("PLATFORM DQ SCORE", "99.9981%", "1,550,893 valid / 29 quarantined", "↑ 12/12 Rules", True, icon="🛡️", color="emerald", raw_value="Quality Firewall")
    with col2:
        render_kpi_card("BRONZE QUALITY", "100% PASSED", "1,550,922 rows (0 byte loss)", "↑ Verified", True, icon="🥉", color="blue", raw_value="Zero Loss")
    with col3:
        render_kpi_card("GOLD RECONCILIATION", "$0.00 VARIANCE", "$15,843,553.24 verified", "↑ Exact Parity", True, icon="🥇", color="purple", raw_value="100% Reconciled")
    with col4:
        render_kpi_card("AIRFLOW DAG HEALTH", "OPERATIONAL", "All task dependencies met", "↑ Automated", True, icon="🌪️", color="cyan", raw_value="SLA Met")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    render_html(
        """
        <div class="ref-panel">
            <div class="ref-panel-header">
                <div>
                    <div class="ref-panel-title">Pipeline Execution Audit History</div>
                    <div class="ref-panel-subtitle">Historical records from data/monitoring/pipeline_run_history.jsonl</div>
                </div>
            </div>
        </div>
        """
    )
    runs = loader.get_pipeline_history()
    if runs:
        df_runs = pd.DataFrame(runs)
        st.dataframe(df_runs, use_container_width=True)
    else:
        st.success("All pipelines executing within normal SLA bounds (SLA Max Latency: 60 mins).")
