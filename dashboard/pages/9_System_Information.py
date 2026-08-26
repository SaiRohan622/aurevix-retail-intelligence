"""
AUREVIX — Page 9: System Information & Engineering Stack
"""
import os
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar

st.set_page_config(page_title="System Information — AUREVIX", page_icon="⚙️", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()

st.title("System Information")
st.caption("AUREVIX Platform Runtime Environment & Component Matrix")

st.markdown(
    """
    ### Platform Runtime Matrix
    - **Language:** Python 3.12.10
    - **Batch Processing:** Apache Spark 4.2.0 (PySpark / PySpark SQL)
    - **Real-Time Streaming:** Apache Kafka (2.13-3.7.0) + Spark Structured Streaming
    - **Orchestration:** Apache Airflow
    - **Warehouse Transformation:** dbt-postgres 1.11.0 / dbt-core 1.12.3
    - **Database Warehouse:** PostgreSQL 16 (aurevix_dw)
    - **Storage Format:** Apache Parquet (Snappy Compressed)
    - **Quality Assurance:** 33 / 33 PyTest Test Suite (100% Passed)
    """,
    unsafe_allow_html=True
)
