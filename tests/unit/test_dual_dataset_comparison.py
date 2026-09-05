"""
AUREVIX — Enterprise Dual-Dataset Comparison Test Suite
Validates schema matching, KPI deltas, record-level diffing, category & trend shifts,
data quality comparisons, division-by-zero protection, state isolation, and caching.
"""
import io
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.comparison_engine import ComparisonEngine, calc_pct_delta
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.report_generator import ExecutiveReportGenerator


def test_two_dataset_upload():
    df_a = pd.DataFrame({"cust_id": [1, 2, 3], "revenue": [100.0, 200.0, 300.0]})
    df_b = pd.DataFrame({"customer_id": [2, 3, 4], "sales": [250.0, 350.0, 450.0]})

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "Sales_2024.csv", "hash_a_123")
    AnalyticsManager.set_comparison_dataset_b(df_b, "Sales_2025.csv", "hash_b_456")

    assert AnalyticsManager.has_comparison_datasets() is True
    comp_state = AnalyticsManager.get_comparison_state()
    assert comp_state["dataset_a_name"] == "Sales_2024.csv"
    assert comp_state["dataset_b_name"] == "Sales_2025.csv"
    assert len(comp_state["dataset_a"]) == 3
    assert len(comp_state["dataset_b"]) == 3


def test_dataset_a_persistence():
    df_a = pd.DataFrame({"id": [10, 20], "amount": [50.0, 60.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "A.csv", "ha")

    # Access multiple times
    st1 = AnalyticsManager.get_comparison_state()
    assert st1["dataset_a_fingerprint"] == "ha"
    assert len(st1["dataset_a"]) == 2


def test_dataset_b_persistence():
    df_b = pd.DataFrame({"id": [10, 20, 30], "amount": [55.0, 65.0, 75.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_b(df_b, "B.csv", "hb")

    st1 = AnalyticsManager.get_comparison_state()
    assert st1["dataset_b_fingerprint"] == "hb"
    assert len(st1["dataset_b"]) == 3


def test_schema_matching():
    df_a = pd.DataFrame({
        "revenue": [100.0, 200.0],
        "customer_id": ["C1", "C2"],
        "order_date": ["2024-01-01", "2024-01-02"],
        "unmatched_a_col": [1, 2]
    })
    df_b = pd.DataFrame({
        "sales": [120.0, 220.0],
        "client": ["C1", "C2"],
        "transaction_date": ["2025-01-01", "2025-01-02"],
        "unmatched_b_col": [3, 4]
    })

    match_res = ComparisonEngine.match_schemas(df_a, df_b)
    matched = match_res["matched"]

    assert "revenue" in matched and matched["revenue"] == "sales"
    assert "customer_id" in matched and matched["customer_id"] == "client"
    assert "order_date" in matched and matched["order_date"] == "transaction_date"
    assert "unmatched_a_col" in match_res["unmatched_a"]
    assert "unmatched_b_col" in match_res["unmatched_b"]
    assert match_res["match_rate_pct"] == 75.0


def test_manual_column_mapping():
    df_a = pd.DataFrame({"metric_alpha": [10, 20], "cat_alpha": ["X", "Y"]})
    df_b = pd.DataFrame({"metric_beta": [15, 25], "cat_beta": ["X", "Y"]})

    custom_mapping = {"metric_alpha": "metric_beta", "cat_alpha": "cat_beta"}
    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "A", "B", schema_mapping=custom_mapping)

    assert "metric_alpha" in comp_res["numeric_metrics"]
    m = comp_res["numeric_metrics"]["metric_alpha"]
    assert m["sum_a"] == 30.0
    assert m["sum_b"] == 40.0
    assert m["sum_diff"] == 10.0


def test_numeric_comparison():
    df_a = pd.DataFrame({"amount": [100.0, 200.0, 300.0]})
    df_b = pd.DataFrame({"amount": [150.0, 250.0, 500.0]})

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "2024", "2025")
    m = comp_res["numeric_metrics"]["amount"]

    assert m["sum_a"] == 600.0
    assert m["sum_b"] == 900.0
    assert m["sum_diff"] == 300.0
    assert m["sum_pct"] == 50.0
    assert m["mean_a"] == 200.0
    assert m["mean_b"] == 300.0
    assert m["min_a"] == 100.0
    assert m["min_b"] == 150.0
    assert m["max_a"] == 300.0
    assert m["max_b"] == 500.0


def test_categorical_comparison():
    df_a = pd.DataFrame({"dept": ["Sales", "Sales", "Eng", "HR"], "val": [10, 20, 30, 40]})
    df_b = pd.DataFrame({"dept": ["Sales", "Eng", "Eng", "Marketing"], "val": [15, 35, 45, 50]})

    cat_res = ComparisonEngine.compare_categories(df_a, df_b, "dept", "dept", "val", "val")
    assert cat_res["available"] is True
    assert "Marketing" in cat_res["categories_only_in_b"]
    assert "HR" in cat_res["categories_only_in_a"]
    assert len(cat_res["data"]) == 4


def test_date_comparison():
    df_a = pd.DataFrame({"dt": ["2024-01-15", "2024-02-15"], "rev": [1000, 2000]})
    df_b = pd.DataFrame({"dt": ["2025-01-15", "2025-02-15"], "rev": [1500, 2500]})

    trend_res = ComparisonEngine.compare_trends(df_a, df_b, "dt", "dt", "rev", "rev", granularity="Month")
    assert trend_res["available"] is True
    assert len(trend_res["ts_a"]) == 2
    assert len(trend_res["ts_b"]) == 2


def test_record_level_comparison():
    df_a = pd.DataFrame({
        "order_id": ["O1", "O2", "O3"],
        "status": ["Completed", "Active", "Shipped"]
    })
    df_b = pd.DataFrame({
        "order_id": ["O2", "O3", "O4"],
        "status": ["Active", "Delivered", "New"]  # O2 is Active in both, O3 changed from Shipped to Delivered
    })

    rec_res = ComparisonEngine.compare_records(df_a, df_b, "order_id", "order_id", compare_cols=[("status", "status")])
    assert rec_res["available"] is True
    assert rec_res["common_count"] == 2  # O2, O3
    assert rec_res["new_count"] == 1     # O4
    assert rec_res["removed_count"] == 1 # O1
    assert rec_res["changed_count"] == 1 # O3 status changed


def test_quality_comparison():
    df_a = pd.DataFrame({"col1": [1, 2, None, 4], "col2": ["A", "B", "C", "D"]})
    df_b = pd.DataFrame({"col1": [1, 2, 3, 4], "col2": ["A", "B", "A", "D"]})

    qc = ComparisonEngine.calculate_quality_comparison(df_a, df_b, "A", "B")
    assert "score_a" in qc
    assert "score_b" in qc
    assert qc["missing_cells_a"] == 1
    assert qc["missing_cells_b"] == 0
    assert qc["missing_delta"] == -1


def test_percentage_delta_zero_division():
    assert calc_pct_delta(0.0, 0.0) == 0.0
    assert calc_pct_delta(0.0, 50.0) == 100.0
    assert calc_pct_delta(0.0, -50.0) == -100.0
    assert calc_pct_delta(100.0, 150.0) == 50.0
    assert calc_pct_delta(200.0, 100.0) == -50.0


def test_incompatible_schema():
    df_a = pd.DataFrame({"col_x": [1, 2]})
    df_b = pd.DataFrame({"col_y": [3, 4]})

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "A", "B")
    assert comp_res["available"] is True
    assert len(comp_res["common_columns"]) == 0
    assert len(comp_res["columns_only_in_a"]) == 1
    assert len(comp_res["columns_only_in_b"]) == 1


def test_comparison_cache():
    df_a = pd.DataFrame({"val": [10, 20]})
    df_b = pd.DataFrame({"val": [15, 25]})

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "A.csv", "ha_cache")
    AnalyticsManager.set_comparison_dataset_b(df_b, "B.csv", "hb_cache")

    res1 = ComparisonEngine.compare_datasets(df_a, df_b, "A", "B")
    AnalyticsManager.set_comparison_results(res1)

    cached_state = AnalyticsManager.get_comparison_state()
    assert cached_state["comparison_results"]["numeric_metrics"]["val"]["sum_diff"] == 10.0


def test_comparison_does_not_use_olist_demo_data():
    df_a = pd.DataFrame({"employee_name": ["Alice", "Bob"], "bonus": [5000, 6000]})
    df_b = pd.DataFrame({"employee_name": ["Alice", "Bob", "Charlie"], "bonus": [5500, 6500, 7000]})

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "HR_2024", "HR_2025")
    assert "freight_value" not in comp_res["common_columns"]
    assert "order_purchase_timestamp" not in comp_res["common_columns"]
    assert "product_category_name" not in comp_res["common_columns"]
    assert "bonus" in comp_res["numeric_metrics"]


def test_existing_single_dataset_workflow_unchanged():
    # Verify that single-dataset active workflow is 100% isolated and unaffected
    df_single = pd.DataFrame({"sku": ["SKU1", "SKU2"], "price": [99.0, 199.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_single, "active_catalog.csv", "hash_active_cat")

    assert AnalyticsManager.is_user_mode() is True
    assert len(AnalyticsManager.get_active_df()) == 2
    assert AnalyticsManager.get_workspace_state()["dataset_name"] == "active_catalog.csv"

    # Now load comparison datasets
    df_comp_a = pd.DataFrame({"x": [1]})
    df_comp_b = pd.DataFrame({"x": [2]})
    AnalyticsManager.set_comparison_dataset_a(df_comp_a, "CompA.csv", "h_ca")
    AnalyticsManager.set_comparison_dataset_b(df_comp_b, "CompB.csv", "h_cb")

    # Single-dataset active data remains 100% intact!
    assert AnalyticsManager.get_workspace_state()["dataset_name"] == "active_catalog.csv"
    assert len(AnalyticsManager.get_active_df()) == 2
    assert "sku" in AnalyticsManager.get_active_df().columns
