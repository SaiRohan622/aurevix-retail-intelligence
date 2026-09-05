"""
AUREVIX — Statistical Time-Series Forecasting Engine
Provides linear trend projection and moving average baselines with confidence intervals.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go

PLOT_BG = "rgba(0,0,0,0)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(34, 47, 73, 0.45)"
TEXT_PRIMARY = "#E8EEF7"
TEXT_SECONDARY = "#CBD5E1"
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


class ForecastEngine:
    """Generates statistical projections for datasets with sufficient historical time series."""

    @classmethod
    def generate_forecast(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        horizon: int = 3
    ) -> Dict[str, Any]:
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return {
                "available": False,
                "reason": "Date or metric column not available in dataset."
            }

        try:
            df_work = df[[date_col, metric_col]].dropna().copy()
            df_work["_dt"] = pd.to_datetime(df_work[date_col], errors="coerce")
            df_work = df_work.dropna(subset=["_dt"]).set_index("_dt")
            df_work["_val"] = pd.to_numeric(df_work[metric_col], errors="coerce").fillna(0.0)

            # Resample monthly
            ts = df_work["_val"].resample("MS").sum().reset_index()

            if len(ts) < 4:
                return {
                    "available": False,
                    "reason": f"Forecast unavailable — at least 4 historical periods required (found {len(ts)})."
                }

            ts["t"] = np.arange(len(ts))
            y = ts["_val"].values
            x = ts["t"].values

            # Linear regression: y = m*x + c
            m, c = np.polyfit(x, y, 1)

            # Standard error of regression
            fitted = m * x + c
            residuals = y - fitted
            std_err = np.std(residuals) if len(residuals) > 1 else y.mean() * 0.1

            # Forecast future points
            last_date = ts["_dt"].max()
            future_dates = [last_date + pd.DateOffset(months=i+1) for i in range(horizon)]
            future_t = np.arange(len(ts), len(ts) + horizon)
            future_y = [max(0.0, float(m * t_val + c)) for t_val in future_t]
            future_upper = [f_val + (1.96 * std_err) for f_val in future_y]
            future_lower = [max(0.0, f_val - (1.96 * std_err)) for f_val in future_y]

            # Build Figure
            fig = go.Figure()

            # Historical Trace
            hist_labels = [d.strftime("%b %Y") for d in ts["_dt"]]
            fig.add_trace(go.Scatter(
                x=hist_labels,
                y=ts["_val"],
                mode="lines+markers",
                name="Historical Actuals",
                line=dict(color="#38bdf8", width=2.5),
                marker=dict(size=6, color="#38bdf8")
            ))

            # Forecast Trace
            fore_labels = [d.strftime("%b %Y (F)") for d in future_dates]
            # Connect last historical to first forecast
            conn_x = [hist_labels[-1]] + fore_labels
            conn_y = [ts["_val"].iloc[-1]] + future_y
            conn_upper = [ts["_val"].iloc[-1]] + future_upper
            conn_lower = [ts["_val"].iloc[-1]] + future_lower

            # Upper Confidence Bound
            fig.add_trace(go.Scatter(
                x=conn_x,
                y=conn_upper,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip"
            ))

            # Lower Confidence Bound + Fill
            fig.add_trace(go.Scatter(
                x=conn_x,
                y=conn_lower,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(168, 85, 247, 0.12)",
                name="95% Confidence Interval"
            ))

            # Forecast line
            fig.add_trace(go.Scatter(
                x=conn_x,
                y=conn_y,
                mode="lines+markers",
                name="Projected Forecast",
                line=dict(color="#a855f7", width=2.5, dash="dash"),
                marker=dict(size=7, color="#a855f7")
            ))

            fig.update_layout(
                paper_bgcolor=PAPER_BG,
                plot_bgcolor=PLOT_BG,
                font=dict(color=TEXT_SECONDARY, family=FONT_FAMILY, size=12),
                xaxis=dict(showgrid=False, tickfont=dict(color=TEXT_PRIMARY, size=11)),
                yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickprefix="$", tickfont=dict(color=TEXT_SECONDARY, size=11)),
                margin=dict(l=10, r=10, t=10, b=10),
                height=290,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#DCE6F2", size=12))
            )

            proj_sum = sum(future_y)
            return {
                "available": True,
                "figure": fig,
                "horizon_months": horizon,
                "forecast_total": proj_sum,
                "next_period_val": future_y[0],
                "next_period_label": fore_labels[0],
                "trend_slope": "Upward" if m > 0 else "Downward",
                "summary": f"Next period ({fore_labels[0]}) is projected at **${future_y[0]:,.2f}** with an overall {('upward' if m > 0 else 'downward')} trajectory."
            }

        except Exception as e:
            return {"available": False, "reason": f"Forecast engine error: {str(e)}"}
