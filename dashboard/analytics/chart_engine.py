"""
AUREVIX — Dynamic Plotly Chart Engine & Automatic Visualization Recommender
Generates interactive enterprise dark-themed Plotly charts with high-contrast, highly readable typography.
"""
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from src.common.logger import get_logger

logger = get_logger("aurevix.chart_engine")

PLOT_BG = "rgba(0,0,0,0)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(34, 47, 73, 0.45)"
TEXT_PRIMARY = "#E8EEF7"
TEXT_SECONDARY = "#CBD5E1"
TEXT_MUTED = "#94A3B8"
LEGEND_TEXT = "#DCE6F2"
LEGEND_TITLE = "#F4F7FB"
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

DONUT_COLORS = [
    "#38bdf8", "#818cf8", "#c084fc", "#f472b6",
    "#fb923c", "#34d399", "#a78bfa", "#f87171",
    "#38d39f", "#94a3b8"
]


def _clean_numeric_series(series: pd.Series) -> pd.Series:
    """Safely converts a series to clean float values, handling currency strings, commas, NaNs, and infinities."""
    if series.empty:
        return series
    if pd.api.types.is_numeric_dtype(series):
        s_clean = pd.to_numeric(series, errors="coerce").fillna(0.0)
    else:
        # Strip common formatting: $, €, £, ¥, %, commas, spaces
        s_str = series.astype(str).str.replace(r"[\$,€,£,¥,%\s]", "", regex=True)
        s_str = s_str.str.replace(",", "", regex=False)
        s_clean = pd.to_numeric(s_str, errors="coerce").fillna(0.0)
    
    # Replace inf/-inf with 0.0
    s_clean = s_clean.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return s_clean


def _format_compact_metric(val: float, is_currency: bool = True) -> str:
    """Formats large metric totals compactly (e.g. $1.45M, $350K, $42.50)."""
    prefix = "$" if is_currency else ""
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"{prefix}{val/1_000_000_000:.2f}B"
    elif abs_val >= 1_000_000:
        return f"{prefix}{val/1_000_000:.2f}M"
    elif abs_val >= 1_000:
        return f"{prefix}{val/1_000:.1f}K"
    else:
        return f"{prefix}{val:,.2f}" if is_currency else f"{val:,.0f}"


