"""
AUREVIX — Saved Workspace JSON Serialization & Lifecycle Test Suite
Validates:
1. Saving normal workspace configurations
2. Saving workspace containing NumPy integer, float, boolean scalars and ndarrays
3. Saving workspace containing Pandas Timestamps, Series, Index, pd.NA, and pd.NaT
4. Safe handling and null-conversion of NaN, Infinity, -Infinity
5. Recursive serialization of nested dictionaries, lists, tuples, and sets
6. Safe summarization when a DataFrame is passed (no raw matrix dump)
7. Workspace restoration into session state without modifying active DataFrame or falling back to Olist
8. Multiple saved workspaces listing and deletion
9. Saving workspace while user dataset is active
10. Saving workspace while comparison mode is active
11. Backward compatibility for both workspace_id and snapshot_id keys
"""

import json
import math
import datetime
import pathlib
import pytest
import numpy as np
import pandas as pd

from dashboard.analytics.workspace_manager import WorkspaceManager, _make_json_serializable
from dashboard.analytics.data_cache import AnalyticsManager


@pytest.fixture(autouse=True)
def cleanup_test_workspaces():
    """Ensure clean test storage before and after each test."""
    test_ids = ["test_ws_normal", "test_ws_numpy", "test_ws_pandas", "test_ws_nan_inf",
                "test_ws_nested", "test_ws_df_ref", "test_ws_restore", "test_ws_multi_1",
                "test_ws_multi_2", "test_ws_user_active", "test_ws_comp_active"]
    yield
    for tid in test_ids:
        WorkspaceManager.delete_workspace(tid)


def test_make_json_serializable_scalars_and_collections():
    """Verify recursive serialization of primitives and complex collections."""
    raw_payload = {
        "int_np": np.int64(42),
        "int_py": 100,
        "float_np": np.float64(3.14159),
        "float_py": 2.718,
        "bool_np": np.bool_(True),
        "bool_py": False,
        "nan_np": np.nan,
        "inf_np": np.inf,
        "neg_inf_np": -np.inf,
        "py_nan": float("nan"),
        "py_inf": float("inf"),
        "pd_na": pd.NA,
        "pd_nat": pd.NaT,
        "timestamp": pd.Timestamp("2025-08-30 20:30:00"),
        "date": datetime.date(2025, 8, 30),
        "datetime": datetime.datetime(2025, 8, 30, 20, 30, 0),
        "series": pd.Series([10, 20, np.nan]),
        "index": pd.Index(["alpha", "beta", "gamma"]),
        "ndarray": np.array([[1, 2], [3, 4]]),
        "tuple_data": (np.int32(1), "two", np.float32(3.0)),
        "set_data": {"b", "a", "c"},
        "path": pathlib.Path("data/workspaces/test.json"),
        "nested": {
            "inner_list": [np.int64(99), pd.Timestamp("2025-01-01"), None]
        }
    }

    serialized = _make_json_serializable(raw_payload)

    # Validate output types
    assert isinstance(serialized["int_np"], int)
    assert serialized["int_np"] == 42
    assert isinstance(serialized["float_np"], float)
    assert serialized["nan_np"] is None
    assert serialized["inf_np"] is None
    assert serialized["neg_inf_np"] is None
    assert serialized["py_nan"] is None
    assert serialized["py_inf"] is None
    assert serialized["pd_na"] is None
    assert serialized["pd_nat"] is None
    assert serialized["bool_np"] is True
    assert isinstance(serialized["timestamp"], str)
    assert "2025-08-30" in serialized["timestamp"]
    assert isinstance(serialized["series"], list)
    assert serialized["series"] == [10, 20, None]
    assert isinstance(serialized["index"], list)
    assert serialized["index"] == ["alpha", "beta", "gamma"]
    assert isinstance(serialized["ndarray"], list)
    assert isinstance(serialized["tuple_data"], list)
    assert isinstance(serialized["set_data"], list)
    assert isinstance(serialized["path"], str)

    # Must serialize via json.dumps with allow_nan=False without raising
    json_str = json.dumps(serialized, indent=2, allow_nan=False)
    assert "null" in json_str


