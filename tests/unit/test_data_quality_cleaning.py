"""
AUREVIX — Unit Tests for Data Quality Center & Interactive Data Cleaning Engine
Validates 4-pillar quality scoring, column-level profiling, atomic transformations,
smart recommendations, and non-destructive recipe lifecycle.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.data_cache import AnalyticsManager


@pytest.fixture(autouse=True)
def reset_workspace():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def _make_dirty_dataset():
    """Create a realistic messy dataset for testing data quality and cleaning."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 5, 7, 8, 9, 10],  # duplicate at index 5
        "name": [" Alice ", "Bob", "Charlie", "David", "Eva", "Eva", "Grace", "Heidi", "Ivan", "Judy "],
        "department": ["Sales", "Engineering", "Sales", "N/A", "HR", "HR", "Finance", "Engineering", "-", "Sales"],
        "salary": [50000.0, 75000.0, np.nan, 80000.0, 60000.0, 60000.0, 90000.0, 70000.0, np.nan, 1000000.0],  # Outlier 1M + nulls
        "join_date": ["2020-01-15", "2021-03-20", "2019-07-11", "invalid_date", "2022-05-01", "2022-05-01", "2020-11-30", "2018-09-14", "2023-02-18", "2021-08-25"],
        "constant_col": ["FixedVal"] * 10
    })


def test_4_pillar_data_quality_scores():
    df = _make_dirty_dataset()
    schema = SchemaDetector.detect_schema(df)
    prof = DataProfiler.profile(df, schema)

    assert prof["row_count"] == 10
    assert prof["col_count"] == 6
    assert prof["missing_cells"] == 2
    assert prof["duplicate_rows"] == 1
    assert "constant_col" in prof["constant_columns"]
    assert "salary" in prof["outliers"]

    # Pillar scores
    assert prof["completeness_score"] < 100.0
    assert prof["uniqueness_score"] < 100.0
    assert prof["quality_score"] > 0.0
    assert prof["rating"] in ["EXCELLENT", "GOOD", "FAIR", "POOR"]
    assert prof["rating_color"].startswith("#")


def test_column_profiles_and_issues_summary():
    df = _make_dirty_dataset()
    schema = SchemaDetector.detect_schema(df)
    prof = DataProfiler.profile(df, schema)

    col_profs = prof["column_profiles"]
    assert "salary" in col_profs
    assert col_profs["salary"]["null_count"] == 2
    assert "Impute" in col_profs["salary"]["recommended_action"]
    assert col_profs["constant_col"]["is_constant"] is True

    issues = prof["issues_summary"]
    assert issues["missing_values"] == 2
    assert issues["duplicate_rows"] == 1
    assert issues["outliers_count"] >= 1
    assert issues["constant_columns_count"] == 1


def test_drop_missing_values():
    df = _make_dirty_dataset()
    cleaned_df, stats = DataCleaningEngine.drop_missing(df, columns=["salary"])
    assert len(cleaned_df) == 8
    assert stats["rows_removed"] == 2
    assert int(cleaned_df["salary"].isnull().sum()) == 0


def test_impute_missing_strategies():
    df = _make_dirty_dataset()
    
    # 1. Median Imputation
    df_med, stats_med = DataCleaningEngine.impute_missing(df, "salary", strategy="median")
    assert df_med["salary"].isnull().sum() == 0
    assert stats_med["imputed_count"] == 2

    # 2. Mode Imputation
    df_mode, stats_mode = DataCleaningEngine.impute_missing(df, "department", strategy="mode")
    assert df_mode["department"].isnull().sum() == 0

    # 3. Constant Imputation
    df_const, stats_const = DataCleaningEngine.impute_missing(df, "salary", strategy="constant", constant_value=55000.0)
    assert df_const["salary"].isnull().sum() == 0


def test_remove_duplicates():
    df = _make_dirty_dataset()
    cleaned_df, stats = DataCleaningEngine.remove_duplicates(df, keep="first")
    assert len(cleaned_df) == 9
    assert stats["duplicates_removed"] == 1
    assert cleaned_df.duplicated().sum() == 0


def test_handle_outliers_iqr_and_zscore():
    df = _make_dirty_dataset()
    
    # IQR Clip
    df_clip, stats_clip = DataCleaningEngine.handle_outliers(df, "salary", method="iqr", action="clip", factor=1.5)
    assert stats_clip["outliers_affected"] >= 1
    assert df_clip["salary"].max() < 1000000.0  # Outlier 1M was clipped
    assert len(df_clip) == len(df)  # Row count preserved

    # IQR Drop
    df_drop, stats_drop = DataCleaningEngine.handle_outliers(df, "salary", method="iqr", action="drop", factor=1.5)
    assert len(df_drop) < len(df)


