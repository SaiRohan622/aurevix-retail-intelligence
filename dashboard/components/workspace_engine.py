"""
AUREVIX — Universal Business Data Analytics Engine
Automatic dataset profiling, intelligent date detection, time-series intelligence,
KPI discovery, rule-based business insights, and smart chart generation.
"""

import io
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

PLOT_BG = "rgba(0,0,0,0)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(25, 35, 56, 0.6)"
TEXT_COLOR = "#94a3b8"
FONT_FAMILY = "Inter, sans-serif"


class WorkspaceEngine:
    """Universal analytical engine for user-uploaded business datasets."""

    DATE_PATTERNS = [
        "date", "timestamp", "datetime", "created", "order_date", "invoice_date",
        "purchase", "trans_date", "time", "day", "period", "year_month"
    ]

    REVENUE_PATTERNS = ["revenue", "sales", "gross", "amount", "total_amount", "price", "val", "spend"]
    PROFIT_PATTERNS = ["profit", "margin", "net_margin", "gain"]
    COST_PATTERNS = ["cost", "freight", "expense", "fee", "tax"]
    QUANTITY_PATTERNS = ["quantity", "qty", "units", "items", "count", "volume"]
    ORDER_ID_PATTERNS = ["order_id", "invoice_id", "transaction_id", "trans_id", "receipt_id"]
    CUSTOMER_ID_PATTERNS = ["customer_id", "user_id", "client_id", "buyer_id", "account_id"]

    @staticmethod
    def load_dataset(file_obj, filename: str) -> pd.DataFrame:
        """Load CSV, Excel, Parquet, or JSON files safely into a pandas DataFrame."""
        from dashboard.analytics.data_loader import UniversalDataLoader
        df, _ = UniversalDataLoader.load_file(file_obj, filename)
        return df

    @classmethod
    def profile_dataset(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive data profiling metrics and data-quality score."""
        row_count = len(df)
        col_count = len(df.columns)
        if row_count == 0:
            return {
                "row_count": 0, "col_count": col_count, "memory_mb": 0.0,
                "missing_cells": 0, "missing_pct": 0.0, "duplicate_rows": 0,
                "duplicate_pct": 0.0, "quality_score": 100.0, "columns": {}
            }

        total_cells = row_count * col_count
        missing_cells = int(df.isnull().sum().sum())
        missing_pct = (missing_cells / total_cells) * 100.0 if total_cells > 0 else 0.0

        duplicate_rows = int(df.duplicated().sum())
        duplicate_pct = (duplicate_rows / row_count) * 100.0 if row_count > 0 else 0.0

        memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

        # DQ Score formulation
        penalty = (missing_pct * 0.4) + (duplicate_pct * 0.6)
        quality_score = max(0.0, min(100.0, 100.0 - penalty))

        col_profiles = {}
        for col in df.columns:
            s = df[col]
            nulls = int(s.isnull().sum())
            uniques = int(s.nunique(dropna=True))
            dtype_str = str(s.dtype)
            sem_type = cls._classify_column(col, s)
            samples = s.dropna().head(3).tolist()
            col_profiles[col] = {
                "dtype": dtype_str,
                "semantic_type": sem_type,
                "null_count": nulls,
                "null_pct": (nulls / row_count) * 100.0 if row_count > 0 else 0.0,
                "unique_count": uniques,
                "samples": [str(x) for x in samples]
            }

        return {
            "row_count": row_count,
            "col_count": col_count,
            "memory_mb": memory_mb,
            "missing_cells": missing_cells,
            "missing_pct": missing_pct,
            "duplicate_rows": duplicate_rows,
            "duplicate_pct": duplicate_pct,
            "quality_score": quality_score,
            "columns": col_profiles
        }

    @classmethod
    def _classify_column(cls, col_name: str, series: pd.Series) -> str:
        """Classify column into: date, numeric, id, categorical, boolean, or text."""
        name_lower = str(col_name).lower()

        if pd.api.types.is_bool_dtype(series) or (series.dropna().isin([True, False, 0, 1]).all() and series.nunique() <= 2 and not pd.api.types.is_numeric_dtype(series)):
            return "boolean"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"
        if any(p in name_lower for p in cls.DATE_PATTERNS):
            sample = series.dropna().head(10)
            if not sample.empty:
                try:
                    pd.to_datetime(sample, errors="raise")
                    return "date"
                except Exception:
                    pass

        if (name_lower.endswith("_id") or name_lower.endswith("id") or name_lower.endswith("_key") or
                name_lower.endswith("_code") or name_lower == "sku"):
            return "id"

        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        uniques = series.nunique()
        total = len(series.dropna())
        if uniques <= 100 or (total > 0 and (uniques / total) < 0.2):
            return "categorical"

        return "text"

    @classmethod
    def detect_date_columns(cls, df: pd.DataFrame) -> List[str]:
        """Identify all date/timestamp columns in the DataFrame."""
        date_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_cols.append(col)
                continue
            name_lower = str(col).lower()
            if any(p in name_lower for p in cls.DATE_PATTERNS):
                sample = df[col].dropna().head(20)
                if not sample.empty:
                    try:
                        pd.to_datetime(sample, errors="raise")
                        date_cols.append(col)
                    except Exception:
                        pass
        return date_cols

    @classmethod
    def detect_kpi_mappings(cls, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Identify best-matching columns for standard business metrics."""
        cols_lower = {str(c).lower(): c for c in df.columns}
        
        def find_best_match(patterns: List[str], require_numeric: bool = True) -> Optional[str]:
            for p in patterns:
                for cl, orig in cols_lower.items():
                    if p in cl:
                        if require_numeric and not pd.api.types.is_numeric_dtype(df[orig]):
                            continue
                        return orig
            return None

        return {
            "revenue": find_best_match(cls.REVENUE_PATTERNS, require_numeric=True),
            "profit": find_best_match(cls.PROFIT_PATTERNS, require_numeric=True),
            "cost": find_best_match(cls.COST_PATTERNS, require_numeric=True),
            "quantity": find_best_match(cls.QUANTITY_PATTERNS, require_numeric=True),
            "order_id": find_best_match(cls.ORDER_ID_PATTERNS, require_numeric=False),
            "customer_id": find_best_match(cls.CUSTOMER_ID_PATTERNS, require_numeric=False),
        }

    @classmethod
    def aggregate_time_series(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        granularity: str = "Monthly",
        agg_func: str = "SUM"
    ) -> pd.DataFrame:
        """Aggregate metric column over time with period-over-period and YoY intelligence."""
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return pd.DataFrame()

        df_work = df[[date_col, metric_col]].dropna().copy()
        try:
            df_work["_parsed_date"] = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work = df_work.dropna(subset=["_parsed_date"])
        except Exception:
            return pd.DataFrame()

        if df_work.empty:
            return pd.DataFrame()

        df_work["_numeric_metric"] = pd.to_numeric(df_work[metric_col], errors="coerce").fillna(0.0)

        freq_map = {
            "Daily": "D",
            "Weekly": "W-MON",
            "Monthly": "MS",
            "Quarterly": "QS",
            "Yearly": "YS"
        }
        freq = freq_map.get(granularity, "MS")

        df_work = df_work.set_index("_parsed_date")
        agg_lower = agg_func.upper()
        if agg_lower == "SUM":
            ts = df_work["_numeric_metric"].resample(freq).sum()
        elif agg_lower in ("AVG", "AVERAGE", "MEAN"):
            ts = df_work["_numeric_metric"].resample(freq).mean()
        elif agg_lower == "COUNT":
            ts = df_work["_numeric_metric"].resample(freq).count()
        elif agg_lower == "MIN":
            ts = df_work["_numeric_metric"].resample(freq).min()
        elif agg_lower == "MAX":
            ts = df_work["_numeric_metric"].resample(freq).max()
        elif agg_lower == "MEDIAN":
            ts = df_work["_numeric_metric"].resample(freq).median()
        else:
            ts = df_work["_numeric_metric"].resample(freq).sum()

        res_df = ts.reset_index()
        res_df.columns = ["date", "value"]
        res_df = res_df.sort_values("date").reset_index(drop=True)

        if granularity == "Monthly":
            res_df["period_label"] = res_df["date"].dt.strftime("%b %Y")
        elif granularity == "Daily":
            res_df["period_label"] = res_df["date"].dt.strftime("%Y-%m-%d")
        elif granularity == "Weekly":
            res_df["period_label"] = res_df["date"].dt.strftime("W%W %Y")
        elif granularity == "Quarterly":
            res_df["period_label"] = res_df["date"].dt.to_period("Q").astype(str)
        elif granularity == "Yearly":
            res_df["period_label"] = res_df["date"].dt.strftime("%Y")
        else:
            res_df["period_label"] = res_df["date"].dt.strftime("%Y-%m")

        res_df["pop_growth_pct"] = res_df["value"].pct_change() * 100.0
        res_df["rolling_3_avg"] = res_df["value"].rolling(window=3, min_periods=1).mean()
        res_df["cumulative_total"] = res_df["value"].cumsum()

        periods_for_yoy = {"Monthly": 12, "Quarterly": 4, "Weekly": 52, "Daily": 365, "Yearly": 1}.get(granularity, 12)
        if len(res_df) > periods_for_yoy:
            res_df["yoy_growth_pct"] = res_df["value"].pct_change(periods=periods_for_yoy) * 100.0
        else:
            res_df["yoy_growth_pct"] = np.nan

        return res_df

    @classmethod
    def generate_smart_insights(
        cls,
        df: pd.DataFrame,
        date_col: Optional[str] = None,
        metric_col: Optional[str] = None,
        dim_col: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Generate high-impact data-driven executive takeaways."""
        insights = []
        if df.empty:
            return insights

        if metric_col and metric_col in df.columns and pd.api.types.is_numeric_dtype(df[metric_col]):
            total_val = float(df[metric_col].sum())
            avg_val = float(df[metric_col].mean())
            med_val = float(df[metric_col].median())
            insights.append({
                "type": "summary",
                "title": f"Aggregate {metric_col.replace('_', ' ').title()}",
                "text": f"Total accumulated <b>${total_val:,.2f}</b> (or {total_val:,.2f} units) across {len(df):,} records, with a mean of ${avg_val:,.2f} and median of ${med_val:,.2f} per record.",
                "badge": "AGGREGATE"
            })

        if metric_col and dim_col and metric_col in df.columns and dim_col in df.columns:
            try:
                cat_grp = df.groupby(dim_col)[metric_col].sum().sort_values(ascending=False)
                if not cat_grp.empty:
                    top_cat = cat_grp.index[0]
                    top_val = cat_grp.iloc[0]
                    tot = cat_grp.sum()
                    share_pct = (top_val / tot * 100.0) if tot > 0 else 0.0
                    insights.append({
                        "type": "concentration",
                        "title": f"Top Performing {dim_col.replace('_', ' ').title()}",
                        "text": f"<b>{top_cat}</b> is the leading contributor generating <b>${top_val:,.2f}</b> ({share_pct:.1f}% of total volume across {len(cat_grp):,} distinct categories).",
                        "badge": "LEADER"
                    })
            except Exception:
                pass

        if date_col and metric_col and date_col in df.columns and metric_col in df.columns:
            try:
                df_ts = cls.aggregate_time_series(df, date_col, metric_col, granularity="Monthly")
                if not df_ts.empty and len(df_ts) >= 2:
                    peak_row = df_ts.sort_values("value", ascending=False).iloc[0]
                    latest_growth = df_ts["pop_growth_pct"].iloc[-1]
                    growth_str = f"+{latest_growth:.1f}%" if latest_growth >= 0 else f"{latest_growth:.1f}%"
                    insights.append({
                        "type": "trend",
                        "title": "Peak Operational Period & Momentum",
                        "text": f"Peak performance occurred in <b>{peak_row['period_label']}</b> (${peak_row['value']:,.2f}). Most recent period momentum recorded <b>{growth_str}</b> growth.",
                        "badge": "MOMENTUM"
                    })
            except Exception:
                pass

        missing_count = int(df.isnull().sum().sum())
        dup_count = int(df.duplicated().sum())
        if missing_count == 0 and dup_count == 0:
            insights.append({
                "type": "quality",
                "title": "High Data Fidelity",
                "text": "The uploaded dataset contains <b>0 missing values</b> and <b>0 duplicate rows</b>, representing a 100% clean analytical dataset ready for production reporting.",
                "badge": "100% CLEAN"
            })
        else:
            insights.append({
                "type": "quality",
                "title": "Data Hygiene Alert",
                "text": f"Identified <b>{missing_count:,} missing values</b> and <b>{dup_count:,} duplicate rows</b>. Dynamic filters and aggregations have safely handled null entries.",
                "badge": "AUDITED"
            })

        return insights

    @staticmethod
    def create_time_series_chart(df_ts: pd.DataFrame, metric_name: str) -> go.Figure:
        """Create responsive interactive Plotly time-series chart with rolling average."""
        fig = go.Figure()
        if df_ts.empty:
            return fig

        fig.add_trace(go.Scatter(
            x=df_ts["period_label"],
            y=df_ts["value"],
            mode="lines+markers",
            name=metric_name.replace("_", " ").title(),
            line=dict(color="#38bdf8", width=2.8, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.08)",
            marker=dict(size=6, color="#38bdf8", line=dict(width=1.5, color="#080c14")),
            hovertemplate="<b>%{x}</b><br>Value: %{y:,.2f}<extra></extra>"
        ))

        if "rolling_3_avg" in df_ts.columns and len(df_ts) >= 3:
            fig.add_trace(go.Scatter(
                x=df_ts["period_label"],
                y=df_ts["rolling_3_avg"],
                mode="lines",
                name="3-Period Moving Avg",
                line=dict(color="#f59e0b", width=2, dash="dash"),
                hovertemplate="Moving Avg: %{y:,.2f}<extra></extra>"
            ))

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT_COLOR, family=FONT_FAMILY, size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    @staticmethod
    def create_dimension_bar_chart(df: pd.DataFrame, dim_col: str, metric_col: str, top_n: int = 10) -> go.Figure:
        """Create horizontal or vertical ranked bar chart for categorical dimension."""
        fig = go.Figure()
        if df.empty or dim_col not in df.columns or metric_col not in df.columns:
            return fig

        grp = df.groupby(dim_col)[metric_col].sum().sort_values(ascending=True).tail(top_n).reset_index()
        fig.add_trace(go.Bar(
            x=grp[metric_col],
            y=grp[dim_col].astype(str),
            orientation="h",
            marker=dict(
                color=grp[metric_col],
                colorscale=[[0, "#0284c7"], [1, "#38bdf8"]],
                line=dict(width=0)
            ),
            hovertemplate="<b>%{y}</b><br>Total: %{x:,.2f}<extra></extra>"
        ))

        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT_COLOR, family=FONT_FAMILY, size=11),
            xaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=10, t=10, b=10),
            height=280
        )
        return fig

    @staticmethod
    def create_dimension_donut_chart(df: pd.DataFrame, dim_col: str, metric_col: str, top_n: int = 6) -> go.Figure:
        """Create donut breakdown chart for categorical dimension."""
        fig = go.Figure()
        if df.empty or dim_col not in df.columns or metric_col not in df.columns:
            return fig

        grp = df.groupby(dim_col)[metric_col].sum().sort_values(ascending=False).reset_index()
        top_grp = grp.head(top_n).copy()
        other_val = grp.iloc[top_n:][metric_col].sum() if len(grp) > top_n else 0.0

        if other_val > 0:
            other_df = pd.DataFrame([{dim_col: "Others", metric_col: other_val}])
            plot_df = pd.concat([top_grp, other_df], ignore_index=True)
        else:
            plot_df = top_grp

        colors = ["#a855f7", "#38bdf8", "#10b981", "#f59e0b", "#f97316", "#e11d48", "#64748b"]

        fig = go.Figure(go.Pie(
            labels=plot_df[dim_col].astype(str),
            values=plot_df[metric_col],
            hole=0.65,
            marker=dict(colors=colors, line=dict(color="#0f1523", width=2)),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>Volume: %{value:,.2f}<br>Share: %{percent}<extra></extra>"
        ))

        tot = float(plot_df[metric_col].sum())
        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT_COLOR, family=FONT_FAMILY),
            margin=dict(l=5, r=5, t=5, b=5),
            height=240,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            annotations=[
                dict(
                    text=f"<b>{tot:,.0f}</b><br><span style='font-size:10px; color:#64748b;'>Total</span>",
                    x=0.5, y=0.5,
                    font=dict(size=13, color="#ffffff", family=FONT_FAMILY),
                    showarrow=False
                )
            ]
        )
        return fig
