"""
AUREVIX — Interactive Plotly Visualizations Factory
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

PLOT_BG = "rgba(0,0,0,0)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#9ca3af"


def create_revenue_trend_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["order_year_month"],
        y=df["revenue"],
        mode="lines+markers",
        name="Gross Revenue ($)",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=6, color="#60a5fa")
    ))
    fig.update_layout(
        title="Monthly Gross Revenue Trend",
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR, family="Inter"),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickprefix="$"),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified"
    )
    return fig


def create_category_bar_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    df_top = df.head(top_n).sort_values("revenue", ascending=True)
    fig = px.bar(
        df_top,
        x="revenue",
        y="category",
        orientation="h",
        title=f"Top {top_n} Product Categories by Revenue",
        color="revenue",
        color_continuous_scale=["#1e3a8a", "#3b82f6", "#60a5fa"]
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR, family="Inter"),
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickprefix="$"),
        yaxis=dict(showgrid=False),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def create_regional_bar_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    df_top = df.head(top_n).sort_values("revenue", ascending=False)
    fig = px.bar(
        df_top,
        x="state",
        y="revenue",
        title=f"Top {top_n} States by Sales Volume",
        color="revenue",
        color_continuous_scale=["#065f46", "#10b981", "#34d399"]
    )
    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR, family="Inter"),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, tickprefix="$"),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig
