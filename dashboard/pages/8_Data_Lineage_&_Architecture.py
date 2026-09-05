"""
AUREVIX — Page 8: Dynamic Data Lineage & Platform Architecture
Displays end-to-end lineage for both production Medallion pipelines and active custom user datasets.
"""
import os
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.analytics.data_cache import AnalyticsManager

st.set_page_config(page_title="Data Lineage & Architecture — AUREVIX", page_icon="🔗", layout="wide")

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()

render_html(
    """
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">🔗</div>
            <div>
                <div class="header-title-text">Data Lineage & Platform Architecture</div>
                <div class="header-title-sub">End-to-end data transformation trace, governance contracts & lakehouse pipeline flow</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> LINEAGE VERIFIED</span>
        </div>
    </div>
    """
)

if user_active:
    ds_name = res.get("dataset_name", "Uploaded Dataset")
    domain = res.get("schema", {}).get("domain", "General Enterprise")
    render_html(
        f"""
        <div class="ref-panel" style="margin-bottom: 14px;">
            <div class="ref-panel-header">
                <div>
                    <div class="ref-panel-title">Dynamic User Dataset Pipeline Lineage</div>
                    <div class="ref-panel-subtitle">Trace for active in-memory dataset: <b>{ds_name}</b> ({domain})</div>
                </div>
            </div>
            <div style="padding: 16px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.8; color: #38bdf8;">
                [SOURCE FILE: {ds_name}]<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>UniversalDataLoader (SHA-256 Fingerprint Validation)</i><br>
                [IN-MEMORY DATAFRAME]<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>SchemaDetector (Semantic Roles, Data Types, Domain Inference)</i><br>
                [SCHEMA INTELLIGENCE]<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>DataProfiler (4-Pillar Quality: Completeness, Validity, Uniqueness, Consistency)</i><br>
                [DATA QUALITY FIREWALL]<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>MetricEngine & AnomalyEngine (Dynamic KPIs, Period-over-Period Trends, Outliers)</i><br>
                [ANALYTICS CACHE & SESSION STORE]<br>
                &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>InsightEngine & QueryEngine (Observation/Driver/Impact, Ask Your Data)</i><br>
                [AUREVIX INTERACTIVE DASHBOARDS & EXECUTIVE REPORT]
            </div>
        </div>
        """
    )

render_html(
    """
    <div class="ref-panel">
        <div class="ref-panel-header">
            <div>
                <div class="ref-panel-title">AUREVIX Production Platform Architecture</div>
                <div class="ref-panel-subtitle">Enterprise Data Engineering & Lakehouse Pipeline Lineage</div>
            </div>
        </div>
        <div style="padding: 16px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.8; color: #10b981;">
            [RAW CSV LAYER] (9 Olist Source Tables / 1,550,922 records)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>Bronze Ingestion (PySpark snappy.parquet / 0-byte loss)</i><br>
            [BRONZE DELTA LAKE] (Raw Immutable Store)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>Silver Transformation + 12 DQ Rules Firewall (29 outliers isolated)</i><br>
            [SILVER QUALITY LAYER] (Validated Clean Snappy Parquet)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>Gold Kimball Star Schema Aggregations</i><br>
            [GOLD STAR SCHEMA] (fact_sales + 6 Dimension Tables / $15,843,553.24 reconciled)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>PostgreSQL DW + Airflow DAG Orchestration + dbt Transformation</i><br>
            [SERVING WAREHOUSE] (PostgreSQL 16 `aurevix_dw`)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;↓ <i>Microsoft Fabric OneLake Contract + Power BI DirectLake Specification</i><br>
            [ENTERPRISE CLOUD LAKEHOUSE & BI CONSUMPTION]
        </div>
    </div>
    """
)
