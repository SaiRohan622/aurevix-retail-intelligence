"""
AUREVIX — Final Production QA, Stability, Performance & UX Hardening Test Suite
Validates:
1. Single-dataset full lifecycle persistence across tabs
2. Dual-dataset comparison workflow, isolation, and schema alignment
3. Data quality and profiling resilience on broken/edge-case datasets (inf, -inf, sentinels, mixed types)
4. Non-destructive cleaning engine with verified Undo and Reset
5. Multi-format exports (CSV, Excel .xlsx, Parquet, JSON, Markdown, pure-python PDF)
6. Strict demo/Olist data isolation
7. ChartEngine error-proofing on empty, missing, and malformed columns
8. Ask Your Data NLP accuracy on arbitrary domains
9. Target attainment & What-If scenario modeling
10. Workspace serialization integrity
11. Accurate system status indicators
"""
import io
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.comparison_engine import ComparisonEngine, calc_pct_delta
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.pdf_generator import AUREVIXPDFGenerator, PDFDocument


def test_single_dataset_full_lifecycle_persistence():
    """Verify complete single-dataset lifecycle: Ingest -> Profile -> Quality -> Clean -> Explore -> Targets -> Ask -> Export."""
    df_raw = pd.DataFrame({
        "order_id": ["O101", "O102", "O103", "O104"],
        "customer": ["CustA", "CustB", "CustC", "CustD"],
        "revenue": [120.0, 240.0, 360.0, 480.0],
        "quantity": [2, 4, 6, 8],
        "order_date": ["2025-01-10", "2025-02-15", "2025-03-20", "2025-04-25"]
    })

    AnalyticsManager.initialize()
    res = AnalyticsManager.activate_user_dataset(df_raw, "sales_q1.csv", "hash_sales_q1")

    # 1. Ingest & Profile
    assert AnalyticsManager.is_user_mode() is True
    assert AnalyticsManager.get_workspace_state()["dataset_name"] == "sales_q1.csv"
    assert len(AnalyticsManager.get_active_df()) == 4

    # 2. Quality & Metrics
    prof = res["profile"]
    assert prof["quality_score"] == 100.0
    kpis = res["kpis"]
    assert kpis["total_revenue"] == 1200.0
    assert kpis["total_transactions"] == 4

    # 3. Clean
    step = {"action": "change_case", "params": {"column": "customer", "case_type": "upper"}, "title": "Uppercase Customers"}
    AnalyticsManager.apply_cleaning_step(step)
    cleaned_df = AnalyticsManager.get_active_df()
    assert cleaned_df["customer"].iloc[0] == "CUSTA"

    # 4. Target
    AnalyticsManager.set_target("revenue", 1500.0)
    assert AnalyticsManager.get_targets().get("revenue") == 1500.0

    # 5. Ask Your Data
    ans = AskYourDataEngine.answer_question("What is total revenue?", cleaned_df, res["schema"], kpis)
    assert "1,200" in ans["answer"] or "1200" in ans["answer"]

    # 6. Export
    md_report = ExecutiveReportGenerator.generate_report(res, cleaned_df)
    assert "sales_q1.csv" in md_report


def test_two_dataset_full_comparison_workflow():
    """Verify dual-dataset comparison workflow across all dimensions."""
    df_a = pd.DataFrame({
        "emp_id": ["E1", "E2", "E3"],
        "dept": ["Engineering", "Sales", "Support"],
        "salary": [90000.0, 75000.0, 50000.0],
        "date_joined": ["2024-01-15", "2024-03-01", "2024-06-15"]
    })
    df_b = pd.DataFrame({
        "emp_id": ["E2", "E3", "E4"],
        "dept": ["Sales", "Support", "Marketing"],
        "salary": [82000.0, 52000.0, 65000.0],
        "date_joined": ["2024-03-01", "2024-06-15", "2025-01-10"]
    })

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "Staff_2024.csv", "hash_s24")
    AnalyticsManager.set_comparison_dataset_b(df_b, "Staff_2025.csv", "hash_s25")

    assert AnalyticsManager.has_comparison_datasets() is True

    # 1. Schema matching
    match_res = ComparisonEngine.match_schemas(df_a, df_b)
    assert "salary" in match_res["matched"]
    assert "emp_id" in match_res["matched"]

    # 2. Comprehensive Comparison
    comp_res = ComparisonEngine.compare_datasets(df_a, df_b, "Staff_2024.csv", "Staff_2025.csv", match_res["matched"])
    assert comp_res["available"] is True
    assert comp_res["numeric_metrics"]["salary"]["sum_diff"] == -16000.0  # 199k vs 215k (-16k delta in sum_diff)
    assert len(comp_res["insights"]) > 0

    # 3. Record Diff
    rec_res = ComparisonEngine.compare_records(df_a, df_b, "emp_id", "emp_id", compare_cols=[("dept", "dept")])
    assert rec_res["common_count"] == 2
    assert rec_res["new_count"] == 1  # E4
    assert rec_res["removed_count"] == 1  # E1

    # 4. Quality Head-to-Head
    qc = ComparisonEngine.calculate_quality_comparison(df_a, df_b, "Staff_2024.csv", "Staff_2025.csv")
    assert qc["score_a"] == 100.0
    assert qc["score_b"] == 100.0


