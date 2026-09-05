"""
AUREVIX — Final Business Intelligence QA & UX Polish Test Suite
Verifies Initial vs Current State, Quality Deltas, Issue Explanations, Drilldown Filters, and Multi-Domain Resilience.
"""
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.universal_analytics import UniversalAnalytics, UniversalAnalyticsContext
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.data_cache import AnalyticsManager


def test_initial_vs_current_data_state_tracking():
    # Pristine dataset with 1 duplicate and 2 nulls
    df_raw = pd.DataFrame({
        "order_id": [1, 2, 2, 3],
        "customer": ["Alice", "Bob", "Bob", None],
        "amount": [100.0, 200.0, 200.0, 300.0]
    })
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_raw, "orders_raw.csv", "hash_orders_1")

    # Initial state
    assert AnalyticsManager.is_user_mode() is True
    init_df = AnalyticsManager.get_original_raw_df()
    assert len(init_df) == 4
    
    ws_state = AnalyticsManager.get_workspace_state()
    assert ws_state["original_rows"] == 4
    assert ws_state["raw_rows"] == 4
    assert ws_state["cleaning_steps_count"] == 0

    init_prof = ws_state.get("initial_profile") or AnalyticsManager.get_analysis_results().get("profile", {})
    init_score = init_prof.get("quality_score", 100.0)

    # 1. Clean: Remove duplicates
    clean_df, stats = AnalyticsManager.apply_cleaning_step({
        "action": "remove_duplicates",
        "params": {},
        "title": "Remove exact duplicate rows"
    })
    assert len(clean_df) == 3
    assert len(AnalyticsManager.get_original_raw_df()) == 4  # Pristine remains untouched
    assert len(AnalyticsManager.get_cleaning_recipe()) == 1

    curr_prof = AnalyticsManager.get_analysis_results().get("profile", {})
    curr_score = curr_prof.get("quality_score", 100.0)
    assert curr_score >= init_score  # Quality improved


def test_problematic_record_drilldown_filtering():
    df = pd.DataFrame({
        "emp_id": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "name": ["John", "Sarah", None, "Michael", "Emma", "David", "Lisa", "Robert", "Anna", "James"],
        "salary": [50000.0, 52000.0, 55000.0, 950000.0, 58000.0, 60000.0, 62000.0, 64000.0, 51000.0, 53000.0],  # 950k is statistical outlier
        "join_date": ["2020-01-15", "2021-06-20", "2019-11-05", "invalid_date", "2022-03-10", "2020-05-12", "2021-09-18", "2022-01-04", "2020-11-23", "2021-04-14"]
    })
    schema = SchemaDetector.detect_schema(df)
    prof = DataProfiler.profile(df, schema)

    # 1. Filter missing values
    null_rows = df[df.isnull().any(axis=1)]
    assert len(null_rows) == 1
    assert null_rows["emp_id"].iloc[0] == 103

    # 2. Filter outliers in salary
    outliers_dict = prof.get("outliers", {})
    assert "salary" in outliers_dict
    bounds = outliers_dict["salary"]
    s_num = pd.to_numeric(df["salary"], errors="coerce")
    outlier_rows = df[(s_num < bounds["lower_bound"]) | (s_num > bounds["upper_bound"])]
    assert len(outlier_rows) == 1
    assert outlier_rows["emp_id"].iloc[0] == 104

    # 3. Filter invalid dates
    s_dt = pd.to_datetime(df["join_date"], errors="coerce")
    invalid_date_rows = df[df["join_date"].notnull() & s_dt.isnull()]
    assert len(invalid_date_rows) == 1
    assert invalid_date_rows["emp_id"].iloc[0] == 104


def test_multi_domain_universal_datasets_no_olist_leakage():
    # A. HR dataset
    df_hr = pd.DataFrame({
        "employee_id": [1, 2, 3],
        "department": ["Engineering", "HR", "Sales"],
        "salary": [120000, 75000, 85000]
    })
    ctx_hr = UniversalAnalytics.build_context(df_hr, "hr_sample.csv")
    assert ctx_hr.domain == "HR / Workforce Analytics"
    assert "price" not in ctx_hr.dataframe.columns
    assert "freight_value" not in ctx_hr.dataframe.columns
    assert ctx_hr.generated_kpis["total_revenue"] == 280000.0

    # B. Finance dataset
    df_fin = pd.DataFrame({
        "account_id": ["AC1", "AC2", "AC3"],
        "income": [50000.0, 80000.0, 120000.0],
        "expense": [30000.0, 45000.0, 60000.0],
        "profit": [20000.0, 35000.0, 60000.0]
    })
    ctx_fin = UniversalAnalytics.build_context(df_fin, "finance_sample.csv")
    assert ctx_fin.domain == "Financial & Banking"
    assert ctx_fin.generated_kpis["total_revenue"] == 250000.0
    assert ctx_fin.generated_kpis["total_profit"] == 115000.0

    # C. Marketing dataset
    df_mkt = pd.DataFrame({
        "campaign_name": ["Spring_Promo", "Summer_Sale", "Retargeting"],
        "impressions": [10000, 25000, 15000],
        "clicks": [500, 1200, 800],
        "ad_spend": [1500.0, 3200.0, 2100.0]
    })
    ctx_mkt = UniversalAnalytics.build_context(df_mkt, "marketing_sample.csv")
    assert ctx_mkt.domain == "Marketing & Campaigns"
    assert ctx_mkt.generated_kpis["total_revenue"] == 6800.0


def test_data_ready_for_analysis_evaluation():
    # Clean dataset with 0 issues
    df_clean = pd.DataFrame({
        "item": ["Product A", "Product B", "Product C"],
        "units": [10, 20, 30],
        "unit_price": [15.0, 25.0, 35.0]
    })
    schema = SchemaDetector.detect_schema(df_clean)
    prof = DataProfiler.profile(df_clean, schema)

    assert prof["quality_score"] >= 95.0
    issues = prof.get("issues_summary", {})
    assert issues.get("total_issues", 0) == 0
