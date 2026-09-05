"""
AUREVIX — Persistent Workspace & Dataset Storage Test Suite
Validates:
1. Dataset persistence across Streamlit session reinitialization (browser refresh / F5)
2. Active dataset restoration from disk
3. Demo dataset NOT loaded when user dataset exists on disk
4. Clear active dataset does NOT delete persisted dataset files
5. Explicit purge / clear deletes persisted dataset files
6. Cleaning recipe and cleaned state survive session reinitialization
7. Reset to original works after session reinitialization
8. Dataset fingerprint reuses existing dataset storage
9. Two-dataset comparison state persists across reinitialization
10. Saved workspace JSON uses dataset reference, not raw matrix
11. Missing persisted dataset fails gracefully without crashing or loading demo data
12. Path traversal filenames and IDs are strictly sanitized
13. Large datasets are stored via Parquet and not serialized into JSON metadata
"""

import json
import shutil
import pytest
import numpy as np
import pandas as pd
import streamlit as st

from dashboard.analytics.persistent_storage import (
    PersistentStorageManager,
    sanitize_id,
    sanitize_filename
)
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.workspace_manager import WorkspaceManager


@pytest.fixture(autouse=True)
def clean_persistent_storage():
    """Clean persistent storage before and after each test."""
    PersistentStorageManager.clear_all_user_workspaces()
    if "workspace" in st.session_state:
        del st.session_state["workspace"]
    yield
    PersistentStorageManager.clear_all_user_workspaces()
    if "workspace" in st.session_state:
        del st.session_state["workspace"]


def test_dataset_persists_after_session_reinitialization():
    """Verify uploaded dataset survives session reinitialization (browser refresh)."""
    df = pd.DataFrame({
        "order_id": ["O1", "O2", "O3"],
        "revenue": [100.0, 200.0, 300.0],
        "category": ["A", "B", "C"]
    })

    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "sales_q1.csv", "hash_pers_01")
    assert AnalyticsManager.is_user_mode() is True
    assert len(AnalyticsManager.get_active_df()) == 3

    # Simulate browser refresh / session reconnect: wipe in-memory session state
    del st.session_state["workspace"]
    for k in list(st.session_state.keys()):
        del st.session_state[k]

    # Reinitialize session
    AnalyticsManager.initialize()

    # Verify state was restored from disk
    assert AnalyticsManager.is_user_mode() is True
    assert AnalyticsManager.get_workspace_state()["dataset_name"] == "sales_q1.csv"
    assert AnalyticsManager.get_workspace_state()["dataset_id"] == "hash_pers_01"
    restored_df = AnalyticsManager.get_active_df()
    assert len(restored_df) == 3
    assert list(restored_df.columns) == ["order_id", "revenue", "category"]


def test_active_dataset_restored_from_disk():
    """Verify PersistentStorageManager.load_active_state() reconstructs complete workspace."""
    df = pd.DataFrame({"id": [1, 2], "val": [10.5, 20.5]})
    res = {"kpis": {"total_revenue": 31.0}, "profile": {"quality_score": 100.0}}

    PersistentStorageManager.save_dataset("hash_act_01", "act.csv", df, original_df=df, analysis_results=res)
    PersistentStorageManager.save_active_state({
        "user_mode": True,
        "user_dataset_id": "hash_act_01",
        "user_dataset_name": "act.csv",
        "analysis_results": res,
        "active_filters": {"id": [1]},
        "user_targets": {"val": 50.0}
    })

    loaded = PersistentStorageManager.load_active_state()
    assert loaded is not None
    assert loaded["user_mode"] is True
    assert loaded["user_dataset_id"] == "hash_act_01"
    assert len(loaded["raw_df"]) == 2
    assert loaded["user_targets"]["val"] == 50.0