class ChartEngine:
    """Builds responsive Plotly charts adhering to AUREVIX dark enterprise design and high readability."""

    @classmethod
    def apply_base_layout(cls, fig: go.Figure, height: int = 280, show_legend: bool = False) -> go.Figure:
        fig.update_layout(
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(color=TEXT_SECONDARY, family=FONT_FAMILY, size=12),
            xaxis=dict(
                showgrid=True,
                gridcolor=GRID_COLOR,
                zeroline=False,
                tickfont=dict(color=TEXT_SECONDARY, size=11, family=FONT_FAMILY),
                title=dict(font=dict(color=TEXT_PRIMARY, size=12, family=FONT_FAMILY))
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=GRID_COLOR,
                zeroline=False,
                tickfont=dict(color=TEXT_SECONDARY, size=11, family=FONT_FAMILY),
                title=dict(font=dict(color=TEXT_PRIMARY, size=12, family=FONT_FAMILY))
            ),
            margin=dict(l=10, r=10, t=10, b=10),
            height=height,
            hoverlabel=dict(
                bgcolor="#0f1523",
                font_size=12,
                font_family=FONT_FAMILY,
                font_color="#F8FAFC",
                bordercolor="#22304d"
            ),
            showlegend=show_legend
        )
        if show_legend:
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color=LEGEND_TEXT, size=12, family=FONT_FAMILY),
                    title=dict(font=dict(color=LEGEND_TITLE, size=12, family=FONT_FAMILY))
                )
            )
        return fig

    @classmethod
    def create_dimension_donut_chart(
        cls,
        df: pd.DataFrame,
        category_column: str,
        metric_column: Optional[str] = None,
        top_n: int = 6,
        height: int = 260
    ) -> Optional[go.Figure]:
        """
        Creates a high-contrast enterprise Plotly donut chart showing proportional distribution.
        Handles missing values, currency strings, negative values, and 'Other' aggregation safely.
        Returns None if dataset or columns are unsuitable for donut visualization.
        """
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return None

        try:
            # Deduplicate columns if identical names exist
            df_work = df.loc[:, ~df.columns.duplicated()].copy()

            if not category_column or category_column not in df_work.columns:
                return None

            # Prepare categories
            cat_series = df_work[category_column].fillna("Unspecified").astype(str).str.strip()
            cat_series = cat_series.replace({"": "Unspecified", "nan": "Unspecified", "None": "Unspecified"})

            # Prepare metric series
            if metric_column and metric_column in df_work.columns:
                val_series = _clean_numeric_series(df_work[metric_column])
                is_currency = any(term in metric_column.lower() for term in ["revenue", "sales", "price", "profit", "cost", "salary", "spend", "amount", "budget", "billed", "freight"])
                metric_label = metric_column.replace("_", " ").title()
            else:
                val_series = pd.Series(1.0, index=df_work.index)
                is_currency = False
                metric_label = "Count"

            # Filter negative values for proportional donut chart
            valid_mask = val_series > 0
            if not valid_mask.any():
                return None

            df_valid = pd.DataFrame({
                "_cat": cat_series[valid_mask],
                "_val": val_series[valid_mask]
            })

            grp = df_valid.groupby("_cat")["_val"].sum().sort_values(ascending=False)
            if grp.empty:
                return None

            total_val = float(grp.sum())
            if total_val <= 0:
                return None

            # Top N & Other aggregation
            top_slice = grp.head(top_n)
            labels = list(top_slice.index.astype(str))
            values = [float(v) for v in top_slice.values]

            if len(grp) > top_n:
                other_sum = float(grp.iloc[top_n:].sum())
                if other_sum > 0:
                    labels.append("Other")
                    values.append(other_sum)

            colors = DONUT_COLORS[:len(labels)]
            while len(colors) < len(labels):
                colors.extend(DONUT_COLORS)
            colors = colors[:len(labels)]

            total_label_str = _format_compact_metric(total_val, is_currency=is_currency)

            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="#0d1322", width=1.8)),
                textinfo="percent",
                textfont=dict(color="#FFFFFF", size=11, family=FONT_FAMILY),
                hovertemplate="<b>%{label}</b><br>" +
                              f"{metric_label}: " + ("$%{value:,.2f}" if is_currency else "%{value:,.0f}") +
                              "<br>Share: %{percent}<extra></extra>"
            ))

            fig.update_layout(
                paper_bgcolor=PAPER_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT_SECONDARY, family=FONT_FAMILY, size=11),
                margin=dict(l=10, r=10, t=10, b=10),
                height=height,
                showlegend=False,
                annotations=[
                    dict(
                        text=f"<b>{total_label_str}</b><br><span style='font-size:10px; color:#94A3B8;'>{metric_label}</span>",
                        x=0.5, y=0.5,
                        font=dict(size=13, color="#FFFFFF", family=FONT_FAMILY),
                        showarrow=False
                    )
                ]
            )
            return fig
        except Exception as e:
            logger.warning(f"Error generating dimension donut chart: {e}")
            return None

    # Backward-compatible aliases
    create_composition_donut_chart = create_dimension_donut_chart
    create_category_donut_chart = create_dimension_donut_chart
    create_donut_chart = create_dimension_donut_chart
    dimension_donut_chart = create_dimension_donut_chart
    create_pie_chart = create_dimension_donut_chart

    @classmethod
    def create_time_series_chart(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        granularity: str = "Monthly",
        agg_func: str = "SUM",
        height: int = 280
    ) -> Optional[go.Figure]:
        """Builds a responsive time series area/line chart."""
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return None

        try:
            df_work = df.loc[:, ~df.columns.duplicated()].copy()
            if date_col not in df_work.columns or metric_col not in df_work.columns:
                return None

            df_work["_dt"] = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work = df_work.dropna(subset=["_dt"])
            if df_work.empty:
                return None

            df_work["_val"] = _clean_numeric_series(df_work[metric_col])

            freq_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS", "Quarterly": "QS", "Yearly": "YS"}
            freq = freq_map.get(granularity, "MS")

            df_work = df_work.set_index("_dt")
            agg_up = agg_func.upper()
            if agg_up == "AVG":
                ts = df_work["_val"].resample(freq).mean().reset_index()
            elif agg_up == "COUNT":
                ts = df_work["_val"].resample(freq).count().reset_index()
            else:
                ts = df_work["_val"].resample(freq).sum().reset_index()

            ts = ts.dropna()
            if ts.empty:
                return None

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ts["_dt"].dt.strftime("%Y-%m-%d"),
                y=ts["_val"],
                mode="lines+markers",
                name=f"{agg_func} of {metric_col}",
                line=dict(color="#38bdf8", width=2.5),
                marker=dict(size=5, color="#0284c7"),
                fill="tozeroy",
                fillcolor="rgba(56, 189, 248, 0.08)",
                hovertemplate=f"<b>Date: %{{x}}</b><br>{metric_col}: %{{y:,.2f}}<extra></extra>"
            ))

            return cls.apply_base_layout(fig, height=height)
        except Exception as e:
            logger.warning(f"Error generating time series chart: {e}")
            return None

    @classmethod
    def create_dimension_bar_chart(
        cls,
        df: pd.DataFrame,
        dimension_col: str,
        metric_col: str,
        top_n: int = 10,
        orientation: str = "v",
        height: int = 280
    ) -> Optional[go.Figure]:
        """Builds a ranked vertical or horizontal bar chart."""
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return None

        try:
            df_work = df.loc[:, ~df.columns.duplicated()].copy()
            if dimension_col not in df_work.columns or metric_col not in df_work.columns:
                return None

            df_work["_cat"] = df_work[dimension_col].fillna("Unspecified").astype(str)
            df_work["_val"] = _clean_numeric_series(df_work[metric_col])
            grp = df_work.groupby("_cat")["_val"].sum().sort_values(ascending=False).head(top_n)

            if grp.empty:
                return None

            fig = go.Figure()
            if orientation == "h":
                fig.add_trace(go.Bar(
                    y=grp.index.astype(str)[::-1],
                    x=grp.values[::-1],
                    orientation="h",
                    marker=dict(color="#38bdf8", opacity=0.9),
                    name=metric_col,
                    hovertemplate="<b>%{y}</b><br>Volume: %{x:,.2f}<extra></extra>"
                ))
            else:
                fig.add_trace(go.Bar(
                    x=grp.index.astype(str),
                    y=grp.values,
                    marker=dict(color="#38bdf8", opacity=0.9),
                    name=metric_col,
                    hovertemplate="<b>%{x}</b><br>Volume: %{y:,.2f}<extra></extra>"
                ))

            return cls.apply_base_layout(fig, height=height)
        except Exception as e:
            logger.warning(f"Error generating dimension bar chart: {e}")
            return None

    @classmethod
    def create_scatter_correlation_chart(
        cls,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        cat_col: Optional[str] = None,
        height: int = 280
    ) -> Optional[go.Figure]:
        """Builds a bivariate correlation scatter chart."""
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return None

        try:
            df_work = df.loc[:, ~df.columns.duplicated()].copy()
            if x_col not in df_work.columns or y_col not in df_work.columns:
                return None

            df_work["_x"] = _clean_numeric_series(df_work[x_col])
            df_work["_y"] = _clean_numeric_series(df_work[y_col])
            df_work = df_work.dropna(subset=["_x", "_y"]).head(2000)

            if df_work.empty:
                return None

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_work["_x"],
                y=df_work["_y"],
                mode="markers",
                marker=dict(color="#38bdf8", size=6, opacity=0.7),
                name=f"{y_col} vs {x_col}",
                hovertemplate=f"<b>{x_col}:</b> %{{x:,.2f}}<br><b>{y_col}:</b> %{{y:,.2f}}<extra></extra>"
            ))

            fig = cls.apply_base_layout(fig, height=height)
            fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)
            return fig
        except Exception as e:
            logger.warning(f"Error generating scatter chart: {e}")
            return None

    @classmethod
    def recommend_visualizations(
        cls,
        df: pd.DataFrame,
        schema_meta: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Intelligent visualization recommendation engine suggesting top Plotly charts based on schema."""
        recs = []
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return recs

        try:
            roles = schema_meta.get("roles", {})
            num_cols = schema_meta.get("numeric_columns", [])
            date_cols = schema_meta.get("date_columns", [])
            cat_cols = schema_meta.get("categorical_columns", [])
            geo_cols = schema_meta.get("geographic_columns", [])

            metric_col = roles.get("revenue") or (num_cols[0] if num_cols else None)
            date_col = roles.get("date") or (date_cols[0] if date_cols else None)
            cat_col = roles.get("category") or (cat_cols[0] if cat_cols else None)
            reg_col = roles.get("region") or (geo_cols[0] if geo_cols else None)

            # 1. Time Series Trend
            if date_col and metric_col and date_col in df.columns and metric_col in df.columns:
                fig_trend = cls.create_time_series_chart(df, date_col, metric_col)
                if fig_trend is not None:
                    recs.append({
                        "id": "trend",
                        "title": f"Time-Series Progression ({metric_col})",
                        "reason": f"Reveals seasonality and momentum across temporal timeline `{date_col}`.",
                        "chart_type": "Area / Trend Chart",
                        "dimension": date_col,
                        "measure": metric_col,
                        "figure": fig_trend
                    })

            # 2. Category Ranking Bar
            if cat_col and metric_col and cat_col in df.columns and metric_col in df.columns:
                fig_bar = cls.create_dimension_bar_chart(df, cat_col, metric_col, top_n=8)
                if fig_bar is not None:
                    recs.append({
                        "id": "category_bar",
                        "title": f"Segment Breakdown by {cat_col.replace('_', ' ').title()}",
                        "reason": f"Highlights top-performing clusters and contribution variance across `{cat_col}`.",
                        "chart_type": "Ranked Bar Chart",
                        "dimension": cat_col,
                        "measure": metric_col,
                        "figure": fig_bar
                    })

            # 3. Composition Donut
            if cat_col and metric_col and cat_col in df.columns and metric_col in df.columns:
                fig_donut = cls.create_dimension_donut_chart(df, cat_col, metric_col)
                if fig_donut is not None:
                    recs.append({
                        "id": "donut",
                        "title": f"Portfolio Share ({cat_col.replace('_', ' ').title()})",
                        "reason": f"Visualizes market share distribution and dominance for `{cat_col}`.",
                        "chart_type": "Donut Composition",
                        "dimension": cat_col,
                        "measure": metric_col,
                        "figure": fig_donut
                    })

            # 4. Regional Geographic Bar
            if reg_col and metric_col and reg_col in df.columns and metric_col in df.columns and reg_col != cat_col:
                fig_geo = cls.create_dimension_bar_chart(df, reg_col, metric_col, top_n=8, orientation="h")
                if fig_geo is not None:
                    recs.append({
                        "id": "geo_bar",
                        "title": f"Geographic Distribution by {reg_col.replace('_', ' ').title()}",
                        "reason": f"Maps regional demand across `{reg_col}`.",
                        "chart_type": "Geographic Bar Chart",
                        "dimension": reg_col,
                        "measure": metric_col,
                        "figure": fig_geo
                    })

            # 5. Scatter Plot Correlation
            if len(num_cols) >= 2:
                x_c = num_cols[0]
                y_c = num_cols[1]
                if x_c in df.columns and y_c in df.columns:
                    fig_scatter = cls.create_scatter_correlation_chart(df, x_c, y_c)
                    if fig_scatter is not None:
                        recs.append({
                            "id": "scatter",
                            "title": f"Bivariate Correlation: {y_c} vs {x_c}",
                            "reason": f"Analyzes statistical co-movement between `{x_c}` and `{y_c}`.",
                            "chart_type": "Scatter Plot",
                            "dimension": x_c,
                            "measure": y_c,
                            "figure": fig_scatter
                        })
        except Exception as e:
            logger.warning(f"Error computing visualization recommendations: {e}")

        return recs
