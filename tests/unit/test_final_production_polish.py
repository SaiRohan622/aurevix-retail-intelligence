"""
AUREVIX — Final Production Polish, Performance & QA Test Suite
Comprehensive edge-case, error-proofing, multi-domain, and performance verification.
"""
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from dashboard.analytics.universal_analytics import UniversalAnalytics, UniversalAnalyticsContext
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from src.common.health import PlatformHealthChecker


# -----------------------------------------------------------------------------
# 1. EMPTY, ONE-ROW & ALL-NULL DATAFRAME HANDLING
# -----------------------------------------------------------------------------

def test_empty_dataframe_end_to_end_safety():
    df = pd.DataFrame()
    ctx = UniversalAnalytics.build_context(df, "empty.csv")
    assert ctx.is_empty is True
    assert ctx.row_count == 0
    
    prof = DataProfiler.profile(df, {})
    assert prof["row_count"] == 0
    assert prof["quality_score"] == 100.0
    
    metrics = MetricEngine.calculate_metrics(df, {})
    assert metrics == {}
    
    fig = ChartEngine.create_dimension_donut_chart(df, "cat", "val")
    assert fig is None
    
    ans = AskYourDataEngine.answer_question(df, "What are my total sales?", {}, {})
    assert "No active dataset" in ans["answer"]


def test_one_row_dataframe_safety():
    df = pd.DataFrame({
        "order_id": [101],
        "category": ["Electronics"],
        "price": [299.99],
        "order_date": ["2026-01-15"]
    })
    ctx = UniversalAnalytics.build_context(df, "one_row.csv")
    assert ctx.row_count == 1
    assert ctx.generated_kpis["total_revenue"] == 299.99
    assert ctx.quality_score >= 90.0


def test_all_null_dataframe_safety():
    df = pd.DataFrame({
        "col_a": [None, None, np.nan],
        "col_b": [np.nan, None, np.nan]
    })
    schema = SchemaDetector.detect_schema(df)
    prof = DataProfiler.profile(df, schema)
    assert prof["missing_pct"] == 100.0
    assert prof["quality_score"] < 50.0


# -----------------------------------------------------------------------------
# 2. MISSING DIMENSIONS & MEASURES RESILIENCE
# -----------------------------------------------------------------------------

def test_no_numeric_columns_dataset():
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "department": ["HR", "IT", "HR"],
        "city": ["New York", "Chicago", "Boston"]
    })
    schema = SchemaDetector.detect_schema(df)
    assert len(schema["numeric_columns"]) == 0
    
    metrics = MetricEngine.calculate_metrics(df, schema)
    assert metrics["total_revenue"] == 0.0
    assert metrics["unique_categories"] == 2


def test_no_categorical_columns_dataset():
    df = pd.DataFrame({
        "val_1": [10.5, 20.2, 30.8],
        "val_2": [100, 200, 300]
    })
    schema = SchemaDetector.detect_schema(df)
    assert len(schema["categorical_columns"]) == 0
    
    metrics = MetricEngine.calculate_metrics(df, schema)
    assert metrics["total_revenue"] == 61.5


def test_no_date_columns_dataset():
    df = pd.DataFrame({
        "item": ["A", "B", "C"],
        "cost": [10, 20, 30]
    })
    schema = SchemaDetector.detect_schema(df)
    assert len(schema["date_columns"]) == 0
    
    fig = ChartEngine.create_time_series_chart(df, "date", "cost")
    assert fig is None
    
    ans = AskYourDataEngine.answer_question(df, "Show sales by month", schema, {})
    assert "time-series analysis requires a recognizable datetime column" in ans["answer"]


def test_invalid_date_strings_handling():
    df = pd.DataFrame({
        "date_str": ["invalid_format_1", "invalid_format_2", "invalid_format_3"],
        "revenue": [100.0, 200.0, 300.0]
    })
    fig = ChartEngine.create_time_series_chart(df, "date_str", "revenue")
    assert fig is None


# -----------------------------------------------------------------------------
# 3. MISSING KPI / CHART COLUMNS DEFENSIVE DESIGN
# -----------------------------------------------------------------------------

def test_missing_chart_columns_returns_none():
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    assert ChartEngine.create_dimension_donut_chart(df, "NonExistent", "B") is None
    assert ChartEngine.create_dimension_bar_chart(df, "NonExistent", "B") is None
    assert ChartEngine.create_time_series_chart(df, "NonExistent", "B") is None
    assert ChartEngine.create_scatter_correlation_chart(df, "NonExistent", "B") is None


def test_unusual_column_names_kpis():
    df = pd.DataFrame({
        "custom_metric_xyz": [100, 200, 300],
        "custom_group_abc": ["Alpha", "Beta", "Alpha"]
    })
    schema = SchemaDetector.detect_schema(df)
    metrics = MetricEngine.calculate_metrics(df, schema)
    assert metrics["total_revenue"] == 600.0
    assert metrics["unique_categories"] == 2


# -----------------------------------------------------------------------------
# 4. LARGE DATASET PERFORMANCE SAMPLING
# -----------------------------------------------------------------------------

