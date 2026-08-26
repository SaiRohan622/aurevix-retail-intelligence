"""
AUREVIX — Page 8: Data Lineage & Architecture
"""
import os
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar

st.set_page_config(page_title="Data Lineage — AUREVIX", page_icon="🏗️", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()

st.title("Data Lineage & System Architecture")
st.caption("End-to-End Enterprise Data Flow & Dual Batch/Streaming Topology")

st.markdown(
    """
    ### 1. Dual-Path Architecture Lineage
    ```mermaid
    flowchart TD
        subgraph Ingestion ["1. Ingestion Layer"]
            R[Raw Olist CSVs]
            S[Order Simulator]
        end

        subgraph BatchProcessing ["2. Batch Engine (PySpark)"]
            B[Bronze Parquet]
            SV[Silver Standardized]
            G[Gold Star Schema]
        end

        subgraph StreamProcessing ["3. Real-Time Engine (Kafka + Spark)"]
            K[Kafka Topic: aurevix.retail.orders]
            SS[Spark Structured Streaming]
            SG[Streaming Gold Windows]
        end

        subgraph Warehouse ["4. Warehouse & Serving Layer"]
            PG[(PostgreSQL 16 DW)]
            DBT[dbt-postgres Analytics Marts]
        end

        subgraph Intelligence ["5. BI & Executive Applications"]
            ST[Streamlit Operations Dashboard]
            PB[Power BI / Microsoft Fabric]
        end

        R --> B --> SV --> G --> PG
        S --> K --> SS --> SG --> PG
        PG --> DBT --> ST
        PG --> DBT --> PB
    ```
    """,
    unsafe_allow_html=True
)
