"""
AUREVIX — Page 6: Real-Time Stream Operations
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

st.set_page_config(page_title="Real-Time Operations — AUREVIX", page_icon="⚡", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()

render_html(
    """
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">⚡</div>
            <div>
                <div class="header-title-text">Real-Time Streaming Operations</div>
                <div class="header-title-sub">Apache Kafka + Spark Structured Streaming (10-min Watermark & Stateful Deduplication)</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> ACTIVE</span>
        </div>
    </div>
    """
)

if user_active:
    st.markdown(
        f"""
        <div style="padding: 24px; border-radius: 8px; background: rgba(22, 32, 53, 0.6); border: 1px solid #192338;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <div style="font-size: 1.5rem;">📂</div>
                <div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">USER DATASET ACTIVE — Historical Batch Ingestion Mode</div>
                    <div style="color: #94a3b8; font-size: 0.8rem;">Dataset: <b>{res.get('dataset_name', 'Uploaded File')}</b> ({len(active_df):,} rows)</div>
                </div>
            </div>
            <div style="color: #94a3b8; font-size: 0.8rem; line-height: 1.6; border-top: 1px solid #192338; padding-top: 12px;">
                ⚠️ <b>Real-Time Analytics Notice:</b> Real-time streaming operations require an active continuous event stream (e.g. Apache Kafka topic). The uploaded dataset is processed using the high-performance In-Memory Universal Analytics Engine.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    loader = DashboardDataLoader()
    metrics_data = loader.get_streaming_metrics()
    metrics = metrics_data.get("metrics", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_kpi_card("EVENTS RECEIVED", f"{metrics.get('total_events_received', 110):,}", "Kafka Ingestion", "↑ Live Stream", True, icon="📥", color="blue", raw_value="Raw Stream")
    with col2:
        render_kpi_card("VALID EVENTS", f"{metrics.get('valid_events_count', 100):,}", "Committed to Gold", "↑ Clean", True, icon="💎", color="emerald", raw_value="Validated Events")
    with col3:
        render_kpi_card("DUPLICATES FILTERED", f"{metrics.get('duplicates_filtered_count', 10):,}", "Deduplicated by event_id", "↑ Filtered", True, icon="🛡️", color="gold", raw_value="Watermark")
    with col4:
        render_kpi_card("QUARANTINED", f"{metrics.get('quarantined_events_count', 0):,}", "DQ Firewall isolated", "↑ 0 Errors", True, icon="⛔", color="purple", raw_value="Zero Errors")
    with col5:
        render_kpi_card("STREAM REVENUE", f"${float(metrics.get('streaming_gross_revenue', 18456.78)):,.2f}", "Windowed aggregates", "↑ Active", True, icon="💰", color="cyan", raw_value="Micro-batch")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    render_html(
        """
        <div class="ref-panel">
            <div class="ref-panel-header">
                <div>
                    <div class="ref-panel-title">Real-Time Event Stream Feed</div>
                    <div class="ref-panel-subtitle">Live micro-batch event payloads processed through Spark engine</div>
                </div>
            </div>
        </div>
        """
    )
    events = metrics_data.get("recent_events", [])
    if events:
        df_ev = pd.DataFrame(events)
        st.dataframe(df_ev, use_container_width=True)
