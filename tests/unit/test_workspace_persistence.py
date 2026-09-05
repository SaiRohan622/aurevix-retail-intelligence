"""
AUREVIX — Workspace Persistence, Data Isolation & Complete Upload Flow Tests
Verifies that uploaded datasets (CSV, XLSX, JSON, Parquet) activate cleanly,
persist across reruns and tab switches, reject empty/invalid files, never silently
fall back to Olist, and power every analytical capability.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
import io
import json

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.profiler import DataProfiler


@pytest.fixture(autouse=True)
def reset_state():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def _make_retail_df(n=50):
    import numpy as _np
    return pd.DataFrame({
        "transaction_id": [f"T{i:04d}" for i in range(1, n + 1)],
        "transaction_date": pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
        "customer_id": [f"C{(i % 10) + 1:03d}" for i in range(n)],
        "product": [f"Product_{chr(65 + i % 5)}" for i in range(n)],
        "category": [["Electronics", "Apparel", "Food", "Home", "Sports"][i % 5] for i in range(n)],
        "region": [["North", "South", "East", "West"][i % 4] for i in range(n)],
        "quantity": _np.random.randint(1, 10, n),
        "unit_price": _np.random.uniform(10, 500, n).round(2),
        "revenue": _np.random.uniform(50, 2000, n).round(2),
    })


def _make_hr_df(n=30):
    import numpy as _np
    return pd.DataFrame({
        "employee_id": [f"E{i:04d}" for i in range(1, n + 1)],
        "name": [f"Employee {i}" for i in range(1, n + 1)],
        "department": [["Engineering", "HR", "Sales", "Finance"][i % 4] for i in range(n)],
        "salary": _np.random.uniform(40000, 150000, n).round(2),
        "hire_date": pd.date_range("2020-01-01", periods=n, freq="30D").astype(str),
        "location": [["New York", "San Francisco", "Chicago"][i % 3] for i in range(n)],
    })


# ---------------------------------------------------------------------
# 1. Upload Activation & Persistence Tests
# ---------------------------------------------------------------------
def test_file_upload_activates_workspace():
    csv_bytes = b"customer_id,name,department,revenue,units\n1,Alice,Electronics,1200,4\n2,Bob,Clothing,850,7\n3,Charlie,Electronics,2100,8"
    buf = io.BytesIO(csv_bytes)
    df, fhash = UniversalDataLoader.load_and_fingerprint(buf, "test_custom.csv")
    res = AnalyticsManager.activate_user_dataset(df, "test_custom.csv", fhash)

    assert AnalyticsManager.has_active_dataset() is True
    assert AnalyticsManager.is_user_mode() is True
    assert AnalyticsManager.is_demo_mode() is False
    assert res["dataset_name"] == "test_custom.csv"
    assert res["dataset_id"] == fhash


def test_uploaded_dataframe_is_not_empty():
    df = _make_retail_df(25)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "ret123")
    active = AnalyticsManager.get_active_df()
    assert isinstance(active, pd.DataFrame)
    assert not active.empty
    assert len(active) == 25
    assert "revenue" in active.columns


def test_uploaded_dataframe_persists_after_rerun():
    df = _make_retail_df(50)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "ret123")

    # Simulate multiple Streamlit reruns
    for _ in range(5):
        AnalyticsManager.initialize()
        assert AnalyticsManager.has_active_dataset() is True
        assert len(AnalyticsManager.get_active_df()) == 50


def test_uploaded_dataframe_persists_across_tabs():
    df = _make_hr_df(30)
    AnalyticsManager.activate_user_dataset(df, "employees.xlsx", "emp123")

    # Simulate accessing from multiple workspace tabs
    tab_ingest_df = AnalyticsManager.get_active_df()
    tab_clean_df = AnalyticsManager.get_active_df()
    tab_explorer_df = AnalyticsManager.get_active_df()
    tab_compare_df = AnalyticsManager.get_active_df()
    tab_export_df = AnalyticsManager.get_active_df()

    for tab_df in (tab_ingest_df, tab_clean_df, tab_explorer_df, tab_compare_df, tab_export_df):
        assert len(tab_df) == 30
        assert "salary" in tab_df.columns


def test_uploaded_dataset_does_not_fallback_to_olist():
    df = _make_retail_df(40)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "ret123")

    for _ in range(10):
        active = AnalyticsManager.get_active_df()
        assert "revenue" in active.columns
        assert "freight_value" not in active.columns
        assert "order_purchase_timestamp" not in active.columns


def test_second_upload_replaces_first_dataset():
    df1 = _make_retail_df(50)
    AnalyticsManager.activate_user_dataset(df1, "retail.csv", "hash_retail")
    assert AnalyticsManager.get_analysis_results()["kpis"]["primary_metric_col"] == "revenue"

    df2 = _make_hr_df(30)
    AnalyticsManager.activate_user_dataset(df2, "hr.xlsx", "hash_hr")
    res = AnalyticsManager.get_analysis_results()

    assert res["dataset_name"] == "hr.xlsx"
    assert res["kpis"]["primary_metric_col"] == "salary"
    assert "revenue" not in res["schema"]["columns"]
    active = AnalyticsManager.get_active_df()
    assert len(active) == 30
    assert "salary" in active.columns
    assert "revenue" not in active.columns


# ---------------------------------------------------------------------
# 2. File Format Loader Tests
# ---------------------------------------------------------------------
def test_csv_upload():
    csv_data = b"id,val,dept\n1,100,A\n2,200,B\n3,300,C"
    buf = io.BytesIO(csv_data)
    df, fhash = UniversalDataLoader.load_and_fingerprint(buf, "test.csv")
    assert len(df) == 3
    assert list(df.columns) == ["id", "val", "dept"]


def test_xlsx_upload():
    df_orig = pd.DataFrame({"col1": [1, 2, 3], "col2": ["x", "y", "z"]})
    buf = io.BytesIO()
    df_orig.to_excel(buf, index=False)
    buf.seek(0)
    df_loaded, _ = UniversalDataLoader.load_and_fingerprint(buf, "test.xlsx")
    assert len(df_loaded) == 3
    assert "col1" in df_loaded.columns


def test_json_upload():
    records = [{"item": f"Item{i}", "price": i * 15.5} for i in range(5)]
    buf = io.BytesIO(json.dumps(records).encode("utf-8"))
    df, _ = UniversalDataLoader.load_and_fingerprint(buf, "test.json")
    assert len(df) == 5
    assert "price" in df.columns


def test_parquet_upload():
    df_orig = pd.DataFrame({"a": [10, 20, 30], "b": [1.1, 2.2, 3.3]})
    buf = io.BytesIO()
    df_orig.to_parquet(buf, index=False)
    buf.seek(0)
    df, _ = UniversalDataLoader.load_and_fingerprint(buf, "test.parquet")
    assert len(df) == 3
    assert "a" in df.columns


def test_empty_file_rejected():
    buf = io.BytesIO(b"")
    with pytest.raises(ValueError, match="empty"):
        UniversalDataLoader.load_and_fingerprint(buf, "empty.csv")


def test_invalid_file_handled():
    buf = io.BytesIO(b"random binary gibberish \x00\x01\x02")
    with pytest.raises(ValueError):
        UniversalDataLoader.load_and_fingerprint(buf, "bad.json")


# ---------------------------------------------------------------------
# 3. Downstream Feature Isolation Tests
# ---------------------------------------------------------------------
def test_profiling_uses_uploaded_dataset():
    df = _make_retail_df(50)
    res = AnalyticsManager.activate_user_dataset(df, "retail.csv", "prof_test")
    prof = res["profile"]
    assert prof["row_count"] == 50
    assert prof["col_count"] == len(df.columns)
    assert prof["quality_score"] > 0.0


def test_kpis_use_uploaded_dataset():
    df = _make_retail_df(50)
    res = AnalyticsManager.activate_user_dataset(df, "retail.csv", "kpi_test")
    kpis = res["kpis"]
    assert kpis["primary_metric_col"] == "revenue"
    assert kpis["total_revenue"] > 0
    assert abs(kpis["total_revenue"] - 15843553.24) > 1000


def test_data_explorer_uses_uploaded_dataset():
    df = _make_retail_df(50)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "exp_test")
    active = AnalyticsManager.get_active_df()
    assert set(active.columns) == set(df.columns)
    assert len(active) == 50


def test_ask_data_uses_uploaded_dataset():
    df = _make_retail_df(50)
    res = AnalyticsManager.activate_user_dataset(df, "retail.csv", "ask_test")
    active = AnalyticsManager.get_active_df()
    ans = AskYourDataEngine.answer_question(
        active, "Which category generated the highest revenue?",
        res["schema"], res["kpis"]
    )
    assert "answer" in ans
    assert any(cat in ans["answer"] for cat in ["Electronics", "Apparel", "Food", "Home", "Sports"])
    assert "beleza_saude" not in ans["answer"]


def test_export_uses_uploaded_dataset():
    df = _make_retail_df(50)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "export_test")
    export_df = AnalyticsManager.get_active_df()
    csv_str = export_df.to_csv(index=False)
    assert "revenue" in csv_str
    assert "freight_value" not in csv_str


def test_clear_dataset_returns_empty_workspace():
    df = _make_retail_df(50)
    AnalyticsManager.activate_user_dataset(df, "retail.csv", "clear_test")
    assert AnalyticsManager.has_active_dataset() is True

    AnalyticsManager.clear_active_dataset()
    assert AnalyticsManager.has_active_dataset() is False
    assert AnalyticsManager.is_user_mode() is False
    assert AnalyticsManager.is_demo_mode() is True
    assert AnalyticsManager.get_active_df().empty


def test_explicit_demo_button_loads_demo_only_when_clicked():
    # In empty state, get_active_df is empty
    assert AnalyticsManager.get_active_df().empty
    # Analysis results for demo are returned only as metadata
    res = AnalyticsManager.get_analysis_results()
    assert res["dataset_id"] == "olist_production_gold"
    # But active DataFrame remains empty until user explicitly loads demo or dataset
    assert AnalyticsManager.get_active_df().empty