def test_large_dataset_profiling_performance():
    # 120,000 rows
    df_large = pd.DataFrame({
        "id": range(120000),
        "cat": [f"Cat_{i%10}" for i in range(120000)],
        "val": np.random.uniform(10.0, 500.0, size=120000)
    })
    schema = SchemaDetector.detect_schema(df_large)
    prof = DataProfiler.profile(df_large, schema)
    assert prof["is_sampled"] is True
    assert prof["sample_size"] <= 100000
    assert prof["row_count"] == 120000


# -----------------------------------------------------------------------------
# 5. DATASET SWITCHING & PERSISTENCE ISOLATION
# -----------------------------------------------------------------------------

def test_dataset_switching_complete_state_isolation():
    AnalyticsManager.initialize()
    
    df_sales = pd.DataFrame({"product": ["Laptop", "Phone"], "revenue": [1500.0, 800.0]})
    AnalyticsManager.activate_user_dataset(df_sales, "sales.csv", "hash_sales")
    
    assert AnalyticsManager.is_user_mode() is True
    assert AnalyticsManager.get_active_df().equals(df_sales)
    assert AnalyticsManager.get_analysis_results()["kpis"]["total_revenue"] == 2300.0
    
    df_hr = pd.DataFrame({"emp": ["John", "Sarah"], "salary": [90000.0, 110000.0]})
    AnalyticsManager.activate_user_dataset(df_hr, "hr.csv", "hash_hr")
    
    assert AnalyticsManager.get_active_df().equals(df_hr)
    assert AnalyticsManager.get_analysis_results()["kpis"]["total_revenue"] == 200000.0
    assert "product" not in AnalyticsManager.get_active_df().columns
    
    AnalyticsManager.revert_to_demo()
    assert AnalyticsManager.is_demo_mode() is True
    assert AnalyticsManager.get_active_df().empty


# -----------------------------------------------------------------------------
# 6. CLEANING ENGINE NON-DESTRUCTIVE RECIPES & UNDO / RESET
# -----------------------------------------------------------------------------

def test_cleaning_recipe_undo_and_reset():
    df_raw = pd.DataFrame({
        "dept": ["  Sales  ", "Engineering", "Sales", "HR"],
        "salary": [50000, 80000, 50000, 60000]
    })
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_raw, "raw_data.csv", "hash_clean_test")
    
    # 1. Apply strip whitespace
    clean_df, stats = AnalyticsManager.apply_cleaning_operation({
        "action": "strip_whitespace",
        "params": {"columns": ["dept"]}
    })
    assert clean_df["dept"].iloc[0] == "Sales"
    assert len(AnalyticsManager.get_cleaning_recipe()) == 1
    
    # Original raw DataFrame remains completely unchanged
    assert AnalyticsManager.get_original_raw_df()["dept"].iloc[0] == "  Sales  "
    
    # 2. Undo cleaning step
    popped = AnalyticsManager.undo_cleaning_operation()
    assert popped is not None
    assert len(AnalyticsManager.get_cleaning_recipe()) == 0
    assert AnalyticsManager.get_active_df()["dept"].iloc[0] == "  Sales  "
    
    # 3. Apply drop duplicates and reset
    clean_df2, stats2 = AnalyticsManager.apply_cleaning_operation({
        "action": "remove_duplicates",
        "params": {}
    })
    AnalyticsManager.reset_cleaning_pipeline()
    reset_df = AnalyticsManager.get_active_df()
    assert len(AnalyticsManager.get_cleaning_recipe()) == 0
    assert len(reset_df) == 4


# -----------------------------------------------------------------------------
# 7. COMPARISON & EXPORT CENTER DATASET AWARENESS
# -----------------------------------------------------------------------------

def test_comparison_engine_arbitrary_datasets():
    df1 = pd.DataFrame({"A": [1, 2, 3], "B": [10, 20, 30]})
    df2 = pd.DataFrame({"A": [1, 2, 3, 4], "C": [100, 200, 300, 400]})
    
    comp = ComparisonEngine.compare_datasets(df1, df2, "v1", "v2")
    assert comp["dataset_a"]["rows"] == 3
    assert comp["dataset_b"]["rows"] == 4
    assert comp["common_columns"] == ["A"]
    assert "B" in comp["columns_only_in_a"]
    assert "C" in comp["columns_only_in_b"]


def test_executive_report_generation_active_dataset():
    df = pd.DataFrame({
        "department": ["Engineering", "Product"],
        "salary": [120000.0, 100000.0]
    })
    ctx = UniversalAnalytics.build_context(df, "hr_report.csv")
    report_text = ctx.get_summary_report()
    
    assert "Executive Business Intelligence Report" in report_text
    assert "hr_report.csv" in report_text
    assert "HR / Workforce" in report_text


# -----------------------------------------------------------------------------
# 8. PLATFORM HEALTH PROBES
# -----------------------------------------------------------------------------

def test_platform_health_probes_validity():
    checker = PlatformHealthChecker()
    live = checker.check_liveness()
    assert live["status"] == "UP"
    assert "runtime" in live
    
    ready = checker.check_readiness()
    assert "ready" in ready
    assert "components" in ready
    assert ready["components"]["storage"]["status"] == "HEALTHY"