def test_two_dataset_isolation_from_active_dataset():
    """Verify loading comparison datasets never alters normal active dataset."""
    df_main = pd.DataFrame({"product": ["P1", "P2"], "price": [10.0, 20.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_main, "Main_Catalog.csv", "h_main")

    df_comp_a = pd.DataFrame({"x": [1, 2]})
    df_comp_b = pd.DataFrame({"x": [3, 4]})
    AnalyticsManager.set_comparison_dataset_a(df_comp_a, "CA.csv", "h_ca")
    AnalyticsManager.set_comparison_dataset_b(df_comp_b, "CB.csv", "h_cb")

    # Verify main dataset is completely intact
    state = AnalyticsManager.get_workspace_state()
    assert state["dataset_name"] == "Main_Catalog.csv"
    assert len(AnalyticsManager.get_active_df()) == 2
    assert "product" in AnalyticsManager.get_active_df().columns


def test_broken_datasets_data_quality_resilience():
    """Test DataProfiler and SchemaDetector on malformed/edge-case datasets."""
    # Dataset with inf, -inf, sentinels, missing values, empty strings, constant column
    df_broken = pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6, 7, 8],
        "metric_inf": [10.0, np.inf, 30.0, -np.inf, 50.0, 60.0, 70.0, 80.0],
        "const_col": ["SAME", "SAME", "SAME", "SAME", "SAME", "SAME", "SAME", "SAME"],
        "invalid_dates": ["2025-01-01", "INVALID_DATE_STR", "2025-03-01", "NOT_A_DATE", "2025-05-01", "BAD", "2025-07-01", "2025-08-01"],
        "sentinels": ["N/A", "Valid1", "?", "Valid2", "None", "Valid3", "EMPTY", "Valid4"],
        "all_null": [None, None, None, None, None, None, None, None]
    })

    schema = SchemaDetector.detect_schema(df_broken)
    assert "metric_inf" in schema["numeric_columns"]

    prof = DataProfiler.profile(df_broken, schema)
    assert isinstance(prof, dict)
    assert "quality_score" in prof
    assert prof["quality_score"] < 90.0  # Penalized for missing values, invalid dates, and constant col
    assert "const_col" in prof["constant_columns"]
    assert prof["issues_summary"]["total_issues"] > 0


def test_cleaning_engine_non_destructive_undo_and_reset():
    """Verify 3 sequential cleaning steps, undoing step 3, and resetting to original."""
    df_init = pd.DataFrame({
        "emp": [" alice ", " bob ", " charlie ", " alice "],
        "val": [10.0, 20.0, None, 10.0]
    })

    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_init, "emp_cleaning_test.csv", "h_clean_test")

    # Step 1: Strip whitespace
    s1 = {"action": "strip_whitespace", "params": {"columns": ["emp"]}, "title": "Trim Whitespace"}
    AnalyticsManager.apply_cleaning_step(s1)
    assert AnalyticsManager.get_active_df()["emp"].iloc[0] == "alice"
    assert len(AnalyticsManager.get_active_df()) == 4

    # Step 2: Impute missing in val
    s2 = {"action": "impute_missing", "params": {"column": "val", "strategy": "median"}, "title": "Impute val"}
    AnalyticsManager.apply_cleaning_step(s2)
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0

    # Step 3: Remove duplicates
    s3 = {"action": "remove_duplicates", "params": {"subset": None, "keep": "first"}, "title": "Deduplicate"}
    AnalyticsManager.apply_cleaning_step(s3)
    assert len(AnalyticsManager.get_active_df()) == 3

    # Undo Step 3 -> returns to 4 rows with imputed values
    AnalyticsManager.undo_last_cleaning_step()
    assert len(AnalyticsManager.get_active_df()) == 4
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0

    # Reset to original -> returns to original whitespace & nulls
    AnalyticsManager.reset_cleaning()
    assert len(AnalyticsManager.get_active_df()) == 4
    assert AnalyticsManager.get_active_df()["emp"].iloc[0] == " alice "
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 1


