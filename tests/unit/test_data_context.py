"""
AUREVIX — Unit & Integration Tests for Global Data Context & Analyst Mode
Validates session persistence, mode switching, dynamic KPI calculations,
and multi-page dataset consistency.
"""

import pandas as pd
import numpy as np
import pytest
from dashboard.utils.data_context import (
    initialize_data_context,
    set_user_dataset,
    get_active_dataset,
    get_active_mode,
    is_analyst_mode,
    is_demo_mode,
    clear_user_dataset,
    get_dataset_metadata,
    get_active_kpis
)


@pytest.fixture(autouse=True)
def reset_context():
    """Reset context before and after each test."""
    clear_user_dataset()
    yield
    clear_user_dataset()


@pytest.fixture
def sample_business_df():
    dates = pd.date_range(start="2023-01-01", periods=24, freq="MS")
    return pd.DataFrame({
        "Date": dates,
        "Category": ["Electronics", "Fashion", "Home", "Beauty"] * 6,
        "Region": ["North", "South", "East", "West"] * 6,
        "Customer_ID": [f"CUST_{i%5}" for i in range(24)],
        "Revenue": [10000 + i * 500 for i in range(24)],
        "Profit": [2000 + i * 100 for i in range(24)],
        "Quantity": [50 + i * 2 for i in range(24)]
    })


def test_demo_mode_fallback():
    initialize_data_context()
    assert is_demo_mode() is True
    assert is_analyst_mode() is False
    assert get_active_mode() == "demo"
    # FIXED: demo mode now correctly returns empty DataFrame (no silent Olist auto-load).
    # Uploaded datasets are the only active data; demo data is explicit-only.
    df = get_active_dataset()
    assert isinstance(df, pd.DataFrame)  # always returns a DataFrame, never None


def test_analyst_mode_activation(sample_business_df):
    set_user_dataset(sample_business_df, "test_file.csv")
    assert is_analyst_mode() is True
    assert is_demo_mode() is False
    assert get_active_mode() == "analyst"


def test_uploaded_dataset_persistence(sample_business_df):
    set_user_dataset(sample_business_df, "persistent_data.csv")
    df1 = get_active_dataset()
    assert len(df1) == 24
    assert "Revenue" in df1.columns

    df2 = get_active_dataset()
    assert len(df2) == 24
    assert df1.equals(df2)


def test_active_dataset_selection(sample_business_df):
    # FIXED: demo mode returns empty DataFrame (no silent Olist load).
    demo_df = get_active_dataset()
    assert isinstance(demo_df, pd.DataFrame)  # returns a DataFrame, not None

    set_user_dataset(sample_business_df, "analyst.csv")
    analyst_df = get_active_dataset()
    assert len(analyst_df) == 24


def test_dataset_context_persistence(sample_business_df):
    res = set_user_dataset(sample_business_df, "custom.csv")
    assert res["profile"]["row_count"] == 24
    meta = get_dataset_metadata()
    assert meta["row_count"] == 24
    assert meta["quality_score"] == 100.0


def test_dynamic_kpis(sample_business_df):
    set_user_dataset(sample_business_df, "custom.csv")
    kpis = get_active_kpis()
    assert kpis["is_analyst_mode"] is True
    assert kpis["total_revenue"] == float(sample_business_df["Revenue"].sum())
    assert kpis["total_profit"] == float(sample_business_df["Profit"].sum())
    assert kpis["total_orders"] == 24
    assert kpis["active_customers"] == 5


def test_dynamic_date_detection(sample_business_df):
    set_user_dataset(sample_business_df, "custom.csv")
    kpis = get_active_kpis()
    assert kpis["date_col"] == "Date"


def test_dynamic_category_analysis(sample_business_df):
    set_user_dataset(sample_business_df, "custom.csv")
    kpis = get_active_kpis()
    assert kpis["category_col"] == "Category"
    cat_grp = sample_business_df.groupby("Category")["Revenue"].sum()
    assert len(cat_grp) == 4


def test_dynamic_region_analysis(sample_business_df):
    set_user_dataset(sample_business_df, "custom.csv")
    reg_grp = sample_business_df.groupby("Region")["Revenue"].sum()
    assert len(reg_grp) == 4


def test_customer_analysis_without_customer_id(sample_business_df):
    df_no_cust = sample_business_df.drop(columns=["Customer_ID"])
    set_user_dataset(df_no_cust, "no_cust.csv")
    kpis = get_active_kpis()
    assert kpis["customer_col"] is None


def test_real_time_unavailable_state(sample_business_df):
    set_user_dataset(sample_business_df, "custom.csv")
    assert is_analyst_mode() is True


def test_quality_metrics_dynamic_calculation():
    df_dirty = pd.DataFrame({
        "id": [1, 2, 2, 4],
        "val": [10.0, np.nan, np.nan, 40.0]
    })
    set_user_dataset(df_dirty, "dirty.csv")
    meta = get_dataset_metadata()
    assert meta["duplicate_rows"] == 1
    assert meta["missing_cells"] == 2
    assert meta["quality_score"] < 100.0


def test_mode_switching(sample_business_df):
    assert is_demo_mode() is True

    set_user_dataset(sample_business_df, "switch.csv")
    assert is_analyst_mode() is True
    assert len(get_active_dataset()) == 24

    clear_user_dataset()
    assert is_demo_mode() is True
    # FIXED: after clearing, demo mode returns empty DataFrame (no silent Olist load).
    cleared_df = get_active_dataset()
    assert isinstance(cleared_df, pd.DataFrame)


def test_clear_dataset(sample_business_df):
    set_user_dataset(sample_business_df, "test.csv")
    assert is_analyst_mode() is True
    clear_user_dataset()
    assert is_demo_mode() is True
    assert get_active_mode() == "demo"
