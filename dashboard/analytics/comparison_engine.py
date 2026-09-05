"""
AUREVIX — Enterprise Dual-Dataset Comparison Engine
Provides automated schema matching, KPI deltas, record-level diffing, category & trend shifts,
data quality comparisons, and autonomous comparison business insights.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from dashboard.analytics.profiler import DataProfiler


def calc_pct_delta(val_a: float, val_b: float) -> float:
    """Safe percentage change calculation with division-by-zero protection."""
    try:
        val_a = float(val_a)
        val_b = float(val_b)
        if np.isnan(val_a) or np.isnan(val_b):
            return 0.0
        if val_a == 0.0 and val_b == 0.0:
            return 0.0
        if val_a == 0.0:
            return 100.0 if val_b > 0 else -100.0
        return ((val_b - val_a) / abs(val_a)) * 100.0
    except Exception:
        return 0.0


class ComparisonEngine:
    """Enterprise-grade Dual-Dataset Comparison & Analytics Engine."""

    # Semantic column synonyms for smart schema matching
    SYNONYM_GROUPS = [
        {"revenue", "sales", "turnover", "total_amount", "amount", "total_sales", "gross_sales", "income"},
        {"profit", "net_profit", "net_income", "earnings", "margin"},
        {"cost", "cogs", "expenses", "expense", "spend", "spending", "total_cost", "freight_value"},
        {"customer", "customer_id", "cust_id", "client", "client_id", "user_id", "account_id", "customer_name"},
        {"product", "product_name", "product_id", "item", "item_name", "item_id", "sku", "product_title"},
        {"category", "product_category", "product_category_name", "department", "dept", "segment", "division", "group"},
        {"date", "order_date", "purchase_date", "transaction_date", "order_purchase_timestamp", "created_at", "timestamp", "dt"},
        {"quantity", "qty", "units", "count", "volume", "items_count", "order_item_id"},
        {"region", "state", "city", "country", "territory", "location", "area", "customer_state", "customer_city"},
        {"id", "order_id", "transaction_id", "invoice_id", "record_id", "row_id", "emp_id", "employee_id"}
    ]

    @classmethod
    def match_schemas(cls, df_a: pd.DataFrame, df_b: pd.DataFrame) -> Dict[str, Any]:
        """
        Automatically aligns columns between Dataset A and Dataset B using exact match,
        normalized casing, semantic synonyms, and type compatibility.
        """
        if df_a is None or df_b is None or df_a.empty or df_b.empty:
            return {
                "matched": {},
                "match_details": [],
                "unmatched_a": list(df_a.columns) if df_a is not None else [],
                "unmatched_b": list(df_b.columns) if df_b is not None else []
            }

        cols_a = list(df_a.columns)
        cols_b = list(df_b.columns)

        matched: Dict[str, str] = {}
        match_details: List[Dict[str, Any]] = []
        assigned_b = set()

        def norm_name(s: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "", str(s).lower().strip())

        # 1. Exact Match
        for ca in cols_a:
            if ca in cols_b and ca not in assigned_b:
                matched[ca] = ca
                assigned_b.add(ca)
                match_details.append({
                    "col_a": ca,
                    "col_b": ca,
                    "method": "Exact Name",
                    "confidence": 100,
                    "type_a": str(df_a[ca].dtype),
                    "type_b": str(df_b[ca].dtype)
                })

        # 2. Normalized Match (ignoring case, spaces, underscores)
        for ca in cols_a:
            if ca in matched:
                continue
            norm_a = norm_name(ca)
            for cb in cols_b:
                if cb in assigned_b:
                    continue
                if norm_a == norm_name(cb):
                    matched[ca] = cb
                    assigned_b.add(cb)
                    match_details.append({
                        "col_a": ca,
                        "col_b": cb,
                        "method": "Normalized Match",
                        "confidence": 95,
                        "type_a": str(df_a[ca].dtype),
                        "type_b": str(df_b[cb].dtype)
                    })
                    break

        # 3. Semantic Synonym Match
        for ca in cols_a:
            if ca in matched:
                continue
            norm_a = norm_name(ca)
            for group in cls.SYNONYM_GROUPS:
                # Check if ca matches any synonym in this group
                if any(norm_a == norm_name(syn) or norm_name(syn) in norm_a for syn in group):
                    # Look for a candidate in cols_b that belongs to the same group
                    for cb in cols_b:
                        if cb in assigned_b:
                            continue
                        norm_b = norm_name(cb)
                        if any(norm_b == norm_name(syn) or norm_name(syn) in norm_b for syn in group):
                            matched[ca] = cb
                            assigned_b.add(cb)
                            match_details.append({
                                "col_a": ca,
                                "col_b": cb,
                                "method": "Semantic Synonym",
                                "confidence": 85,
                                "type_a": str(df_a[ca].dtype),
                                "type_b": str(df_b[cb].dtype)
                            })
                            break
                    if ca in matched:
                        break

        unmatched_a = [ca for ca in cols_a if ca not in matched]
        unmatched_b = [cb for cb in cols_b if cb not in assigned_b]

        return {
            "matched": matched,
            "match_details": match_details,
            "unmatched_a": unmatched_a,
            "unmatched_b": unmatched_b,
            "match_rate_pct": round(len(matched) / max(1, len(cols_a)) * 100, 1)
        }

    @classmethod
    def compare_datasets(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        name_a: str = "Dataset A",
        name_b: str = "Dataset B",
        schema_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Comprehensive comparison across volume, metrics, schema, and quality."""
        if df_a is None or df_b is None or df_a.empty or df_b.empty:
            return {"available": False, "reason": "Both Dataset A and Dataset B must be loaded and non-empty."}

        mapping_res = cls.match_schemas(df_a, df_b)
        mapping = schema_mapping if schema_mapping is not None else mapping_res["matched"]

        row_diff = len(df_b) - len(df_a)
        row_pct = calc_pct_delta(len(df_a), len(df_b))
        col_diff = len(df_b.columns) - len(df_a.columns)
        col_pct = calc_pct_delta(len(df_a.columns), len(df_b.columns))

        # Memory estimation
        mem_a_mb = round(df_a.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        mem_b_mb = round(df_b.memory_usage(deep=True).sum() / (1024 * 1024), 2)

        # Numeric Columns Comparison
        num_comparisons = {}
        for col_a, col_b in mapping.items():
            if col_a in df_a.columns and col_b in df_b.columns:
                s_a = pd.to_numeric(df_a[col_a], errors="coerce")
                s_b = pd.to_numeric(df_b[col_b], errors="coerce")
                if s_a.notnull().sum() > 0 and s_b.notnull().sum() > 0:
                    sum_a = float(s_a.sum())
                    sum_b = float(s_b.sum())
                    mean_a = float(s_a.mean())
                    mean_b = float(s_b.mean())
                    med_a = float(s_a.median())
                    med_b = float(s_b.median())
                    min_a = float(s_a.min())
                    min_b = float(s_b.min())
                    max_a = float(s_a.max())
                    max_b = float(s_b.max())
                    std_a = float(s_a.std()) if len(s_a.dropna()) > 1 else 0.0
                    std_b = float(s_b.std()) if len(s_b.dropna()) > 1 else 0.0

                    num_comparisons[col_a] = {
                        "col_a": col_a,
                        "col_b": col_b,
                        "sum_a": sum_a,
                        "sum_b": sum_b,
                        "sum_diff": sum_b - sum_a,
                        "sum_pct": calc_pct_delta(sum_a, sum_b),
                        "mean_a": mean_a,
                        "mean_b": mean_b,
                        "mean_diff": mean_b - mean_a,
                        "mean_pct": calc_pct_delta(mean_a, mean_b),
                        "median_a": med_a,
                        "median_b": med_b,
                        "min_a": min_a,
                        "min_b": min_b,
                        "max_a": max_a,
                        "max_b": max_b,
                        "std_a": std_a,
                        "std_b": std_b
                    }

        # Quality Comparison
        quality_comp = cls.calculate_quality_comparison(df_a, df_b, name_a, name_b)

        # Build Overall Insights
        insights = cls.generate_comparison_insights(
            df_a, df_b, name_a, name_b,
            kpi_comp={"row_diff": row_diff, "row_pct": row_pct, "num_metrics": num_comparisons},
            quality_comp=quality_comp
        )

        return {
            "available": True,
            "dataset_a": {
                "name": name_a,
                "rows": len(df_a),
                "columns": len(df_a.columns),
                "column_names": list(df_a.columns),
                "memory_mb": mem_a_mb
            },
            "dataset_b": {
                "name": name_b,
                "rows": len(df_b),
                "columns": len(df_b.columns),
                "column_names": list(df_b.columns),
                "memory_mb": mem_b_mb
            },
            "schema_matching": mapping_res,
            "effective_mapping": mapping,
            "common_columns": list(mapping.keys()),
            "columns_only_in_a": mapping_res["unmatched_a"],
            "columns_only_in_b": mapping_res["unmatched_b"],
            "row_difference": row_diff,
            "row_pct_change": row_pct,
            "column_difference": col_diff,
            "column_pct_change": col_pct,
            "numeric_metrics": num_comparisons,
            "quality_comparison": quality_comp,
            "insights": insights,
            "summary": f"Comparing **{name_a}** ({len(df_a):,} rows) with **{name_b}** ({len(df_b):,} rows) — {len(mapping)} mapped columns, {row_pct:+.1f}% volume shift."
        }

    @classmethod
    def calculate_quality_comparison(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        name_a: str = "Dataset A",
        name_b: str = "Dataset B"
    ) -> Dict[str, Any]:
        """Compares Data Quality 4-pillars and issue summaries between A and B."""
        prof_a = DataProfiler.profile(df_a)
        prof_b = DataProfiler.profile(df_b)

        q_a = float(prof_a.get("quality_score", 100.0))
        q_b = float(prof_b.get("quality_score", 100.0))
        delta_q = q_b - q_a

        comp_a = float(prof_a.get("completeness_score", 100.0))
        comp_b = float(prof_b.get("completeness_score", 100.0))
        val_a = float(prof_a.get("validity_score", 100.0))
        val_b = float(prof_b.get("validity_score", 100.0))
        cons_a = float(prof_a.get("consistency_score", 100.0))
        cons_b = float(prof_b.get("consistency_score", 100.0))
        uniq_a = float(prof_a.get("uniqueness_score", 100.0))
        uniq_b = float(prof_b.get("uniqueness_score", 100.0))

        nulls_a = int(prof_a.get("missing_cells", 0))
        nulls_b = int(prof_b.get("missing_cells", 0))
        dups_a = int(prof_a.get("duplicate_rows", 0))
        dups_b = int(prof_b.get("duplicate_rows", 0))
        out_a = int(prof_a.get("issues_summary", {}).get("outliers_count", 0))
        out_b = int(prof_b.get("issues_summary", {}).get("outliers_count", 0))
        inv_a = int(prof_a.get("issues_summary", {}).get("invalid_dates", 0))
        inv_b = int(prof_b.get("issues_summary", {}).get("invalid_dates", 0))
        const_a = len(prof_a.get("constant_columns", []))
        const_b = len(prof_b.get("constant_columns", []))

        return {
            "score_a": q_a,
            "score_b": q_b,
            "score_delta": delta_q,
            "completeness_a": comp_a,
            "completeness_b": comp_b,
            "completeness_delta": comp_b - comp_a,
            "validity_a": val_a,
            "validity_b": val_b,
            "validity_delta": val_b - val_a,
            "consistency_a": cons_a,
            "consistency_b": cons_b,
            "consistency_delta": cons_b - cons_a,
            "uniqueness_a": uniq_a,
            "uniqueness_b": uniq_b,
            "uniqueness_delta": uniq_b - uniq_a,
            "missing_cells_a": nulls_a,
            "missing_cells_b": nulls_b,
            "missing_delta": nulls_b - nulls_a,
            "duplicate_rows_a": dups_a,
            "duplicate_rows_b": dups_b,
            "duplicate_delta": dups_b - dups_a,
            "outliers_a": out_a,
            "outliers_b": out_b,
            "outliers_delta": out_b - out_a,
            "invalid_dates_a": inv_a,
            "invalid_dates_b": inv_b,
            "invalid_dates_delta": inv_b - inv_a,
            "constant_cols_a": const_a,
            "constant_cols_b": const_b,
            "constant_cols_delta": const_b - const_a
        }

    @classmethod
    def compare_records(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        key_col_a: str,
        key_col_b: str,
        compare_cols: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """Identifies Common, New (in B only), Removed (in A only), and Changed records."""
        if df_a.empty or df_b.empty or key_col_a not in df_a.columns or key_col_b not in df_b.columns:
            return {"available": False, "reason": "Valid key column must be present in both datasets."}

        keys_a = set(df_a[key_col_a].dropna().astype(str))
        keys_b = set(df_b[key_col_b].dropna().astype(str))

        common_keys = keys_a.intersection(keys_b)
        removed_keys = keys_a - keys_b
        new_keys = keys_b - keys_a

        # Extract dataframes
        df_common_a = df_a[df_a[key_col_a].astype(str).isin(common_keys)]
        df_common_b = df_b[df_b[key_col_b].astype(str).isin(common_keys)]
        df_removed = df_a[df_a[key_col_a].astype(str).isin(removed_keys)]
        df_new = df_b[df_b[key_col_b].astype(str).isin(new_keys)]

        # Check for changed records among common keys
        changed_keys = set()
        if compare_cols and common_keys:
            df_ca = df_common_a.drop_duplicates(subset=[key_col_a]).set_index(key_col_a)
            df_cb = df_common_b.drop_duplicates(subset=[key_col_b]).set_index(key_col_b)
            # Normalize index to string
            df_ca.index = df_ca.index.astype(str)
            df_cb.index = df_cb.index.astype(str)
            for k in common_keys:
                if k in df_ca.index and k in df_cb.index:
                    for ca, cb in compare_cols:
                        if ca in df_ca.columns and cb in df_cb.columns:
                            va = str(df_ca.loc[k, ca])
                            vb = str(df_cb.loc[k, cb])
                            if va != vb:
                                changed_keys.add(k)
                                break

        return {
            "available": True,
            "key_a": key_col_a,
            "key_b": key_col_b,
            "total_a": len(df_a),
            "total_b": len(df_b),
            "common_count": len(common_keys),
            "common_pct": round(len(common_keys) / max(1, len(keys_a)) * 100, 1),
            "new_count": len(new_keys),
            "removed_count": len(removed_keys),
            "changed_count": len(changed_keys),
            "df_common": df_common_b.head(100),
            "df_new": df_new.head(100),
            "df_removed": df_removed.head(100)
        }

    @classmethod
    def compare_categories(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        cat_col_a: str,
        cat_col_b: str,
        metric_col_a: Optional[str] = None,
        metric_col_b: Optional[str] = None,
        top_n: int = 8
    ) -> Dict[str, Any]:
        """Compares categorical segment distribution and volume growth between A and B."""
        if df_a.empty or df_b.empty or cat_col_a not in df_a.columns or cat_col_b not in df_b.columns:
            return {"available": False, "reason": "Selected categorical columns must be present."}

        # Calculate counts or metric sums
        if metric_col_a and metric_col_b and metric_col_a in df_a.columns and metric_col_b in df_b.columns:
            grp_a = df_a.groupby(cat_col_a)[metric_col_a].sum().dropna()
            grp_b = df_b.groupby(cat_col_b)[metric_col_b].sum().dropna()
            val_label = "Total Value"
        else:
            grp_a = df_a[cat_col_a].value_counts()
            grp_b = df_b[cat_col_b].value_counts()
            val_label = "Record Count"

        cats_a = set(grp_a.index.astype(str))
        cats_b = set(grp_b.index.astype(str))
        all_cats = list(cats_a.union(cats_b))

        rows = []
        for cat in all_cats:
            va = float(grp_a.get(cat, 0.0))
            vb = float(grp_b.get(cat, 0.0))
            diff = vb - va
            pct = calc_pct_delta(va, vb)
            rows.append({
                "Category": str(cat),
                "Dataset A": va,
                "Dataset B": vb,
                "Absolute Shift": diff,
                "Growth %": pct,
                "Status": "Common" if (cat in cats_a and cat in cats_b) else ("New in B" if cat in cats_b else "Only in A")
            })

        df_cat_comp = pd.DataFrame(rows).sort_values(by="Dataset B", ascending=False)
        top_cats = df_cat_comp.head(top_n)

        # Build Grouped Bar Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top_cats["Category"],
            y=top_cats["Dataset A"],
            name="Dataset A",
            marker_color="#38bdf8"
        ))
        fig.add_trace(go.Bar(
            x=top_cats["Category"],
            y=top_cats["Dataset B"],
            name="Dataset B",
            marker_color="#10b981"
        ))
        fig.update_layout(
            barmode="group",
            title=f"Top Categories Comparison ({val_label})",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.6)",
            font=dict(color="#f8fafc"),
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        return {
            "available": True,
            "data": df_cat_comp,
            "figure": fig,
            "categories_only_in_a": list(cats_a - cats_b),
            "categories_only_in_b": list(cats_b - cats_a),
            "top_growing": df_cat_comp.sort_values(by="Growth %", ascending=False).head(3).to_dict("records")
        }

    @classmethod
    def compare_trends(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        date_col_a: str,
        date_col_b: str,
        metric_col_a: str,
        metric_col_b: str,
        granularity: str = "Month"
    ) -> Dict[str, Any]:
        """Aggregates and overlays temporal trends from both datasets."""
        if df_a.empty or df_b.empty or date_col_a not in df_a.columns or date_col_b not in df_b.columns:
            return {"available": False, "reason": "Date columns missing."}

        try:
            freq_map = {"Day": "D", "Week": "W", "Month": "M", "Quarter": "Q", "Year": "Y"}
            freq = freq_map.get(granularity, "M")

            def prep_ts(df, dcol, mcol):
                w = df[[dcol, mcol]].dropna().copy()
                w["_dt"] = pd.to_datetime(w[dcol], errors="coerce")
                w = w.dropna(subset=["_dt"])
                w["_val"] = pd.to_numeric(w[mcol], errors="coerce").fillna(0.0)
                w["_period"] = w["_dt"].dt.to_period(freq).astype(str)
                ts = w.groupby("_period")["_val"].sum().reset_index().sort_values("_period")
                return ts

            ts_a = prep_ts(df_a, date_col_a, metric_col_a)
            ts_b = prep_ts(df_b, date_col_b, metric_col_b)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ts_a["_period"],
                y=ts_a["_val"],
                mode="lines+markers",
                name="Dataset A",
                line=dict(color="#38bdf8", width=3)
            ))
            fig.add_trace(go.Scatter(
                x=ts_b["_period"],
                y=ts_b["_val"],
                mode="lines+markers",
                name="Dataset B",
                line=dict(color="#10b981", width=3)
            ))
            fig.update_layout(
                title=f"Historical Trend Overlay ({granularity} Aggregation)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.6)",
                font=dict(color="#f8fafc"),
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            return {
                "available": True,
                "figure": fig,
                "ts_a": ts_a,
                "ts_b": ts_b
            }
        except Exception as exc:
            return {"available": False, "reason": f"Trend comparison failed: {str(exc)}"}

    @classmethod
    def generate_comparison_insights(
        cls,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        name_a: str,
        name_b: str,
        kpi_comp: Dict[str, Any],
        quality_comp: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generates dynamic, data-driven narrative insights without hardcoded strings."""
        insights = []

        row_diff = kpi_comp.get("row_diff", 0)
        row_pct = kpi_comp.get("row_pct", 0.0)

        # 1. Volume shift
        if abs(row_diff) > 0:
            direction = "expanded" if row_diff > 0 else "contracted"
            insights.append({
                "type": "Volume Dynamics",
                "title": f"Dataset Record Volume {direction.capitalize()} by {abs(row_pct):.1f}%",
                "observation": f"{name_b} contains {len(df_b):,} records compared to {len(df_a):,} in {name_a} (net difference of {row_diff:+d} rows).",
                "driver": "Data Ingestion & Cohort Sizing",
                "impact": "High"
            })

        # 2. Numeric metric shift
        num_metrics = kpi_comp.get("num_metrics", {})
        for col_name, m_info in list(num_metrics.items())[:3]:
            s_diff = m_info["sum_diff"]
            s_pct = m_info["sum_pct"]
            if abs(s_diff) > 0:
                s_dir = "growth" if s_diff > 0 else "decline"
                insights.append({
                    "type": "Metric Performance",
                    "title": f"{col_name.title()} showed {abs(s_pct):.1f}% {s_dir}",
                    "observation": f"Aggregated {col_name} shifted from {m_info['sum_a']:,.2f} in {name_a} to {m_info['sum_b']:,.2f} in {name_b} ({s_diff:+,.2f} net change).",
                    "driver": f"{col_name} Variance",
                    "impact": "High" if abs(s_pct) > 10 else "Medium"
                })

        # 3. Quality score shift
        q_delta = quality_comp.get("score_delta", 0.0)
        if abs(q_delta) >= 0.1:
            q_dir = "improved" if q_delta > 0 else "declined"
            insights.append({
                "type": "Data Quality Governance",
                "title": f"Data Quality {q_dir.capitalize()} by {abs(q_delta):.1f} points",
                "observation": f"Overall Data Quality Score moved from {quality_comp['score_a']:.1f}% ({name_a}) to {quality_comp['score_b']:.1f}% ({name_b}).",
                "driver": "Completeness & Validity Shifts",
                "impact": "Medium"
            })

        return insights

    @classmethod
    def answer_comparison_query(
        cls,
        query: str,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        name_a: str,
        name_b: str,
        comp_res: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Natural language comparison query responder."""
        q_lower = query.lower()

        if "revenue" in q_lower or "sales" in q_lower or "higher" in q_lower or "more" in q_lower:
            num_m = comp_res.get("numeric_metrics", {})
            if num_m:
                first_key = list(num_m.keys())[0]
                m = num_m[first_key]
                leader = name_b if m["sum_b"] >= m["sum_a"] else name_a
                return {
                    "answer": f"**{leader}** has higher total {first_key} ({max(m['sum_a'], m['sum_b']):,.2f} vs {min(m['sum_a'], m['sum_b']):,.2f}), representing a **{m['sum_pct']:+.1f}%** shift.",
                    "data": pd.DataFrame([{"Metric": first_key, name_a: m["sum_a"], name_b: m["sum_b"], "Change %": f"{m['sum_pct']:+.1f}%"}])
                }

        if "quality" in q_lower:
            qc = comp_res.get("quality_comparison", {})
            q_lead = name_b if qc.get("score_b", 0) >= qc.get("score_a", 0) else name_a
            return {
                "answer": f"**{q_lead}** exhibits higher data quality ({max(qc.get('score_a', 0), qc.get('score_b', 0)):.1f}% vs {min(qc.get('score_a', 0), qc.get('score_b', 0)):.1f}%, a delta of {qc.get('score_delta', 0):+.1f} pts).",
                "data": pd.DataFrame([{
                    "Dataset": name_a, "Quality Score": f"{qc.get('score_a', 0):.1f}%", "Missing Cells": qc.get("missing_cells_a", 0)
                }, {
                    "Dataset": name_b, "Quality Score": f"{qc.get('score_b', 0):.1f}%", "Missing Cells": qc.get("missing_cells_b", 0)
                }])
            }

        if "change" in q_lower or "diff" in q_lower or "what changed" in q_lower:
            return {
                "answer": f"Between {name_a} and {name_b}, total rows changed by **{comp_res.get('row_pct_change', 0):+.1f}%** ({comp_res.get('row_difference', 0):+d} rows). {len(comp_res.get('insights', []))} major analytical shifts were detected.",
                "data": pd.DataFrame(comp_res.get("insights", []))
            }

        return {
            "answer": f"Compared {name_a} ({len(df_a):,} rows) with {name_b} ({len(df_b):,} rows). Mapped {len(comp_res.get('common_columns', []))} columns across schemas.",
            "data": None
        }

    # Backward compatibility helpers
    @classmethod
    def compare_dimensions(cls, df: pd.DataFrame, dim_col: str, item_a: str, item_b: str, metric_col: str) -> Dict[str, Any]:
        if df.empty or dim_col not in df.columns or metric_col not in df.columns:
            return {"available": False, "reason": "Missing dimension or metric column."}
        df_a = df[df[dim_col].astype(str) == str(item_a)]
        df_b = df[df[dim_col].astype(str) == str(item_b)]
        val_a = float(pd.to_numeric(df_a[metric_col], errors="coerce").sum())
        val_b = float(pd.to_numeric(df_b[metric_col], errors="coerce").sum())
        count_a = len(df_a)
        count_b = len(df_b)
        avg_a = val_a / max(1, count_a)
        avg_b = val_b / max(1, count_b)
        diff_abs = val_a - val_b
        diff_pct = calc_pct_delta(val_b, val_a)
        leader = item_a if val_a >= val_b else item_b
        return {
            "available": True,
            "dim_col": dim_col,
            "metric_col": metric_col,
            "item_a": item_a,
            "item_b": item_b,
            "val_a": val_a,
            "val_b": val_b,
            "count_a": count_a,
            "count_b": count_b,
            "avg_a": avg_a,
            "avg_b": avg_b,
            "diff_abs": diff_abs,
            "diff_pct": diff_pct,
            "leader": leader,
            "summary": f"**{leader}** outperforms by **${abs(diff_abs):,.2f}** ({abs(diff_pct):.1f}% relative difference)."
        }

    @classmethod
    def compare_periods(cls, df: pd.DataFrame, date_col: str, metric_col: str) -> Dict[str, Any]:
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return {"available": False, "reason": "Missing date or metric column."}
        try:
            df_work = df[[date_col, metric_col]].dropna().copy()
            df_work["_dt"] = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work = df_work.dropna(subset=["_dt"]).sort_values("_dt")
            df_work["_val"] = pd.to_numeric(df_work[metric_col], errors="coerce").fillna(0.0)
            if len(df_work) < 4:
                return {"available": False, "reason": "Insufficient observations for period comparison (at least 4 required)."}
            mid_idx = len(df_work) // 2
            p1_df = df_work.iloc[:mid_idx]
            p2_df = df_work.iloc[mid_idx:]
            p1_val = float(p1_df["_val"].sum())
            p2_val = float(p2_df["_val"].sum())
            p1_start = p1_df["_dt"].min().strftime("%b %Y")
            p1_end = p1_df["_dt"].max().strftime("%b %Y")
            p2_start = p2_df["_dt"].min().strftime("%b %Y")
            p2_end = p2_df["_dt"].max().strftime("%b %Y")
            diff_abs = p2_val - p1_val
            diff_pct = calc_pct_delta(p1_val, p2_val)
            return {
                "available": True,
                "p1_label": f"Previous ({p1_start} - {p1_end})",
                "p2_label": f"Current ({p2_start} - {p2_end})",
                "p1_val": p1_val,
                "p2_val": p2_val,
                "diff_abs": diff_abs,
                "diff_pct": diff_pct,
                "growth": diff_pct >= 0,
                "summary": f"Current period achieved **${p2_val:,.2f}** vs **${p1_val:,.2f}** previously ({'+' if diff_pct >= 0 else ''}{diff_pct:.1f}% change)."
            }
        except Exception as e:
            return {"available": False, "reason": f"Calculation error: {str(e)}"}
