"""
AUREVIX — KPI Explainability & "Why?" Driver Decomposition Engine
Generates transparent calculation formulas, source field mappings, and root-cause driver analysis for metric changes.
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


class KPIExplainer:
    """Generates calculation metadata, explainability details, and 'Why?' driver variance decomposition."""

    @classmethod
    def explain_kpi(
        cls,
        kpi_name: str,
        source_col: Optional[str],
        formula: str,
        row_count: int,
        active_filters: Dict[str, Any]
    ) -> Dict[str, str]:
        filter_str = ", ".join([f"{k} = {v}" for k, v in active_filters.items() if v]) or "None (Full Dataset)"
        return {
            "kpi_name": kpi_name,
            "source_column": source_col or "Derived Field",
            "formula": formula,
            "rows_included": f"{row_count:,}",
            "active_filters": filter_str,
            "explanation": f"Calculated as `{formula}` from source column `{source_col or 'N/A'}` across {row_count:,} active records ({filter_str})."
        }

    @classmethod
    def explain_why_variance(
        cls,
        df: pd.DataFrame,
        metric_col: str,
        date_col: Optional[str] = None,
        category_col: Optional[str] = None,
        region_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """Performs analytical driver decomposition to explain why a metric increased, decreased, or concentrated."""
        if df.empty or metric_col not in df.columns:
            return {"available": False, "reason": "Insufficient metric data for Why Analysis."}

        reasons: List[Dict[str, Any]] = []
        tot_val = float(pd.to_numeric(df[metric_col], errors="coerce").fillna(0.0).sum())

        # 1. Period Movement Drivers (if date exists)
        if date_col and date_col in df.columns:
            try:
                dt_s = pd.to_datetime(df[date_col], errors="coerce")
                val_s = pd.to_numeric(df[metric_col], errors="coerce").fillna(0.0)
                work = pd.DataFrame({"_dt": dt_s, "_val": val_s}).dropna(subset=["_dt"]).sort_values("_dt")
                half = len(work) // 2
                if half >= 3:
                    p1_tot = float(work.iloc[:half]["_val"].sum())
                    p2_tot = float(work.iloc[half:]["_val"].sum())
                    diff = p2_tot - p1_tot
                    pct = ((diff / p1_tot) * 100.0) if p1_tot > 0 else 0.0
                    dir_str = "increased" if diff >= 0 else "decreased"
                    reasons.append({
                        "driver": f"Period Shift ({metric_col})",
                        "impact": f"Total {metric_col} {dir_str} by <b>{abs(pct):.1f}%</b> (${abs(diff):,.2f}) between historical halves.",
                        "type": "positive" if diff >= 0 else "negative"
                    })
            except Exception:
                pass

        # 2. Segment Contribution Drivers
        if category_col and category_col in df.columns:
            try:
                cat_grp = df.groupby(category_col)[metric_col].sum().sort_values(ascending=False)
                if not cat_grp.empty and tot_val > 0:
                    top_cat = str(cat_grp.index[0])
                    top_share = (cat_grp.iloc[0] / tot_val) * 100.0
                    reasons.append({
                        "driver": f"Segment Dominance ({category_col})",
                        "impact": f"<b>{top_cat}</b> is the primary driver generating <b>${cat_grp.iloc[0]:,.2f}</b> ({top_share:.1f}% of total).",
                        "type": "info"
                    })
            except Exception:
                pass

        # 3. Regional Contribution Drivers
        if region_col and region_col in df.columns and region_col != category_col:
            try:
                reg_grp = df.groupby(region_col)[metric_col].sum().sort_values(ascending=False)
                if not reg_grp.empty and tot_val > 0:
                    top_reg = str(reg_grp.index[0])
                    reg_share = (reg_grp.iloc[0] / tot_val) * 100.0
                    reasons.append({
                        "driver": f"Geographic Hub ({region_col})",
                        "impact": f"<b>{top_reg}</b> concentrated <b>${reg_grp.iloc[0]:,.2f}</b> ({reg_share:.1f}% of regional volume).",
                        "type": "info"
                    })
            except Exception:
                pass

        return {
            "available": len(reasons) > 0,
            "metric": metric_col,
            "total_value": tot_val,
            "drivers": reasons
        }