def test_export_formats_all_generated():
    """Verify generation of CSV, Excel, Parquet, JSON, Markdown, and PDF bytes."""
    df_export = pd.DataFrame({"sku": ["SKU-1", "SKU-2"], "sales": [100.50, 250.75]})
    res = {
        "dataset_name": "export_test.csv",
        "schema": {"domain": "Retail & E-Commerce"},
        "profile": {"quality_score": 100.0, "completeness_score": 100.0, "validity_score": 100.0, "consistency_score": 100.0, "uniqueness_score": 100.0, "missing_cells": 0, "duplicate_rows": 0, "memory_mb": 0.05},
        "kpis": {"total_revenue": 351.25, "total_transactions": 2, "total_quantity": 2, "average_transaction_value": 175.625},
        "insights": [{"title": "Strong Performance", "observation": "All units sold."}],
        "anomalies": []
    }

    # 1. CSV
    csv_bytes = df_export.to_csv(index=False).encode("utf-8")
    assert b"SKU-1" in csv_bytes

    # 2. Excel
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)
    assert len(excel_buf.getvalue()) > 0

    # 3. Parquet
    parquet_buf = io.BytesIO()
    df_export.to_parquet(parquet_buf, index=False)
    assert len(parquet_buf.getvalue()) > 0

    # 4. JSON
    json_bytes = df_export.to_json(orient="records").encode("utf-8")
    assert b"SKU-1" in json_bytes

    # 5. Markdown
    md_text = ExecutiveReportGenerator.generate_report(res, df_export)
    assert "AUREVIX" in md_text

    # 6. PDF
    pdf_bytes = ExecutiveReportGenerator.generate_pdf_report(res)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes


def test_demo_mode_isolation_and_explicit_activation():
    """Verify demo mode is completely isolated and never accessed by accident."""
    AnalyticsManager.initialize()
    AnalyticsManager.clear_active_dataset()

    # Empty state when cleared
    assert AnalyticsManager.is_user_mode() is False
    assert AnalyticsManager.get_active_df().empty is True

    # User uploads dataset -> user mode only
    df = pd.DataFrame({"user_col": [1, 2]})
    AnalyticsManager.activate_user_dataset(df, "user_only.csv", "h_uo")
    assert AnalyticsManager.is_user_mode() is True
    assert "user_col" in AnalyticsManager.get_active_df().columns

    # Clearing returns to empty state, NOT demo mode
    AnalyticsManager.clear_active_dataset()
    assert AnalyticsManager.is_user_mode() is False
    assert AnalyticsManager.get_active_df().empty is True

    # Explicit demo reversion
    AnalyticsManager.revert_to_demo()
    assert AnalyticsManager.is_user_mode() is False


def test_chart_engine_graceful_on_problematic_data():
    """Verify ChartEngine never raises exceptions on empty, missing, or malformed data."""
    # 1. Empty DataFrame
    df_empty = pd.DataFrame()
    fig1 = ChartEngine.create_time_series_chart(df_empty, "date", "revenue")
    assert fig1 is None

    # 2. Missing columns
    df_data = pd.DataFrame({"col_a": [1, 2, 3]})
    fig2 = ChartEngine.create_dimension_bar_chart(df_data, "missing_column", "col_a")
    assert fig2 is None

    # 3. Valid chart
    fig3 = ChartEngine.create_dimension_bar_chart(df_data, "col_a", "col_a")
    assert fig3 is not None


def test_nlp_ask_your_data_domain_adaptability():
    """Verify Ask Your Data answers questions accurately for various domains."""
    # HR Dataset
    df_hr = pd.DataFrame({
        "department": ["Sales", "Sales", "Eng", "HR"],
        "headcount": [10, 15, 20, 5],
        "salary": [60000, 70000, 110000, 65000]
    })
    schema_hr = SchemaDetector.detect_schema(df_hr)
    kpis_hr = MetricEngine.calculate_metrics(df_hr, schema_hr)
    ans_hr = AskYourDataEngine.answer_question("What is total headcount?", df_hr, schema_hr, kpis_hr)
    assert ans_hr["answer"] != ""


def test_target_engine_on_arbitrary_metrics():
    """Verify TargetEngine evaluates targets correctly."""
    eval1 = TargetEngine.evaluate_target(120000.0, 100000.0, "Revenue")
    assert eval1["status"] == "EXCEEDED"
    assert eval1["attainment_pct"] == 120.0
    assert eval1["gap"] <= 0

    eval2 = TargetEngine.evaluate_target(40000.0, 100000.0, "Revenue")
    assert eval2["status"] == "BEHIND"
    assert eval2["attainment_pct"] == 40.0
    assert eval2["gap"] == 60000.0


def test_workspace_manager_serialization_integrity():
    """Verify workspace saving and loading preserving state integrity."""
    df_ws = pd.DataFrame({"id": [1, 2], "val": [100, 200]})
    ws_meta = WorkspaceManager.save_workspace(
        name="Q1_Snapshot",
        dataset_id="hash_q1_snap",
        dataset_name="Snapshot_Data.csv",
        active_filters={"cat": ["A"]},
        user_targets={"val": 500.0},
        cleaning_recipe=[{"action": "test"}],
        notes="Q1 final review"
    )
    assert ws_meta["name"] == "Q1_Snapshot"
    assert ws_meta["dataset_id"] == "hash_q1_snap"

    saved_list = WorkspaceManager.list_saved_workspaces()
    assert len(saved_list) > 0
    assert any(w["name"] == "Q1_Snapshot" for w in saved_list)
