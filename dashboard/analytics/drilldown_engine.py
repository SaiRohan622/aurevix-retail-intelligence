"""
AUREVIX — Interactive Multi-Dimensional Hierarchical Drill-Down Engine
Provides multi-level drill-down capabilities across Time, Geography, and Product/Category hierarchies.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class DrillDownEngine:
    """Manages multi-level hierarchical drill-down and roll-up across dimensional axes."""

    @classmethod
    def get_supported_hierarchies(cls, df: pd.DataFrame, schema_meta: Dict[str, Any]) -> Dict[str, List[str]]:
        if df.empty:
            return {}

        roles = schema_meta.get("roles", {})
        cols_lower = {c.lower(): c for c in df.columns}
        hierarchies = {}

        # 1. Time Hierarchy
        date_col = roles.get("date")
        if date_col and date_col in df.columns:
            hierarchies["Time Hierarchy"] = ["Year", "Quarter", "Month", "Day"]

        # 2. Geographic Hierarchy
        geo_levels = []
        for term in ["region", "country", "state", "province", "city"]:
            for cl, orig in cols_lower.items():
                if term in cl and orig not in geo_levels:
                    geo_levels.append(orig)
        if len(geo_levels) >= 2:
            hierarchies["Geographic Hierarchy"] = geo_levels

        # 3. Product / Category Hierarchy
        cat_levels = []
        for term in ["department", "category", "sub_category", "subcategory", "product", "item"]:
            for cl, orig in cols_lower.items():
                if term in cl and orig not in cat_levels:
                    cat_levels.append(orig)
        if len(cat_levels) >= 2:
            hierarchies["Product Hierarchy"] = cat_levels

        return hierarchies

    @classmethod
    def drill_into_time(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        level: str = "Month",
        filter_val: Optional[str] = None
    ) -> Dict[str, Any]:
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return {"data": pd.DataFrame(), "current_level": level}

        df_work = df[[date_col, metric_col]].dropna().copy()
        df_work["_dt"] = pd.to_datetime(df_work[date_col], errors="coerce")
        df_work = df_work.dropna(subset=["_dt"])
        df_work["_val"] = pd.to_numeric(df_work[metric_col], errors="coerce").fillna(0.0)

        if level == "Year":
            df_work["_group"] = df_work["_dt"].dt.year.astype(str)
        elif level == "Quarter":
            if filter_val:
                df_work = df_work[df_work["_dt"].dt.year.astype(str) == str(filter_val)]
            df_work["_group"] = df_work["_dt"].dt.to_period("Q").astype(str)
        elif level == "Month":
            if filter_val:
                df_work = df_work[df_work["_dt"].dt.to_period("Q").astype(str) == str(filter_val)]
            df_work["_group"] = df_work["_dt"].dt.strftime("%Y-%m")
        elif level == "Day":
            if filter_val:
                df_work = df_work[df_work["_dt"].dt.strftime("%Y-%m") == str(filter_val)]
            df_work["_group"] = df_work["_dt"].dt.strftime("%Y-%m-%d")
        else:
            df_work["_group"] = df_work["_dt"].dt.strftime("%Y-%m")

        grp = df_work.groupby("_group")["_val"].agg(["sum", "count", "mean"]).reset_index()
        grp.columns = ["Period", f"Total {metric_col}", "Transactions", f"Average {metric_col}"]
        return {
            "data": grp,
            "current_level": level,
            "record_count": len(df_work),
            "total_metric": float(df_work["_val"].sum())
        }

    @classmethod
    def drill_into_dimension(
        cls,
        df: pd.DataFrame,
        parent_col: str,
        child_col: str,
        parent_val: str,
        metric_col: str
    ) -> Dict[str, Any]:
        if df.empty or parent_col not in df.columns or child_col not in df.columns or metric_col not in df.columns:
            return {"data": pd.DataFrame()}

        df_slice = df[df[parent_col].astype(str) == str(parent_val)].copy()
        df_slice["_val"] = pd.to_numeric(df_slice[metric_col], errors="coerce").fillna(0.0)

        grp = df_slice.groupby(child_col)["_val"].agg(["sum", "count"]).sort_values("sum", ascending=False).reset_index()
        grp.columns = [child_col, f"Total {metric_col}", "Count"]
        tot = df_slice["_val"].sum()
        grp["Share %"] = (grp[f"Total {metric_col}"] / tot * 100.0).round(2) if tot > 0 else 0.0

        return {
            "parent_value": parent_val,
            "child_dimension": child_col,
            "data": grp,
            "total_metric": float(tot),
            "records": len(df_slice)
        }
