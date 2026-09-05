"""
AUREVIX — Universal Data Cleaning & Preparation Engine
Provides atomic, pure, non-destructive cleaning transformations, smart recommendations,
and reproducible recipe execution.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import datetime
import pandas as pd
import numpy as np


class DataCleaningEngine:
    """Enterprise-grade data cleaning and transformation engine."""

    DEFAULT_SENTINELS = [
        "N/A", "NA", "null", "NULL", "None", "NONE", "-", "--", "?", "???",
        "#N/A", "#VALUE!", "nan", "NAN", "nil", "NIL", "empty", "EMPTY"
    ]

    # ----------------------------------------------------------------------
    # 1. Missing Value Handlers
    # ----------------------------------------------------------------------
    @classmethod
    def drop_missing(
        cls,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        how: str = "any",
        thresh: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Drop rows with missing values in specified columns or all columns."""
        df_out = df.copy()
        rows_before = len(df_out)
        
        subset = [c for c in columns if c in df_out.columns] if columns else None
        
        if thresh is not None:
            df_out = df_out.dropna(thresh=thresh, subset=subset)
        else:
            df_out = df_out.dropna(how=how, subset=subset)
            
        rows_after = len(df_out)
        rows_removed = rows_before - rows_after
        
        stats = {
            "operation": "drop_missing",
            "columns": subset or "all",
            "how": how,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_removed,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    @classmethod
    def impute_missing(
        cls,
        df: pd.DataFrame,
        column: str,
        strategy: str = "median",
        constant_value: Any = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Impute missing values using statistical or heuristic strategies."""
        df_out = df.copy()
        if column not in df_out.columns:
            return df_out, {"operation": "impute_missing", "error": f"Column {column} not found"}

        s = df_out[column]
        null_count = int(s.isnull().sum())
        fill_val = None

        if null_count == 0:
            return df_out, {
                "operation": "impute_missing",
                "column": column,
                "strategy": strategy,
                "imputed_count": 0,
                "fill_value": None,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        strategy_lower = strategy.lower().strip()

        if strategy_lower in ("mean", "average"):
            numeric_s = pd.to_numeric(s, errors="coerce")
            fill_val = float(numeric_s.mean())
            df_out[column] = s.fillna(fill_val)

        elif strategy_lower == "median":
            numeric_s = pd.to_numeric(s, errors="coerce")
            fill_val = float(numeric_s.median())
            df_out[column] = s.fillna(fill_val)

        elif strategy_lower == "mode":
            mode_vals = s.dropna().mode()
            if not mode_vals.empty:
                fill_val = mode_vals.iloc[0]
                df_out[column] = s.fillna(fill_val)
            else:
                fill_val = "Unknown"
                df_out[column] = s.fillna(fill_val)

        elif strategy_lower in ("zero", "0"):
            fill_val = 0
            df_out[column] = s.fillna(0)

        elif strategy_lower == "constant":
            fill_val = constant_value if constant_value is not None else "Unknown"
            df_out[column] = s.fillna(fill_val)

        elif strategy_lower in ("ffill", "forward_fill"):
            df_out[column] = s.ffill()
            fill_val = "forward_fill"

        elif strategy_lower in ("bfill", "backward_fill"):
            df_out[column] = s.bfill()
            fill_val = "backward_fill"

        else:
            fill_val = "Unknown"
            df_out[column] = s.fillna(fill_val)

        stats = {
            "operation": "impute_missing",
            "column": column,
            "strategy": strategy,
            "imputed_count": null_count,
            "fill_value": str(fill_val),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    # ----------------------------------------------------------------------
    # 2. Duplicate Removal Handlers
    # ----------------------------------------------------------------------
    @classmethod
    def remove_duplicates(
        cls,
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = "first"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Remove duplicate rows based on subset or all columns."""
        df_out = df.copy()
        rows_before = len(df_out)
        
        valid_subset = [c for c in subset if c in df_out.columns] if subset else None
        
        df_out = df_out.drop_duplicates(subset=valid_subset, keep=keep)
        rows_after = len(df_out)
        duplicates_removed = rows_before - rows_after

        stats = {
            "operation": "remove_duplicates",
            "subset": valid_subset or "all_columns",
            "keep": keep,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "duplicates_removed": duplicates_removed,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    # ----------------------------------------------------------------------
    # 3. Outlier Handlers
    # ----------------------------------------------------------------------
    @classmethod
    def handle_outliers(
        cls,
        df: pd.DataFrame,
        column: str,
        method: str = "iqr",
        action: str = "clip",
        factor: float = 1.5
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Clip or remove statistical outliers in numeric columns."""
        df_out = df.copy()
        if column not in df_out.columns:
            return df_out, {"operation": "handle_outliers", "error": f"Column {column} not found"}

        s_num = pd.to_numeric(df_out[column], errors="coerce")
        valid_s = s_num.dropna()
        if len(valid_s) < 5:
            return df_out, {
                "operation": "handle_outliers",
                "column": column,
                "outliers_affected": 0,
                "reason": "Insufficient numeric values"
            }

        if method.lower() == "zscore":
            mean_val = float(valid_s.mean())
            std_val = float(valid_s.std())
            if std_val == 0:
                return df_out, {"operation": "handle_outliers", "column": column, "outliers_affected": 0}
            lower_bound = mean_val - (factor * std_val)
            upper_bound = mean_val + (factor * std_val)
        else:  # IQR method default
            q25, q75 = np.percentile(valid_s, [25, 75])
            iqr = q75 - q25
            lower_bound = float(q25 - (factor * iqr))
            upper_bound = float(q75 + (factor * iqr))

        outlier_mask = (s_num < lower_bound) | (s_num > upper_bound)
        outliers_count = int(outlier_mask.sum())

        rows_before = len(df_out)
        if action.lower() == "drop":
            df_out = df_out[~outlier_mask]
            rows_after = len(df_out)
        else:  # Clip / Winsorize
            df_out[column] = s_num.clip(lower=lower_bound, upper=upper_bound)
            rows_after = len(df_out)

        stats = {
            "operation": "handle_outliers",
            "column": column,
            "method": method,
            "action": action,
            "factor": factor,
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
            "outliers_affected": outliers_count,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    # ----------------------------------------------------------------------
    # 4. Text & Whitespace Formatters
    # ----------------------------------------------------------------------
    @classmethod
    def strip_whitespace(
        cls,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Strip leading and trailing whitespace from string columns."""
        df_out = df.copy()
        target_cols = columns if columns else [
            c for c in df_out.columns if df_out[c].dtype == object or pd.api.types.is_string_dtype(df_out[c])
        ]
        
        modified_cols = []
        cells_trimmed = 0

        for c in target_cols:
            if c in df_out.columns:
                orig = df_out[c].astype(str)
                trimmed = orig.str.strip()
                diff_mask = df_out[c].notnull() & (orig != trimmed)
                count = int(diff_mask.sum())
                if count > 0:
                    cells_trimmed += count
                    modified_cols.append(c)
                # Keep NaNs intact
                df_out[c] = df_out[c].apply(lambda x: x.strip() if isinstance(x, str) else x)

        stats = {
            "operation": "strip_whitespace",
            "columns_modified": modified_cols,
            "cells_trimmed": cells_trimmed,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    @classmethod
    def change_case(
        cls,
        df: pd.DataFrame,
        column: str,
        case_type: str = "title"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Convert string casing in a column."""
        df_out = df.copy()
        if column not in df_out.columns:
            return df_out, {"operation": "change_case", "error": f"Column {column} not found"}

        case_type = case_type.lower().strip()
        if case_type == "upper":
            df_out[column] = df_out[column].apply(lambda x: str(x).upper() if pd.notnull(x) else x)
        elif case_type == "lower":
            df_out[column] = df_out[column].apply(lambda x: str(x).lower() if pd.notnull(x) else x)
        elif case_type == "title":
            df_out[column] = df_out[column].apply(lambda x: str(x).title() if pd.notnull(x) else x)
        elif case_type == "capitalize":
            df_out[column] = df_out[column].apply(lambda x: str(x).capitalize() if pd.notnull(x) else x)

        stats = {
            "operation": "change_case",
            "column": column,
            "case_type": case_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    # ----------------------------------------------------------------------
    # 5. Type Coercion & Sentinel Handlers
    # ----------------------------------------------------------------------
    @classmethod
    def replace_sentinels(
        cls,
        df: pd.DataFrame,
        sentinels: Optional[List[str]] = None,
        columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Replace custom sentinel strings (e.g. 'N/A', '-', '?') with NaN."""
        df_out = df.copy()
        sentinel_list = sentinels if sentinels is not None else cls.DEFAULT_SENTINELS
        target_cols = columns if columns else list(df_out.columns)

        replaced_count = 0
        affected_cols = []

        for c in target_cols:
            if c in df_out.columns:
                mask = df_out[c].astype(str).str.strip().isin(sentinel_list)
                cnt = int(mask.sum())
                if cnt > 0:
                    replaced_count += cnt
                    affected_cols.append(c)
                    df_out.loc[mask, c] = np.nan

        stats = {
            "operation": "replace_sentinels",
            "sentinels": sentinel_list,
            "replaced_count": replaced_count,
            "affected_columns": affected_cols,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    @classmethod
    def coerce_data_type(
        cls,
        df: pd.DataFrame,
        column: str,
        target_type: str,
        date_format: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Coerce column data type safely."""
        df_out = df.copy()
        if column not in df_out.columns:
            return df_out, {"operation": "coerce_data_type", "error": f"Column {column} not found"}

        orig_type = str(df_out[column].dtype)
        target_type = target_type.lower().strip()

        if target_type in ("numeric", "float", "number"):
            df_out[column] = pd.to_numeric(df_out[column], errors="coerce")
        elif target_type in ("int", "integer"):
            s_num = pd.to_numeric(df_out[column], errors="coerce")
            df_out[column] = s_num.round().astype("Int64")  # Nullable integer
        elif target_type in ("datetime", "date"):
            if date_format:
                df_out[column] = pd.to_datetime(df_out[column], format=date_format, errors="coerce")
            else:
                df_out[column] = pd.to_datetime(df_out[column], errors="coerce")
        elif target_type in ("string", "text"):
            df_out[column] = df_out[column].astype(str).replace("nan", np.nan).replace("None", np.nan)
        elif target_type in ("bool", "boolean"):
            bool_map = {"true": True, "1": True, "yes": True, "y": True, "t": True,
                        "false": False, "0": False, "no": False, "n": False, "f": False}
            df_out[column] = df_out[column].astype(str).str.lower().map(bool_map)

        stats = {
            "operation": "coerce_data_type",
            "column": column,
            "original_type": orig_type,
            "target_type": target_type,
            "new_type": str(df_out[column].dtype),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    @classmethod
    def drop_columns(
        cls,
        df: pd.DataFrame,
        columns: List[str]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Drop specific columns from DataFrame."""
        df_out = df.copy()
        valid_cols = [c for c in columns if c in df_out.columns]
        df_out = df_out.drop(columns=valid_cols, errors="ignore")

        stats = {
            "operation": "drop_columns",
            "dropped_columns": valid_cols,
            "remaining_columns": list(df_out.columns),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return df_out, stats

    # ----------------------------------------------------------------------
    # 6. Smart Recommendations Generator
    # ----------------------------------------------------------------------
    @classmethod
    def generate_smart_cleaning_recommendations(
        cls,
        df: pd.DataFrame,
        profile: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate high-impact, actionable cleaning recommendations based on profile."""
        recs = []

        # 1. Whitespace in text columns
        text_cols = [c for c in df.columns if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]
        cols_with_trailing_spaces = []
        for c in text_cols:
            s_str = df[c].dropna().astype(str)
            if (s_str.str.strip() != s_str).any():
                cols_with_trailing_spaces.append(c)

        if cols_with_trailing_spaces:
            recs.append({
                "id": "rec_whitespace",
                "title": f"Trim whitespace in {len(cols_with_trailing_spaces)} text column(s)",
                "description": f"Columns ({', '.join(cols_with_trailing_spaces[:3])}) contain leading/trailing whitespaces.",
                "category": "Format",
                "impact": "Formatting",
                "action": "strip_whitespace",
                "params": {"columns": cols_with_trailing_spaces}
            })

        # 2. Sentinel strings detected
        sentinel_found_cols = []
        for c in text_cols:
            if df[c].astype(str).str.strip().isin(cls.DEFAULT_SENTINELS).any():
                sentinel_found_cols.append(c)

        if sentinel_found_cols:
            recs.append({
                "id": "rec_sentinels",
                "title": f"Replace placeholder strings (e.g. 'N/A', '-') with NaN",
                "description": f"Detected placeholder sentinel values in {len(sentinel_found_cols)} column(s).",
                "category": "Data Quality",
                "impact": "Validity",
                "action": "replace_sentinels",
                "params": {"columns": sentinel_found_cols}
            })

        # 3. Duplicate rows
        dup_count = profile.get("duplicate_rows", 0)
        if dup_count > 0:
            recs.append({
                "id": "rec_duplicates",
                "title": f"Remove {dup_count:,} duplicate rows",
                "description": f"Deduplicate dataset (keeping first occurrence) to boost uniqueness score.",
                "category": "Deduplication",
                "impact": "Uniqueness",
                "action": "remove_duplicates",
                "params": {"keep": "first"}
            })

        # 4. Constant columns
        const_cols = profile.get("constant_columns", [])
        if const_cols:
            recs.append({
                "id": "rec_constant_cols",
                "title": f"Drop {len(const_cols)} zero-variance constant column(s)",
                "description": f"Columns ({', '.join(const_cols)}) contain only one unique value.",
                "category": "Dimensionality",
                "impact": "Consistency",
                "action": "drop_columns",
                "params": {"columns": const_cols}
            })

        # 5. Missing values in numeric/categorical columns
        col_profiles = profile.get("column_profiles", {})
        for col, meta in col_profiles.items():
            null_count = meta.get("null_count", 0)
            null_pct = meta.get("null_pct", 0.0)
            if 0 < null_pct <= 40.0 and col in schema.get("numeric_columns", []):
                recs.append({
                    "id": f"rec_impute_{col}",
                    "title": f"Impute {null_count} missing values in '{col}'",
                    "description": f"Fill {null_pct}% missing numeric values using column median.",
                    "category": "Imputation",
                    "impact": "Completeness",
                    "action": "impute_missing",
                    "params": {"column": col, "strategy": "median"}
                })
            elif 0 < null_pct <= 40.0 and col in schema.get("categorical_columns", []):
                recs.append({
                    "id": f"rec_impute_{col}",
                    "title": f"Fill {null_count} missing categories in '{col}'",
                    "description": f"Fill {null_pct}% missing categorical values with most frequent value (Mode).",
                    "category": "Imputation",
                    "impact": "Completeness",
                    "action": "impute_missing",
                    "params": {"column": col, "strategy": "mode"}
                })

        # 6. Outliers in numeric columns
        outliers = profile.get("outliers", {})
        for col, o_info in outliers.items():
            if o_info.get("count", 0) > 0:
                recs.append({
                    "id": f"rec_outliers_{col}",
                    "title": f"Clip {o_info['count']} IQR outliers in '{col}'",
                    "description": f"Winsorize extreme values beyond [{o_info.get('lower_bound', 0):.2f}, {o_info.get('upper_bound', 0):.2f}] bounds.",
                    "category": "Outliers",
                    "impact": "Consistency",
                    "action": "handle_outliers",
                    "params": {"column": col, "method": "iqr", "action": "clip", "factor": 1.5}
                })

        return recs

    # ----------------------------------------------------------------------
    # 7. Batch Recipe Execution
    # ----------------------------------------------------------------------
    @classmethod
    def apply_cleaning_recipe(
        cls,
        df: pd.DataFrame,
        recipe: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Apply a sequence of cleaning operations in order."""
        current_df = df.copy()
        history = []

        for step in recipe:
            action = step.get("action")
            params = step.get("params", {})
            try:
                if action == "drop_missing":
                    current_df, stats = cls.drop_missing(current_df, **params)
                elif action == "impute_missing":
                    current_df, stats = cls.impute_missing(current_df, **params)
                elif action == "remove_duplicates":
                    current_df, stats = cls.remove_duplicates(current_df, **params)
                elif action == "handle_outliers":
                    current_df, stats = cls.handle_outliers(current_df, **params)
                elif action == "strip_whitespace":
                    current_df, stats = cls.strip_whitespace(current_df, **params)
                elif action == "change_case":
                    current_df, stats = cls.change_case(current_df, **params)
                elif action == "replace_sentinels":
                    current_df, stats = cls.replace_sentinels(current_df, **params)
                elif action == "coerce_data_type":
                    current_df, stats = cls.coerce_data_type(current_df, **params)
                elif action == "drop_columns":
                    current_df, stats = cls.drop_columns(current_df, **params)
                else:
                    stats = {"action": action, "error": "Unknown operation"}
                history.append(stats)
            except Exception as e:
                history.append({"action": action, "error": str(e)})

        return current_df, history
