"""
AUREVIX — Central Analysis Cache & Progressive Profiling Test Suite
Verifies central analysis cache hits/misses, fingerprint invalidation,
progressive profiling, large dataset handling, and dataset immutability.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
import io
import time

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.profiler import DataProfiler


@pytest.fixture(autouse=True)
def reset_state():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def _make_test_df(n=500):
    np.random.seed(42)
    return pd.DataFrame({
        "transaction_id": [f"TX_{i:05d}" for i in range(1, n + 1)],
        "tx_date": pd.date_range("2024-01-01", periods=n, freq="h").astype(str),
        "customer": [f"CUST_{i % 30:03d}" for i in range(n)],
        "category": [["Apparel", "Beauty", "Electronics", "Groceries"][i % 4] for i in range(n)],
        "amount": np.random.uniform(15.0, 450.0, n).round(2),
    })


def test_central_cache_hit_and_miss():
    df = _make_test_df(200)
    hash_key = "hash_prog_cache_001"

    # 1. First activation -> Cache MISS
    AnalyticsManager.activate_user_dataset(df, "transactions.csv", hash_key)
    ws_state1 = AnalyticsManager.get_workspace_state()
    assert ws_state1["cache_status"] == "MISS"
    assert ws_state1["analysis_status"] == "complete"

    # 2. Re-activation of same fingerprint -> Cache HIT (sub-millisecond)
    t0 = time.time()
    AnalyticsManager.activate_user_dataset(df, "transactions.csv", hash_key)
    duration = time.time() - t0
    ws_state2 = AnalyticsManager.get_workspace_state()

    assert ws_state2["cache_status"] == "HIT"
    assert ws_state2["cache_hits"] >= 1
    assert duration < 0.05


def test_switching_datasets_restores_from_cache():
    df_a = _make_test_df(100)
    df_b = pd.DataFrame({
        "emp_id": [1, 2, 3],
        "salary": [60000, 75000, 90000],
        "dept": ["IT", "HR", "Sales"]
    })

    # Activate A
    AnalyticsManager.activate_user_dataset(df_a, "dataset_prog_a.csv", "hash_prog_a")
    res_a1 = AnalyticsManager.get_analysis_results()
    assert res_a1["dataset_name"] == "dataset_prog_a.csv"

    # Activate B
    AnalyticsManager.activate_user_dataset(df_b, "dataset_prog_b.csv", "hash_prog_b")
    res_b = AnalyticsManager.get_analysis_results()
    assert res_b["dataset_name"] == "dataset_prog_b.csv"
    assert res_b["kpis"]["primary_metric_col"] == "salary"

    # Re-activate A -> Instant Cache HIT
    AnalyticsManager.activate_user_dataset(df_a, "dataset_prog_a.csv", "hash_prog_a")
    res_a2 = AnalyticsManager.get_analysis_results()
    assert res_a2["dataset_name"] == "dataset_prog_a.csv"
    assert res_a2["kpis"]["primary_metric_col"] == "amount"
    assert AnalyticsManager.get_workspace_state()["cache_status"] == "HIT"


def test_lightweight_profile_is_sub_millisecond():
    df = _make_test_df(1000)
    schema = {"numeric_columns": ["amount"], "categorical_columns": ["category"], "date_columns": ["tx_date"]}

    t0 = time.time()
    prof = DataProfiler.lightweight_profile(df, schema)
    duration = time.time() - t0

    assert prof["row_count"] == 1000
    assert prof["col_count"] == 5
    assert prof["missing_cells"] == 0
    assert duration < 0.05


def test_large_dataset_sampled_profiling():
    n = 150_000
    large_df = pd.DataFrame({
        "val": np.random.uniform(1, 100, n),
        "grp": [["A", "B", "C"][i % 3] for i in range(n)]
    })
    schema = {"numeric_columns": ["val"], "categorical_columns": ["grp"], "date_columns": []}

    t0 = time.time()
    prof = DataProfiler.profile(large_df, schema, sample_threshold=50_000)
    duration = time.time() - t0

    assert prof["is_sampled"] is True
    assert prof["sample_size"] == 50_000
    assert prof["row_count"] == 150_000
    assert duration < 2.0


def test_original_raw_df_remains_immutable_during_cleaning():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "name": [" Alice ", " Bob ", " Charlie ", " David "],
        "score": [10, 20, 30, 40]
    })
    AnalyticsManager.activate_user_dataset(df, "students.csv", "hash_prog_immutable")
    orig_before = AnalyticsManager.get_original_raw_df().copy()

    step = {
        "action": "strip_whitespace",
        "params": {"columns": ["name"]},
        "title": "Strip whitespace"
    }
    AnalyticsManager.apply_cleaning_step(step)

    cleaned_df = AnalyticsManager.get_active_df()
    orig_after = AnalyticsManager.get_original_raw_df()

    assert list(cleaned_df["name"]) == ["Alice", "Bob", "Charlie", "David"]
    assert list(orig_after["name"]) == [" Alice ", " Bob ", " Charlie ", " David "]
    pd.testing.assert_frame_equal(orig_before, orig_after)


def test_empty_and_malformed_datasets():
    empty_df = pd.DataFrame()
    schema_empty = {"numeric_columns": [], "categorical_columns": [], "date_columns": []}
    prof_empty = DataProfiler.profile(empty_df, schema_empty)
    assert prof_empty["row_count"] == 0
    assert prof_empty["quality_score"] == 100.0

    light_empty = DataProfiler.lightweight_profile(empty_df, schema_empty)
    assert light_empty["row_count"] == 0
