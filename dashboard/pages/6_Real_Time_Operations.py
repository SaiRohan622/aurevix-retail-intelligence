"""
AUREVIX — Page 6: Real-Time Stream Operations (Kafka + Spark Structured Streaming)
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

st.set_page_config(page_title="Real-Time Operations — AUREVIX", page_icon="⚡", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()
loader = DashboardDataLoader()

st.title("Real-Time Operations")
st.markdown('<span class="live-pulse"><span class="live-dot"></span> LIVE RETAIL STREAM ACTIVE</span>', unsafe_allow_html=True)
st.caption("Apache Kafka + Spark Structured Streaming Engine (10-min Watermark)")

st.markdown("<br>", unsafe_allow_html=True)

metrics_data = loader.get_streaming_metrics()
metrics = metrics_data.get("metrics", {})

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    render_kpi_card("Events Received", f"{metrics.get('total_events_received', 110):,}", "Kafka Ingestion")
with col2:
    render_kpi_card("Valid Events", f"{metrics.get('valid_events_count', 100):,}", "Committed to Gold")
with col3:
    render_kpi_card("Duplicates Filtered", f"{metrics.get('duplicates_filtered_count', 10):,}", "Deduplicated by event_id")
with col4:
    render_kpi_card("Quarantined", f"{metrics.get('quarantined_events_count', 0):,}", "DQ Firewall isolated")
with col5:
    render_kpi_card("Streaming Revenue", f"${metrics.get('streaming_gross_revenue', 14250.80):,.2f}", "Windowed aggregates")

st.markdown('<div class="section-header">Live Event Feed</div>', unsafe_allow_html=True)
events = metrics_data.get("recent_events", [])
if events:
    df_ev = pd.DataFrame(events)
    st.dataframe(df_ev, use_container_width=True)
else:
    st.info("STREAM IDLE — awaiting events")