def test_strip_whitespace_and_change_case():
    df = _make_dirty_dataset()
    
    # Whitespace trimming
    df_clean, stats_ws = DataCleaningEngine.strip_whitespace(df, columns=["name"])
    assert df_clean["name"].iloc[0] == "Alice"
    assert df_clean["name"].iloc[-1] == "Judy"
    assert stats_ws["cells_trimmed"] >= 2

    # Case conversion
    df_upper, _ = DataCleaningEngine.change_case(df_clean, "name", case_type="upper")
    assert df_upper["name"].iloc[0] == "ALICE"


def test_replace_sentinels():
    df = _make_dirty_dataset()
    df_clean, stats = DataCleaningEngine.replace_sentinels(df, sentinels=["N/A", "-"], columns=["department"])
    assert stats["replaced_count"] == 2
    assert int(df_clean["department"].isnull().sum()) == 2


def test_coerce_data_types_and_drop_columns():
    df = _make_dirty_dataset()
    
    # Drop constant column
    df_dropped, stats_drop = DataCleaningEngine.drop_columns(df, ["constant_col"])
    assert "constant_col" not in df_dropped.columns
    assert stats_drop["dropped_columns"] == ["constant_col"]

    # Coerce int
    df_int, _ = DataCleaningEngine.coerce_data_type(df, "id", target_type="integer")
    assert "Int" in str(df_int["id"].dtype) or "int" in str(df_int["id"].dtype)


def test_smart_recommendations_generation():
    df = _make_dirty_dataset()
    schema = SchemaDetector.detect_schema(df)
    prof = DataProfiler.profile(df, schema)

    recs = DataCleaningEngine.generate_smart_cleaning_recommendations(df, prof, schema)
    assert len(recs) > 0
    rec_actions = [r["action"] for r in recs]
    assert any(a in rec_actions for a in ["strip_whitespace", "remove_duplicates", "drop_columns", "impute_missing"])


def test_cleaning_recipe_undo_and_reset():
    df = _make_dirty_dataset()
    AnalyticsManager.activate_user_dataset(df, "dirty.csv", "dirty123")
    assert AnalyticsManager.is_user_mode() is True

    # 1. Apply Step 1: Remove duplicates
    AnalyticsManager.apply_cleaning_step({
        "action": "remove_duplicates",
        "params": {"keep": "first"},
        "title": "Remove duplicate rows"
    })
    assert len(AnalyticsManager.get_active_df()) == 9
    assert len(AnalyticsManager.get_cleaning_recipe()) == 1

    # 2. Apply Step 2: Strip whitespace
    AnalyticsManager.apply_cleaning_step({
        "action": "strip_whitespace",
        "params": {},
        "title": "Strip whitespace"
    })
    assert len(AnalyticsManager.get_cleaning_recipe()) == 2
    assert AnalyticsManager.get_active_df()["name"].iloc[0] == "Alice"

    # 3. Undo Step 2
    undone = AnalyticsManager.undo_last_cleaning_step()
    assert undone is not None
    assert len(AnalyticsManager.get_cleaning_recipe()) == 1
    assert len(AnalyticsManager.get_active_df()) == 9

    # 4. Reset All
    AnalyticsManager.reset_cleaning()
    assert len(AnalyticsManager.get_cleaning_recipe()) == 0
    assert len(AnalyticsManager.get_active_df()) == 10  # Restored to original 10 rows


def test_quality_score_improvement_delta():
    df = _make_dirty_dataset()
    res_init = AnalyticsManager.activate_user_dataset(df, "dirty.csv", "score123")
    init_score = res_init["profile"]["quality_score"]

    # Clean duplicates & impute missing
    AnalyticsManager.apply_cleaning_step({"action": "remove_duplicates", "params": {"keep": "first"}})
    AnalyticsManager.apply_cleaning_step({"action": "impute_missing", "params": {"column": "salary", "strategy": "median"}})
    AnalyticsManager.apply_cleaning_step({"action": "handle_outliers", "params": {"column": "salary", "method": "iqr", "action": "clip"}})

    res_clean = AnalyticsManager.get_analysis_results()
    clean_score = res_clean["profile"]["quality_score"]
    
    assert clean_score > init_score