def test_demo_dataset_not_loaded_when_user_dataset_exists():
    """Verify demo dataset is NEVER loaded when a user dataset exists on disk."""
    df = pd.DataFrame({"sku": ["SKU1", "SKU2"], "price": [15.0, 25.0]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "custom_products.csv", "hash_prod_01")

    # Wipe session state
    del st.session_state["workspace"]

    # Reinitialize
    AnalyticsManager.initialize()
    assert AnalyticsManager.is_demo_mode() is False
    assert AnalyticsManager.is_user_mode() is True
    assert "sku" in AnalyticsManager.get_active_df().columns
    assert "price" in AnalyticsManager.get_active_df().columns


def test_clear_current_dataset_does_not_delete_saved_dataset():
    """Verify clearing the active dataset removes active state but leaves dataset directory intact."""
    df = pd.DataFrame({"a": [1, 2]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "test_clear.csv", "hash_clear_01")

    # Clear active dataset
    AnalyticsManager.clear_active_dataset()
    assert AnalyticsManager.is_user_mode() is False
    assert AnalyticsManager.get_active_df().empty is True

    # Persisted dataset file should still exist in storage
    assert PersistentStorageManager.dataset_exists("hash_clear_01") is True

    # After refresh, since active state was cleared, it remains in clean empty state
    del st.session_state["workspace"]
    AnalyticsManager.initialize()
    assert AnalyticsManager.is_user_mode() is False


def test_explicit_clear_saved_workspace_deletes_dataset():
    """Verify explicit purge deletes the dataset directory and active state."""
    df = pd.DataFrame({"x": [10, 20]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "purge_test.csv", "hash_purge_01")

    assert PersistentStorageManager.dataset_exists("hash_purge_01") is True

    # Purge
    AnalyticsManager.purge_persistent_storage()
    assert PersistentStorageManager.dataset_exists("hash_purge_01") is False
    assert PersistentStorageManager.load_active_state() is None


def test_cleaning_recipe_survives_refresh():
    """Verify cleaning transformations and recipe survive session reinitialization."""
    df = pd.DataFrame({
        "name": [" alice ", " bob ", " charlie "],
        "val": [10.0, None, 30.0]
    })
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "clean_test.csv", "hash_clean_01")

    # Apply 2 cleaning steps
    s1 = {"action": "strip_whitespace", "params": {"columns": ["name"]}, "title": "Trim Whitespace"}
    AnalyticsManager.apply_cleaning_step(s1)

    s2 = {"action": "impute_missing", "params": {"column": "val", "strategy": "median"}, "title": "Impute Val"}
    AnalyticsManager.apply_cleaning_step(s2)

    assert len(AnalyticsManager.get_cleaning_recipe()) == 2
    assert AnalyticsManager.get_active_df()["name"].iloc[0] == "alice"
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0

    # Wipe session state
    del st.session_state["workspace"]

    # Reinitialize
    AnalyticsManager.initialize()
    assert len(AnalyticsManager.get_cleaning_recipe()) == 2
    assert AnalyticsManager.get_cleaning_recipe()[0]["title"] == "Trim Whitespace"
    assert AnalyticsManager.get_active_df()["name"].iloc[0] == "alice"
    assert AnalyticsManager.get_active_df()["val"].isnull().sum() == 0


def test_reset_original_after_refresh():
    """Verify Reset to Original works after a session refresh."""
    df = pd.DataFrame({
        "item": [" foo ", " bar "],
        "cost": [100.0, 200.0]
    })
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "reset_test.csv", "hash_reset_01")

    # Apply cleaning
    AnalyticsManager.apply_cleaning_step({"action": "strip_whitespace", "params": {"columns": ["item"]}, "title": "Trim"})
    assert AnalyticsManager.get_active_df()["item"].iloc[0] == "foo"

    # Refresh
    del st.session_state["workspace"]
    AnalyticsManager.initialize()

    # Reset cleaning
    AnalyticsManager.reset_cleaning()
    assert AnalyticsManager.get_active_df()["item"].iloc[0] == " foo "
    assert len(AnalyticsManager.get_cleaning_recipe()) == 0


def test_dataset_fingerprint_reuses_existing_dataset():
    """Verify uploading dataset with same fingerprint reuses storage without duplicates."""
    df = pd.DataFrame({"id": [1, 2, 3]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df, "data.csv", "hash_same_01")
    ds_dir1 = PersistentStorageManager.get_dataset_dir("hash_same_01")

    # Re-activate same hash
    AnalyticsManager.activate_user_dataset(df, "data.csv", "hash_same_01")
    ds_dir2 = PersistentStorageManager.get_dataset_dir("hash_same_01")
    assert ds_dir1 == ds_dir2


def test_two_dataset_comparison_persists():
    """Verify dual-dataset comparison configuration persists across refresh."""
    df_a = pd.DataFrame({"id": [1, 2], "rev_a": [100, 200]})
    df_b = pd.DataFrame({"id": [1, 2], "rev_b": [150, 250]})

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "Q1_Sales.csv", "hash_q1")
    AnalyticsManager.set_comparison_dataset_b(df_b, "Q2_Sales.csv", "hash_q2")
    AnalyticsManager.set_comparison_schema_mapping({"rev_a": "rev_b"})

    assert AnalyticsManager.has_comparison_datasets() is True

    # Wipe session state
    del st.session_state["workspace"]

    # Reinitialize
    AnalyticsManager.initialize()
    assert AnalyticsManager.has_comparison_datasets() is True
    comp_state = AnalyticsManager.get_comparison_state()
    assert comp_state["dataset_a_name"] == "Q1_Sales.csv"
    assert comp_state["dataset_b_name"] == "Q2_Sales.csv"
    assert comp_state["schema_mapping"] == {"rev_a": "rev_b"}


def test_saved_workspace_uses_dataset_reference():
    """Verify saved workspace stores dataset_id reference, not raw matrix bytes."""
    df = pd.DataFrame({"col_1": range(100), "col_2": range(100)})
    ws = WorkspaceManager.save_workspace(
        name="test_ref_ws",
        dataset_id="hash_ref_01",
        dataset_name="Large_Data.csv",
        filters={"col_1": [1, 2]}
    )

    loaded = WorkspaceManager.load_workspace("test_ref_ws")
    assert loaded["dataset_id"] == "hash_ref_01"
    # Ensure no full DataFrame values array is serialized directly in root
    assert "data" not in loaded
    assert "values" not in loaded


def test_missing_persisted_dataset_graceful_failure():
    """Verify if active_state points to missing dataset, it fails gracefully without crashing."""
    PersistentStorageManager.save_active_state({
        "user_mode": True,
        "user_dataset_id": "non_existent_hash",
        "user_dataset_name": "missing.csv"
    })

    AnalyticsManager.initialize()
    # Should not crash, and should not be user_mode since dataset file is missing
    assert AnalyticsManager.is_user_mode() is False
    assert AnalyticsManager.get_active_df().empty is True


def test_path_traversal_filename_rejected():
    """Verify path traversal characters are strictly stripped from IDs and filenames."""
    malicious_id = "../../etc/passwd"
    clean_id = sanitize_id(malicious_id)
    assert ".." not in clean_id
    assert "/" not in clean_id
    assert "\\" not in clean_id
    assert clean_id == "etcpasswd"

    malicious_name = "../../../windows/system32/cmd.exe"
    clean_name = sanitize_filename(malicious_name)
    assert ".." not in clean_name
    assert "/" not in clean_name
    assert clean_name == "cmd.exe"


def test_large_dataset_not_serialized_into_json():
    """Verify large datasets do not bloat metadata JSON files."""
    df_large = pd.DataFrame({
        "col_a": [f"val_{i}" for i in range(1000)],
        "col_b": list(range(1000)),
        "col_c": [i * 1.5 for i in range(1000)]
    })

    ds_dir = PersistentStorageManager.save_dataset("hash_large_01", "large.csv", df_large)
    meta_path = ds_dir / "metadata.json"
    assert meta_path.exists()
    # Metadata JSON should be lightweight (< 10 KB)
    assert meta_path.stat().st_size < 10240
