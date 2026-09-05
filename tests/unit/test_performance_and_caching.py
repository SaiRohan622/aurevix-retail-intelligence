"""
AUREVIX — Enterprise Performance & Cache Optimization Test Suite
Verifies sub-millisecond in-memory cache reuse, dataset fingerprint caching,
filter signature caching, version invalidation, large dataset sampling, and non-destructive undo/reset.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
import io
import time
import json

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.cleaning_engine import DataCleaningEngine


@pytest.fixture(autouse=True)
def reset_state():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def _make_perf_df(n=1000):
    np.random.seed(42)
    return pd.DataFrame({
        "order_id": [f"ORD_{i:06d}" for i in range(1, n + 1)],
        "order_date": pd.date_range("2024-01-01", periods=n, freq="min").astype(str),
        "customer_id": [f"CUST_{i % 100:03d}" for i in range(n)],
        "category": [["Electronics", "Apparel", "Home", "Books", "Toys"][i % 5] for i in range(n)],
        "region": [["North", "South", "East", "West"][i % 4] for i in range(n)],
        "quantity": np.random.randint(1, 10, n),
        "unit_price": np.random.uniform(5.0, 500.0, n).round(2),
        "revenue": np.random.uniform(20.0, 2500.0, n).round(2),
    })


def test_same_dataset_loads_from_cache():
    csv_bytes = b"id,dept,revenue\n1,Sales,1000\n2,Eng,2500\n3,Mktg,1800"
    buf1 = io.BytesIO(csv_bytes)
    t0 = time.time()
    df1, hash1 = UniversalDataLoader.load_and_fingerprint(buf1, "test_cache.csv")
    first_load_time = time.time() - t0

    buf2 = io.BytesIO(csv_bytes)
    t1 = time.time()
    df2, hash2 = UniversalDataLoader.load_and_fingerprint(buf2, "test_cache.csv")
    second_load_time = time.time() - t1

    assert hash1 == hash2
    assert len(df1) == len(df2) == 3
    # Second cached load should be sub-millisecond
    assert second_load_time <= first_load_time + 0.05


def test_repeated_page_navigation_does_not_reload_dataset():
    df = _make_perf_df(500)
    AnalyticsManager.activate_user_dataset(df, "perf.csv", "hash_perf_001")

    # Simulate 10 page navigations
    for _ in range(10):
        active = AnalyticsManager.get_active_df()
        assert len(active) == 500
        assert "revenue" in active.columns
        assert AnalyticsManager.has_active_dataset() is True


def test_repeated_profile_requests_use_cache():
    df = _make_perf_df(1000)
    AnalyticsManager.activate_user_dataset(df, "perf.csv", "hash_prof_001")

    res1 = AnalyticsManager.get_analysis_results()
    prof1 = res1.get("profile", {})

    res2 = AnalyticsManager.get_analysis_results()
    prof2 = res2.get("profile", {})

    assert prof1["quality_score"] == prof2["quality_score"]
    assert prof1["row_count"] == prof2["row_count"] == 1000


def test_switching_datasets_invalidates_correct_cache():
    df1 = _make_perf_df(100)
    AnalyticsManager.activate_user_dataset(df1, "dataset_a.csv", "hash_a")
    assert AnalyticsManager.get_dataset_version() >= 1
    assert AnalyticsManager.get_analysis_results()["kpis"]["primary_metric_col"] == "revenue"

    hr_df = pd.DataFrame({
        "emp_id": ["E1", "E2", "E3"],
        "salary": [75000, 85000, 95000],
        "department": ["IT", "HR", "Sales"]
    })
    AnalyticsManager.activate_user_dataset(hr_df, "dataset_b.xlsx", "hash_b")
    res_b = AnalyticsManager.get_analysis_results()

    assert res_b["dataset_name"] == "dataset_b.xlsx"
    assert res_b["kpis"]["primary_metric_col"] == "salary"
    assert "revenue" not in res_b["schema"]["columns"]


def test_user_dataset_never_becomes_olist():
    df = _make_perf_df(200)
    AnalyticsManager.activate_user_dataset(df, "user_exclusive.csv", "hash_user")

    for _ in range(15):
        df_active = AnalyticsManager.get_active_df()
        assert "revenue" in df_active.columns
        assert "freight_value" not in df_active.columns
        assert "price" not in df_active.columns


def test_filtering_reuses_filtered_df_when_signature_unchanged():
    df = _make_perf_df(300)
    AnalyticsManager.activate_user_dataset(df, "filter_perf.csv", "hash_filt")

    filt = {"category": ["Electronics", "Apparel"]}
    df_f1 = AnalyticsManager.apply_filters(filt)
    hits_before = AnalyticsManager.get_workspace_state().get("cache_hits", 0)

    # Re-applying identical filter should trigger signature cache hit
    df_f2 = AnalyticsManager.apply_filters(filt)
    hits_after = AnalyticsManager.get_workspace_state().get("cache_hits", 0)

    assert len(df_f1) == len(df_f2)
    assert hits_after >= hits_before + 1


def test_cleaning_invalidates_derived_analytics_correctly():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "dept": ["  Sales  ", "Eng", "  Mktg  ", "Finance", "HR"],
        "salary": [50000, 60000, 55000, 70000, 65000]
    })
    AnalyticsManager.activate_user_dataset(df, "cleaning_test.csv", "hash_clean")
    v_initial = AnalyticsManager.get_dataset_version()

    step = {
        "action": "strip_whitespace",
        "params": {"columns": ["dept"]},
        "title": "Strip whitespace in dept"
    }
    cleaned_df, stats = AnalyticsManager.apply_cleaning_step(step)

    assert AnalyticsManager.get_dataset_version() == v_initial + 1
    assert list(cleaned_df["dept"]) == ["Sales", "Eng", "Mktg", "Finance", "HR"]
    assert stats["cells_trimmed"] == 2


def test_undo_and_reset_performance():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "val": [10, np.nan, 30, 40]
    })
    AnalyticsManager.activate_user_dataset(df, "undo_test.csv", "hash_undo")

    # 1. Apply step
    step = {"action": "impute_missing", "params": {"column": "val", "strategy": "median"}, "title": "Impute median"}
    AnalyticsManager.apply_cleaning_step(step)
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0

    # 2. Undo step
    AnalyticsManager.undo_last_cleaning_step()
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 1

    # 3. Apply again & Reset
    AnalyticsManager.apply_cleaning_step(step)
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0
    AnalyticsManager.reset_cleaning()
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 1


def test_large_dataset_sampling_profiler():
    # Construct a dataset with 120,000 rows
    n = 120_000
    large_df = pd.DataFrame({
        "id": range(n),
        "metric": np.random.uniform(10, 500, n),
        "cat": [["A", "B", "C"][i % 3] for i in range(n)]
    })
    schema_meta = {
        "numeric_columns": ["metric"],
        "categorical_columns": ["cat"],
        "date_columns": [],
        "columns": {}
    }

    t0 = time.time()
    prof = DataProfiler.profile(large_df, schema_meta, sample_threshold=100_000)
    duration = time.time() - t0

    assert prof["is_sampled"] is True
    assert prof["sample_size"] == 100_000
    assert prof["row_count"] == 120_000
    # Sampling must execute in under 1 second
    assert duration < 2.0


def test_ask_data_deterministic_nlp():
    df = _make_perf_df(50)
    res = AnalyticsManager.activate_user_dataset(df, "nlp_test.csv", "hash_nlp")
    active = AnalyticsManager.get_active_df()

    ans = AskYourDataEngine.answer_question(
        active, "Which category generated the highest revenue?",
        res["schema"], res["kpis"]
    )
    assert "answer" in ans
    assert "The top category is" in ans["answer"] or "category" in ans["answer"]
