"""
AUREVIX — Data Workspace Symbols, Imports, and Dual-Comparison Verification
Validates that 10_Data_Workspace.py has all required imports (including DataProfiler),
and that all 8 workspace sections execute safely across diverse dataset shapes:
- One uploaded dataset
- Two uploaded datasets (Dual-Dataset comparison mode)
- Empty comparison state
- Datasets with missing values
- Datasets without numeric columns
- Datasets without date columns
- Isolation from Olist demo dataset
"""
import ast
import inspect
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.comparison_engine import ComparisonEngine


def test_10_data_workspace_ast_and_dataprofiler_import():
    """Verify that DataProfiler is properly imported and defined in 10_Data_Workspace.py."""
    ws_path = Path("dashboard/pages/10_Data_Workspace.py")
    assert ws_path.exists()
    code = ws_path.read_text(encoding="utf-8")
    tree = ast.parse(code)

    # Check that DataProfiler is imported
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for n in node.names:
                imported_names.add(n.name)
    
    assert "DataProfiler" in imported_names, "DataProfiler must be explicitly imported in 10_Data_Workspace.py"
    assert "ComparisonEngine" in imported_names
    assert "AnalyticsManager" in imported_names
    assert "UniversalDataLoader" in imported_names


def test_dataprofiler_profile_execution_on_arbitrary_datasets():
    """Verify DataProfiler.profile executes safely on various dataset shapes."""
    # 1. Dataset with missing values
    df_missing = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "category": ["A", "B", None, "D"],
        "amount": [10.5, None, 30.0, 40.0]
    })
    prof_missing = DataProfiler.profile(df_missing)
    assert isinstance(prof_missing, dict)
    assert "quality_score" in prof_missing
    assert prof_missing["missing_cells"] == 2

    # 2. Dataset without numeric columns
    df_no_numeric = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "status": ["Active", "Pending", "Active"],
        "country": ["US", "CA", "UK"]
    })
    prof_no_numeric = DataProfiler.profile(df_no_numeric)
    assert isinstance(prof_no_numeric, dict)
    assert "quality_score" in prof_no_numeric
    assert prof_no_numeric["row_count"] == 3

    # 3. Dataset without date columns
    df_no_date = pd.DataFrame({
        "sku": ["SKU1", "SKU2"],
        "qty": [100, 200]
    })
    prof_no_date = DataProfiler.profile(df_no_date)
    assert isinstance(prof_no_date, dict)
    assert "quality_score" in prof_no_date


def test_comparison_workspace_empty_state():
    """Verify comparison workspace operates cleanly when comparison state is empty."""
    AnalyticsManager.initialize()
    AnalyticsManager.clear_comparison_state()

    comp_state = AnalyticsManager.get_comparison_state()
    assert comp_state["dataset_a"] is None
    assert comp_state["dataset_b"] is None
    assert AnalyticsManager.has_comparison_datasets() is False


def test_comparison_workspace_one_uploaded_dataset():
    """Verify comparison workspace when only Dataset A is loaded."""
    AnalyticsManager.initialize()
    AnalyticsManager.clear_comparison_state()

    df_a = pd.DataFrame({"product": ["A", "B"], "revenue": [500.0, 700.0]})
    AnalyticsManager.set_comparison_dataset_a(df_a, "Products_A.csv", "hash_pa")

    comp_state = AnalyticsManager.get_comparison_state()
    assert comp_state["dataset_a"] is not None
    assert comp_state["dataset_b"] is None
    assert AnalyticsManager.has_comparison_datasets() is False

    prof_a = DataProfiler.profile(df_a)
    assert prof_a.get("quality_score") is not None


def test_comparison_workspace_two_uploaded_datasets_and_comparison_engine():
    """Verify full dual-dataset comparison flow with two distinct datasets."""
    df_a = pd.DataFrame({
        "order_id": ["101", "102", "103"],
        "sales": [150.0, 250.0, 350.0],
        "category": ["Tech", "Office", "Tech"],
        "date": ["2025-01-01", "2025-01-02", "2025-01-03"]
    })
    df_b = pd.DataFrame({
        "order_id": ["102", "103", "104"],
        "sales": [270.0, 360.0, 480.0],
        "category": ["Office", "Tech", "Furniture"],
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"]
    })

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "Sales_2025.csv", "hash_2025")
    AnalyticsManager.set_comparison_dataset_b(df_b, "Sales_2026.csv", "hash_2026")

    assert AnalyticsManager.has_comparison_datasets() is True

    # Profiling both datasets
    prof_a = DataProfiler.profile(df_a)
    prof_b = DataProfiler.profile(df_b)
    assert prof_a["quality_score"] == 100.0
    assert prof_b["quality_score"] == 100.0

    # Comparison computation
    schema_match = ComparisonEngine.match_schemas(df_a, df_b)
    assert schema_match["match_rate_pct"] == 100.0

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "Sales_2025.csv", "Sales_2026.csv", schema_match["matched"])
    AnalyticsManager.set_comparison_results(comp_res)

    saved_res = AnalyticsManager.get_comparison_state()["comparison_results"]
    assert "numeric_metrics" in saved_res
    assert "quality_comparison" in saved_res
    assert len(saved_res["insights"]) > 0


def test_comparison_workspace_no_numeric_columns():
    """Verify comparison engine behaves defensively when datasets have no numeric columns."""
    df_a = pd.DataFrame({"code": ["C1", "C2"], "dept": ["HR", "IT"]})
    df_b = pd.DataFrame({"code": ["C2", "C3"], "dept": ["IT", "Sales"]})

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "Staff_A", "Staff_B")
    assert comp_res["available"] is True
    assert len(comp_res["numeric_metrics"]) == 0
    assert comp_res["row_difference"] == 0


def test_comparison_workspace_no_date_columns():
    """Verify comparison trend overlay behaves gracefully when date columns are absent."""
    df_a = pd.DataFrame({"id": [1, 2], "score": [80, 90]})
    df_b = pd.DataFrame({"id": [2, 3], "score": [85, 95]})

    trend_res = ComparisonEngine.compare_trends(df_a, df_b, "missing_date", "missing_date", "score", "score")
    assert trend_res["available"] is False


def test_dual_comparison_isolation_from_olist():
    """Verify dual-dataset comparison never injects Olist columns."""
    df_a = pd.DataFrame({"employee": ["E1", "E2"], "hours": [40, 45]})
    df_b = pd.DataFrame({"employee": ["E1", "E3"], "hours": [38, 42]})

    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "Timesheet_A", "Timesheet_B")
    for olist_col in ["freight_value", "order_purchase_timestamp", "product_category_name", "olist_production_gold"]:
        assert olist_col not in comp_res["common_columns"]
        assert olist_col not in comp_res["numeric_metrics"]