def test_save_normal_workspace():
    """Verify saving a standard workspace configuration."""
    ws = WorkspaceManager.save_workspace(
        name="test_ws_normal",
        dataset_id="hash_retail_123",
        dataset_name="Retail_Sales.csv",
        filters={"region": ["North", "South"]},
        targets={"revenue": 500000.0, "transactions": 10000.0},
        dashboard_layout=["kpis", "target", "trend"],
        notes="Standard production baseline workspace"
    )

    assert ws["name"] == "test_ws_normal"
    assert ws["workspace_id"] == "test_ws_normal"
    assert ws["snapshot_id"] == "test_ws_normal"
    assert ws["dataset_id"] == "hash_retail_123"
    assert ws["targets"]["revenue"] == 500000.0

    # Load and verify from disk
    loaded = WorkspaceManager.load_workspace("test_ws_normal")
    assert loaded is not None
    assert loaded["dataset_name"] == "Retail_Sales.csv"
    assert loaded["filters"]["region"] == ["North", "South"]


def test_save_workspace_numpy_types():
    """Verify saving workspace containing NumPy scalar and array types."""
    ws = WorkspaceManager.save_workspace(
        name="test_ws_numpy",
        dataset_id="hash_np_test",
        dataset_name="NumPy_Dataset.csv",
        filters={
            "selected_ids": np.array([101, 102, 103]),
            "threshold": np.float64(99.5),
            "flag": np.bool_(True),
            "count": np.int64(50)
        },
        targets={
            "metric_target": np.float32(125000.75),
            "max_volume": np.int32(5000)
        },
        cleaning_recipe=[
            {"action": "impute_missing", "params": {"fill_val": np.float64(42.0)}}
        ]
    )

    assert ws["workspace_id"] == "test_ws_numpy"
    loaded = WorkspaceManager.load_workspace("test_ws_numpy")
    assert loaded is not None
    assert loaded["filters"]["selected_ids"] == [101, 102, 103]
    assert loaded["filters"]["threshold"] == 99.5
    assert loaded["filters"]["flag"] is True
    assert loaded["targets"]["metric_target"] == pytest.approx(125000.75, rel=1e-3)


def test_save_workspace_pandas_types():
    """Verify saving workspace containing Pandas Timestamps, Series, Index, NA, NaT."""
    ws = WorkspaceManager.save_workspace(
        name="test_ws_pandas",
        dataset_id="hash_pd_test",
        dataset_name="Pandas_Data.csv",
        filters={
            "date_range": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-06-30")],
            "categories": pd.Series(["Electronics", "Clothing"]),
            "index_keys": pd.Index(["k1", "k2"]),
            "missing_na": pd.NA,
            "missing_nat": pd.NaT
        }
    )

    loaded = WorkspaceManager.load_workspace("test_ws_pandas")
    assert loaded is not None
    assert "2025-01-01" in loaded["filters"]["date_range"][0]
    assert loaded["filters"]["categories"] == ["Electronics", "Clothing"]
    assert loaded["filters"]["missing_na"] is None
    assert loaded["filters"]["missing_nat"] is None


def test_save_workspace_nan_and_infinity():
    """Verify NaN, Infinity, -Infinity are cleanly converted to null."""
    ws = WorkspaceManager.save_workspace(
        name="test_ws_nan_inf",
        dataset_id="hash_nan",
        dataset_name="NaN_Data.csv",
        filters={
            "upper_bound": np.inf,
            "lower_bound": -np.inf,
            "missing_val": np.nan,
            "py_nan": float("nan")
        },
        targets={
            "growth_target": float("inf")
        }
    )

    loaded = WorkspaceManager.load_workspace("test_ws_nan_inf")
    assert loaded is not None
    assert loaded["filters"]["upper_bound"] is None
    assert loaded["filters"]["lower_bound"] is None
    assert loaded["filters"]["missing_val"] is None
    assert loaded["targets"]["growth_target"] is None


def test_save_workspace_with_dataframe_reference():
    """Verify passing a DataFrame as 2nd argument does not crash and summarizes metadata."""
    df_sample = pd.DataFrame({
        "customer": ["CustA", "CustB", "CustC"],
        "spend": [120.50, 450.00, 890.25],
        "active": [True, True, False]
    })

    ws = WorkspaceManager.save_workspace(
        name="test_ws_df_ref",
        dataset_id=df_sample,  # Passing DataFrame directly
        dataset_name="Customer_Spend.csv",
        filters={"customer": ["CustA", "CustB"]},
        targets={"spend": 10000.0}
    )

    assert ws["workspace_id"] == "test_ws_df_ref"
    assert ws["metadata"]["rows"] == 3
    assert "customer" in ws["metadata"]["columns"]

    loaded = WorkspaceManager.load_workspace("test_ws_df_ref")
    assert loaded is not None
    assert loaded["metadata"]["rows"] == 3


