"""
AUREVIX — Universal Data Loader & Data Workspace Stability Test Suite
Verifies all 15 criteria: CSV/XLSX/Parquet/JSON parsing, load_file API, fingerprinting, error safety, and Olist isolation.
"""
import io
import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.universal_analytics import UniversalAnalytics


# Mock Streamlit UploadedFile object
class MockUploadedFile(io.BytesIO):
    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.name = name


def test_load_file_csv():
    csv_bytes = b"product,price,quantity\nLaptop,1200.0,5\nPhone,800.0,10\n"
    mock_file = MockUploadedFile(csv_bytes, "inventory.csv")
    df, fhash = UniversalDataLoader.load_file(mock_file)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["product", "price", "quantity"]
    assert len(fhash) == 16


def test_load_file_xlsx():
    df_orig = pd.DataFrame({
        "emp_id": [1, 2, 3],
        "department": ["Eng", "Sales", "HR"],
        "salary": [100000, 70000, 65000]
    })
    buf = io.BytesIO()
    df_orig.to_excel(buf, index=False)
    buf.seek(0)
    mock_file = MockUploadedFile(buf.read(), "employees.xlsx")

    df, fhash = UniversalDataLoader.load_file(mock_file)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert list(df.columns) == ["emp_id", "department", "salary"]
    assert len(fhash) == 16


def test_load_file_parquet():
    df_orig = pd.DataFrame({
        "order_id": [101, 102],
        "total_amount": [150.50, 89.20]
    })
    buf = io.BytesIO()
    df_orig.to_parquet(buf, index=False)
    buf.seek(0)
    mock_file = MockUploadedFile(buf.read(), "orders.parquet")

    df, fhash = UniversalDataLoader.load_file(mock_file)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["order_id", "total_amount"]
    assert len(fhash) == 16


def test_load_file_json():
    json_bytes = b'[{"campaign": "Promo_A", "spend": 1000}, {"campaign": "Promo_B", "spend": 2000}]'
    mock_file = MockUploadedFile(json_bytes, "campaigns.json")
    df, fhash = UniversalDataLoader.load_file(mock_file)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["campaign", "spend"]
    assert len(fhash) == 16


def test_load_file_returns_dataframe_and_hash():
    csv_bytes = b"col1,col2\n10,20\n30,40\n"
    mock_file = MockUploadedFile(csv_bytes, "test.csv")
    df, fhash = UniversalDataLoader.load_file(mock_file)

    assert isinstance(df, pd.DataFrame)
    assert isinstance(fhash, str)
    assert len(fhash) > 0


def test_load_file_empty_dataset():
    empty_file = MockUploadedFile(b"", "empty.csv")
    with pytest.raises(ValueError) as exc:
        UniversalDataLoader.load_file(empty_file)
    assert "empty" in str(exc.value).lower()


def test_load_file_invalid_format():
    txt_file = MockUploadedFile(b"some,data,here\n1,2,3\n", "dataset.unsupported_ext")
    # Will attempt parse via CSV or raise ValueError
    df, fhash = UniversalDataLoader.load_file(txt_file)
    assert isinstance(df, pd.DataFrame)


def test_load_file_malformed_file():
    corrupt_excel = MockUploadedFile(b"this is definitely not a real excel binary", "bad.xlsx")
    with pytest.raises(ValueError) as exc:
        UniversalDataLoader.load_file(corrupt_excel)
    assert "unable to parse" in str(exc.value).lower()


def test_uploaded_dataset_becomes_active():
    df = pd.DataFrame({"item": ["Widget A", "Widget B"], "cost": [10.0, 20.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "widgets.csv", "hash_widgets_99")

    assert AnalyticsManager.is_user_mode() is True
    assert AnalyticsManager.has_active_dataset() is True
    active_df = AnalyticsManager.get_active_df()
    assert len(active_df) == 2
    assert "item" in active_df.columns


def test_uploaded_dataset_persists_across_tabs():
    df = pd.DataFrame({"cust": ["C1", "C2"], "score": [95, 88]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "scores.csv", "hash_scores_1")

    # Simulate tab navigation
    AnalyticsManager.set_active_section("🔎 Data Explorer")
    assert AnalyticsManager.get_active_df().equals(df)

    AnalyticsManager.set_active_section("🧹 Clean & Transform")
    assert AnalyticsManager.get_active_df().equals(df)

    AnalyticsManager.set_active_section("📄 Export Center")
    assert AnalyticsManager.get_active_df().equals(df)


def test_user_dataset_never_falls_back_to_olist():
    df = pd.DataFrame({"city": ["London", "Paris"], "sales": [5000, 6000]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "cities.csv", "hash_cities_1")

    active_df = AnalyticsManager.get_active_df()
    assert "order_purchase_timestamp" not in active_df.columns
    assert "product_category_name" not in active_df.columns
    assert "customer_state" not in active_df.columns
    assert len(active_df) == 2


def test_new_upload_replaces_previous_dataset():
    df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    df2 = pd.DataFrame({"X": [10, 20, 30], "Y": [40, 50, 60]})

    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df1, "first.csv", "hash_first")
    assert len(AnalyticsManager.get_active_df()) == 2
    assert "A" in AnalyticsManager.get_active_df().columns

    AnalyticsManager.activate_user_dataset(df2, "second.csv", "hash_second")
    assert len(AnalyticsManager.get_active_df()) == 3
    assert "X" in AnalyticsManager.get_active_df().columns
    assert "A" not in AnalyticsManager.get_active_df().columns


def test_fingerprint_is_deterministic():
    content = b"header1,header2\nval1,val2\n"
    f1 = MockUploadedFile(content, "file1.csv")
    f2 = MockUploadedFile(content, "file2.csv")

    _, hash1 = UniversalDataLoader.load_file(f1)
    _, hash2 = UniversalDataLoader.load_file(f2)
    assert hash1 == hash2


def test_same_dataset_reuses_analysis():
    df = pd.DataFrame({"metric": [100, 200, 300]})
    AnalyticsManager.initialize()
    res1 = AnalyticsManager.activate_user_dataset(df, "data.csv", "same_hash")
    res2 = AnalyticsManager.activate_user_dataset(df, "data.csv", "same_hash")
    
    assert res1["dataset_id"] == res2["dataset_id"]
    assert res1["kpis"]["total_revenue"] == res2["kpis"]["total_revenue"]


def test_generic_dataset_does_not_use_olist_columns():
    df_hr = pd.DataFrame({
        "emp_name": ["Alice", "Bob"],
        "salary": [90000, 80000],
        "department": ["Dev", "Marketing"]
    })
    ctx = UniversalAnalytics.build_context(df_hr, "hr.csv")
    assert ctx.domain == "HR / Workforce Analytics"
    assert "freight_value" not in ctx.dataframe.columns
    assert "price" not in ctx.dataframe.columns
    assert ctx.generated_kpis["total_revenue"] == 170000.0
