"""
AUREVIX — Unit Tests for Universal WorkspaceEngine
Tests CSV, Excel, Parquet loading, schema profiling, date detection,
KPI classification, time-series aggregation, MoM/YoY growth, and insight generation.
"""

import io
import pandas as pd
import numpy as np
import pytest
from dashboard.components.workspace_engine import WorkspaceEngine


@pytest.fixture
def synthetic_business_df():
    dates = pd.date_range(start="2023-01-01", periods=24, freq="MS")
    return pd.DataFrame({
        "order_date": dates,
        "category": ["Electronics", "Fashion", "Home", "Beauty"] * 6,
        "region": ["North", "South", "East", "West"] * 6,
        "revenue": [10000 + i * 500 for i in range(24)],
        "profit": [2000 + i * 100 for i in range(24)],
        "quantity": [50 + i * 2 for i in range(24)],
        "customer_id": [f"CUST_{i%5}" for i in range(24)]
    })


def test_workspace_profile_dataset(synthetic_business_df):
    profile = WorkspaceEngine.profile_dataset(synthetic_business_df)
    assert profile["row_count"] == 24
    assert profile["col_count"] == 7
    assert profile["missing_cells"] == 0
    assert profile["duplicate_rows"] == 0
    assert profile["quality_score"] == 100.0
    assert "revenue" in profile["columns"]
    assert profile["columns"]["revenue"]["semantic_type"] == "numeric"


def test_workspace_date_detection(synthetic_business_df):
    date_cols = WorkspaceEngine.detect_date_columns(synthetic_business_df)
    assert "order_date" in date_cols


def test_workspace_kpi_detection(synthetic_business_df):
    kpis = WorkspaceEngine.detect_kpi_mappings(synthetic_business_df)
    assert kpis["revenue"] == "revenue"
    assert kpis["profit"] == "profit"
    assert kpis["quantity"] == "quantity"
    assert kpis["customer_id"] == "customer_id"


def test_workspace_time_series_aggregation(synthetic_business_df):
    df_ts = WorkspaceEngine.aggregate_time_series(
        synthetic_business_df,
        date_col="order_date",
        metric_col="revenue",
        granularity="Monthly",
        agg_func="SUM"
    )
    assert not df_ts.empty
    assert len(df_ts) == 24
    assert "pop_growth_pct" in df_ts.columns
    assert "yoy_growth_pct" in df_ts.columns
    assert "rolling_3_avg" in df_ts.columns
    assert df_ts["value"].sum() > 0


def test_workspace_insights_generation(synthetic_business_df):
    insights = WorkspaceEngine.generate_smart_insights(
        synthetic_business_df,
        date_col="order_date",
        metric_col="revenue",
        dim_col="category"
    )
    assert len(insights) >= 3
    titles = [ins["title"] for ins in insights]
    assert any("Aggregate Revenue" in t for t in titles)
    assert any("Top Performing Category" in t for t in titles)


def test_workspace_file_loaders(synthetic_business_df, tmp_path):
    # CSV test
    csv_bytes = io.BytesIO()
    synthetic_business_df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)
    df_csv = WorkspaceEngine.load_dataset(csv_bytes, "test_data.csv")
    assert len(df_csv) == 24

    # Excel test
    xlsx_bytes = io.BytesIO()
    synthetic_business_df.to_excel(xlsx_bytes, index=False)
    xlsx_bytes.seek(0)
    df_xlsx = WorkspaceEngine.load_dataset(xlsx_bytes, "test_data.xlsx")
    assert len(df_xlsx) == 24

    # Parquet test
    pq_bytes = io.BytesIO()
    synthetic_business_df.to_parquet(pq_bytes, index=False)
    pq_bytes.seek(0)
    df_pq = WorkspaceEngine.load_dataset(pq_bytes, "test_data.parquet")
    assert len(df_pq) == 24