def test_restore_saved_workspace_state():
    """Verify workspace restoration updates targets, layout, and recipe in session state."""
    AnalyticsManager.initialize()
    df_user = pd.DataFrame({"item": ["Item1", "Item2"], "price": [10.0, 20.0]})
    AnalyticsManager.activate_user_dataset(df_user, "Catalog.csv", "hash_catalog")

    # Save a workspace snapshot
    WorkspaceManager.save_workspace(
        name="test_ws_restore",
        dataset_id="hash_catalog",
        dataset_name="Catalog.csv",
        filters={},
        targets={"price": 50.0},
        dashboard_layout=["kpis", "donut"],
        cleaning_recipe=[{"action": "strip_whitespace", "params": {"columns": ["item"]}}]
    )

    # Modify targets in session state
    AnalyticsManager.set_target("price", 100.0)
    assert AnalyticsManager.get_targets().get("price") == 100.0

    # Restore snapshot
    restored = WorkspaceManager.restore_workspace("test_ws_restore")
    assert restored is not None
    assert AnalyticsManager.get_targets().get("price") == 50.0
    assert AnalyticsManager.get_dashboard_layout() == ["kpis", "donut"]

    # Verify active dataset is completely intact and did NOT revert to demo mode
    assert AnalyticsManager.is_user_mode() is True
    assert len(AnalyticsManager.get_active_df()) == 2


def test_multiple_saved_workspaces_and_deletion():
    """Verify multiple snapshots listing, ordering, and deletion."""
    ws1 = WorkspaceManager.save_workspace(name="test_ws_multi_1", dataset_id="h1", dataset_name="D1.csv")
    ws2 = WorkspaceManager.save_workspace(name="test_ws_multi_2", dataset_id="h2", dataset_name="D2.csv")

    all_ws = WorkspaceManager.list_workspaces()
    assert len(all_ws) >= 2
    ws_ids = [w["workspace_id"] for w in all_ws]
    assert "test_ws_multi_1" in ws_ids
    assert "test_ws_multi_2" in ws_ids

    # Delete ws1
    del_ok = WorkspaceManager.delete_workspace("test_ws_multi_1")
    assert del_ok is True
    assert WorkspaceManager.load_workspace("test_ws_multi_1") is None

    # ws2 still exists
    assert WorkspaceManager.load_workspace("test_ws_multi_2") is not None


def test_saving_while_user_dataset_active():
    """Verify saving workspace while user dataset is active does not affect working data."""
    df_live = pd.DataFrame({"col_x": [1, 2, 3], "col_y": ["a", "b", "c"]})
    AnalyticsManager.initialize()
    AnalyticsManager.activate_user_dataset(df_live, "Live_Dataset.csv", "hash_live")

    # Apply a filter
    AnalyticsManager.apply_filters({"col_y": ["a", "b"]})
    assert len(AnalyticsManager.get_active_df()) == 2

    # Save workspace
    ws = WorkspaceManager.save_workspace(
        name="test_ws_user_active",
        dataset_id="hash_live",
        dataset_name="Live_Dataset.csv",
        filters=AnalyticsManager.get_workspace_state()["active_filters"]
    )
    assert ws["workspace_id"] == "test_ws_user_active"

    # Verify active data is unchanged
    assert len(AnalyticsManager.get_active_df()) == 2
    assert AnalyticsManager.is_user_mode() is True


def test_saving_while_comparison_mode_active():
    """Verify saving workspace configuration when comparison datasets are active."""
    df_a = pd.DataFrame({"id": [1, 2], "val": [10.0, 20.0]})
    df_b = pd.DataFrame({"id": [2, 3], "val": [25.0, 35.0]})

    AnalyticsManager.initialize()
    AnalyticsManager.set_comparison_dataset_a(df_a, "CompA.csv", "hash_ca")
    AnalyticsManager.set_comparison_dataset_b(df_b, "CompB.csv", "hash_cb")

    ws = WorkspaceManager.save_workspace(
        name="test_ws_comp_active",
        dataset_id="comp_a_b",
        dataset_name="CompA vs CompB",
        filters={"schema_mapping": {"val": "val"}},
        notes="Dual-dataset comparison snapshot"
    )

    assert ws["workspace_id"] == "test_ws_comp_active"
    assert AnalyticsManager.has_comparison_datasets() is True
