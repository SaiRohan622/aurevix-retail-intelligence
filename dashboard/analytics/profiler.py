"""
AUREVIX — High-Performance Data Profiler & 4-Pillar Data Quality Engine
Vectorized completeness, validity, uniqueness, consistency, IQR outliers,
column-level quality diagnostics, and smart sampling for large datasets (>100k rows).
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class DataProfiler:
    """High-performance data profiler with vectorized 4-pillar quality calculation and sampling."""

    @classmethod
    def lightweight_profile(cls, df: pd.DataFrame, schema_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Sub-millisecond lightweight profile for immediate UI feedback upon dataset upload."""
        row_count = len(df)
        col_count = len(df.columns)
        if row_count == 0:
            return {
                "row_count": 0, "col_count": 0, "memory_mb": 0.0,
                "missing_cells": 0, "missing_pct": 0.0, "duplicate_rows": 0,
                "duplicate_pct": 0.0, "quality_score": 100.0,
                "completeness_score": 100.0, "validity_score": 100.0,
                "uniqueness_score": 100.0, "consistency_score": 100.0,
                "rating": "EXCELLENT", "rating_color": "#10b981",
                "is_sampled": False, "sample_size": 0
            }

        total_cells = row_count * col_count
        missing_cells = int(df.isnull().sum().sum())
        missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
        memory_mb = round(float(df.memory_usage(deep=True).sum() / (1024 * 1024)), 2)

        completeness = max(0.0, 100.0 - missing_pct)
        return {
            "row_count": row_count,
            "col_count": col_count,
            "memory_mb": memory_mb,
            "missing_cells": missing_cells,
            "missing_pct": round(missing_pct, 2),
            "completeness_score": round(completeness, 2),
            "is_sampled": False,
            "sample_size": row_count
        }

    @classmethod
    def profile(
        cls,
        df: pd.DataFrame,
        schema_meta: Optional[Dict[str, Any]] = None,
        sample_threshold: int = 100_000
    ) -> Dict[str, Any]:
        """Full 4-pillar data quality profiling with vectorized operations and large dataset sampling."""
        if schema_meta is None:
            from dashboard.analytics.schema_detector import SchemaDetector
            schema_meta = SchemaDetector.detect_schema(df) if df is not None and not df.empty else {}
        row_count = len(df)
        col_count = len(df.columns)
        if row_count == 0:
            return {
                "row_count": 0, "col_count": 0, "memory_mb": 0.0,
                "missing_cells": 0, "missing_pct": 0.0, "duplicate_rows": 0,
                "duplicate_pct": 0.0, "quality_score": 100.0,
                "completeness_score": 100.0, "validity_score": 100.0,
                "uniqueness_score": 100.0, "consistency_score": 100.0,
                "outliers": {}, "constant_columns": [], "problematic_indices": [],
                "rating": "EXCELLENT", "rating_color": "#10b981",
                "issues_summary": {
                    "total_issues": 0, "missing_values": 0, "duplicate_rows": 0,
                    "invalid_dates": 0, "outliers_count": 0, "constant_columns_count": 0
                },
                "column_profiles": {},
                "invalid_dates": {},
                "problematic_records": [],
                "is_sampled": False,
                "sample_size": 0
            }

        total_cells = row_count * col_count
        
        # 1. Exact Global Metrics (Computed on full dataset)
        col_null_counts = df.isnull().sum()
        missing_cells = int(col_null_counts.sum())
        missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0

        duplicate_rows = int(df.duplicated().sum())
        duplicate_pct = (duplicate_rows / row_count * 100.0) if row_count > 0 else 0.0

        memory_mb = round(float(df.memory_usage(deep=True).sum() / (1024 * 1024)), 2)
        constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]

        # 2. Intelligent Sampling for Large Datasets (> 100k rows)
        is_sampled = False
        sample_size = row_count
        if row_count > sample_threshold:
            is_sampled = True
            sample_size = sample_threshold
            df_calc = df.sample(n=sample_threshold, random_state=42)
            sampling_multiplier = row_count / sample_threshold
        else:
            df_calc = df
            sampling_multiplier = 1.0

        # 3. Outlier detection on numeric columns (IQR method)
        outliers_info = {}
        total_outlier_count = 0
        total_numeric_values = 0

        numeric_cols = schema_meta.get("numeric_columns", [])
        for num_col in numeric_cols:
            if num_col not in df_calc.columns:
                continue
            s_num = pd.to_numeric(df_calc[num_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            n_vals = len(s_num)
            total_numeric_values += int(n_vals * sampling_multiplier)
            if n_vals >= 8:
                q25, q75 = np.percentile(s_num, [25, 75])
                iqr = q75 - q25
                if iqr > 0:
                    lower_bound = float(q25 - (1.5 * iqr))
                    upper_bound = float(q75 + (1.5 * iqr))
                    outlier_mask = (s_num < lower_bound) | (s_num > upper_bound)
                    sampled_outliers = int(outlier_mask.sum())
                    if sampled_outliers > 0:
                        est_outliers = int(sampled_outliers * sampling_multiplier)
                        total_outlier_count += est_outliers
                        outliers_info[num_col] = {
                            "count": est_outliers,
                            "pct": round((sampled_outliers / n_vals) * 100.0, 2),
                            "lower_bound": round(lower_bound, 4),
                            "upper_bound": round(upper_bound, 4),
                            "sample_values": [float(v) for v in s_num[outlier_mask].head(3).tolist()]
                        }

        # 4. Date validation
        invalid_dates_info = {}
        total_invalid_dates = 0
        date_cols = schema_meta.get("date_columns", [])
        for date_col in date_cols:
            if date_col not in df_calc.columns:
                continue
            s_raw = df_calc[date_col].dropna().astype(str)
            if not s_raw.empty:
                s_parsed = pd.to_datetime(df_calc[date_col], errors="coerce")
                invalid_mask = df_calc[date_col].notnull() & s_parsed.isnull()
                sampled_invalid = int(invalid_mask.sum())
                if sampled_invalid > 0:
                    est_invalid = int(sampled_invalid * sampling_multiplier)
                    total_invalid_dates += est_invalid
                    invalid_dates_info[date_col] = {
                        "count": est_invalid,
                        "pct": round((sampled_invalid / len(s_raw)) * 100.0, 2),
                        "samples": s_raw[invalid_mask].head(3).tolist()
                    }

        # 5. 4 Pillars of Data Quality
        completeness = max(0.0, 100.0 - missing_pct)
        uniqueness = max(0.0, 100.0 - duplicate_pct)

        outlier_rate = (total_outlier_count / max(1, total_numeric_values)) * 100.0
        consistency_pen = (outlier_rate * 1.5) + (len(constant_cols) * 2.0)
        consistency = max(0.0, 100.0 - consistency_pen)

        invalid_date_rate = (total_invalid_dates / max(1, row_count)) * 100.0
        validity_pen = (missing_pct * 0.4) + (invalid_date_rate * 2.0)
        validity = max(0.0, 100.0 - validity_pen)

        quality_score = (completeness * 0.35) + (uniqueness * 0.30) + (validity * 0.20) + (consistency * 0.15)
        quality_score = round(max(0.0, min(100.0, quality_score)), 2)

        if quality_score >= 95.0:
            rating = "EXCELLENT"
            rating_color = "#10b981"
        elif quality_score >= 85.0:
            rating = "GOOD"
            rating_color = "#38bdf8"
        elif quality_score >= 70.0:
            rating = "FAIR"
            rating_color = "#f59e0b"
        else:
            rating = "POOR"
            rating_color = "#ef4444"

        # 6. Column-level quality profiles
        column_profiles = {}
        col_meta_dict = schema_meta.get("columns", {})

        for col in df.columns:
            s = df[col]
            c_nulls = int(col_null_counts.get(col, 0))
            c_null_pct = round((c_nulls / row_count) * 100.0, 2)
            c_unique = int(s.nunique(dropna=True))
            c_unique_pct = round((c_unique / max(1, row_count)) * 100.0, 2)
            c_outliers = outliers_info.get(col, {}).get("count", 0)
            c_invalid_dates = invalid_dates_info.get(col, {}).get("count", 0)
            c_is_const = col in constant_cols

            recommendation = "No issues detected"
            if c_is_const:
                recommendation = "Consider dropping constant column"
            elif c_null_pct > 60.0:
                recommendation = f"High nulls ({c_null_pct}%): consider dropping column"
            elif c_null_pct > 0.0:
                if col in numeric_cols:
                    recommendation = f"Impute {c_nulls} missing values (Median/Mean)"
                else:
                    recommendation = f"Impute {c_nulls} missing values (Mode/Unknown)"
            elif c_invalid_dates > 0:
                recommendation = f"Standardize {c_invalid_dates} invalid date formats"
            elif c_outliers > 0:
                recommendation = f"Review/Clip {c_outliers} IQR outliers"

            column_profiles[col] = {
                "dtype": str(s.dtype),
                "semantic_role": col_meta_dict.get(col, {}).get("semantic_type", "general"),
                "null_count": c_nulls,
                "null_pct": c_null_pct,
                "unique_count": c_unique,
                "unique_pct": c_unique_pct,
                "completeness_score": round(max(0.0, 100.0 - c_null_pct), 2),
                "outlier_count": c_outliers,
                "invalid_date_count": c_invalid_dates,
                "is_constant": c_is_const,
                "recommended_action": recommendation,
                "sample_values": [str(v) for v in s.dropna().head(3).tolist()]
            }

        # 7. Fast Vectorized Problematic Records Drilldown (Top 20)
        has_nulls_mask = df.isnull().any(axis=1)
        has_dups_mask = df.duplicated(keep=False)
        flagged_mask = has_nulls_mask | has_dups_mask
        flagged_df = df[flagged_mask].head(20)

        problematic_records = []
        for idx, row in flagged_df.iterrows():
            reasons = []
            if has_nulls_mask.loc[idx]:
                null_cols_in_row = df.columns[row.isnull()].tolist()
                reasons.append(f"Missing values in: {', '.join(null_cols_in_row[:3])}")
            if has_dups_mask.loc[idx]:
                reasons.append("Duplicate row")
            problematic_records.append({
                "row_index": idx,
                "reason": " | ".join(reasons),
                "data": row.to_dict()
            })

        issues_summary = {
            "total_issues": missing_cells + duplicate_rows + total_invalid_dates + total_outlier_count + len(constant_cols),
            "missing_values": missing_cells,
            "duplicate_rows": duplicate_rows,
            "invalid_dates": total_invalid_dates,
            "outliers_count": total_outlier_count,
            "constant_columns_count": len(constant_cols)
        }

        return {
            "row_count": row_count,
            "col_count": col_count,
            "memory_mb": memory_mb,
            "missing_cells": missing_cells,
            "missing_pct": round(missing_pct, 4),
            "duplicate_rows": duplicate_rows,
            "duplicate_pct": round(duplicate_pct, 4),
            "quality_score": quality_score,
            "completeness_score": round(completeness, 2),
            "validity_score": round(validity, 2),
            "uniqueness_score": round(uniqueness, 2),
            "consistency_score": round(consistency, 2),
            "outliers": outliers_info,
            "constant_columns": constant_cols,
            "problematic_indices": list(flagged_df.index),
            "rating": rating,
            "rating_color": rating_color,
            "issues_summary": issues_summary,
            "column_profiles": column_profiles,
            "invalid_dates": invalid_dates_info,
            "problematic_records": problematic_records,
            "is_sampled": is_sampled,
            "sample_size": sample_size
        }
