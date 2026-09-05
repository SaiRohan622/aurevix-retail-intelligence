"""
AUREVIX — Centralized Global Data Session & Context Manager
Bridge to dashboard.analytics.data_cache.AnalyticsManager.
"""

from typing import Optional, Dict, List, Any
import streamlit as st
import pandas as pd
from dashboard.analytics.data_cache import AnalyticsManager


def initialize_data_context():
    AnalyticsManager.initialize()


def set_user_dataset(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    import hashlib
    file_hash = hashlib.sha256(filename.encode('utf-8')).hexdigest()[:16]
    return AnalyticsManager.activate_user_dataset(df, filename, file_hash)


def clear_user_dataset():
    AnalyticsManager.revert_to_demo()


def get_active_mode() -> str:
    return "analyst" if AnalyticsManager.is_user_mode() else "demo"


def is_analyst_mode() -> bool:
    return AnalyticsManager.is_user_mode()


def is_demo_mode() -> bool:
    return AnalyticsManager.is_demo_mode()


def get_active_dataset() -> pd.DataFrame:
    return AnalyticsManager.get_active_df()


def get_dataset_metadata() -> Dict[str, Any]:
    res = AnalyticsManager.get_analysis_results()
    prof = res.get("profile", {})
    return {
        "row_count": prof.get("row_count", 0),
        "quality_score": prof.get("quality_score", 100.0),
        "dataset_name": res.get("dataset_name", "Dataset"),
        "missing_cells": prof.get("missing_cells", 0),
        "duplicate_rows": prof.get("duplicate_rows", 0),
        "missing_pct": prof.get("missing_pct", 0.0),
        "memory_mb": prof.get("memory_mb", 0.1),
        "columns": res.get("schema", {}).get("columns", {})
    }


def get_active_kpis() -> Dict[str, Any]:
    res = AnalyticsManager.get_analysis_results()
    kpis = res.get("kpis", {})
    return {
        "total_revenue": kpis.get("total_revenue", 0.0),
        "total_profit": kpis.get("total_profit"),
        "total_orders": kpis.get("total_transactions", 0),
        "units_sold": kpis.get("total_quantity", 0),
        "active_customers": kpis.get("unique_customers"),
        "average_order_value": kpis.get("average_transaction_value", 0.0),
        "average_freight": kpis.get("average_cost", 0.0),
        "is_analyst_mode": AnalyticsManager.is_user_mode(),
        "primary_metric_col": kpis.get("primary_metric_col"),
        "profit_col": kpis.get("profit_col"),
        "customer_col": kpis.get("customer_col"),
        "category_col": kpis.get("category_col"),
        "date_col": kpis.get("date_col")
    }
