"""
AUREVIX — Interactive Plotly Visualizations Factory
Pixel-perfect styling matching AUREVIX dark enterprise design with high-contrast readable typography.
"""

import plotly.graph_objects as go
import pandas as pd

PLOT_BG = "rgba(0,0,0,0)"
PAPER_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(34, 47, 73, 0.45)"
TEXT_PRIMARY = "#E8EEF7"
TEXT_SECONDARY = "#CBD5E1"
TEXT_MUTED = "#94A3B8"
LEGEND_TEXT = "#DCE6F2"
LEGEND_TITLE = "#F4F7FB"
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def apply_chart_theme(fig: go.Figure, height: int = 260, show_legend: bool = False, legend_h: bool = True) -> go.Figure:
    """Applies consistent, highly-readable typography and axis contrast across all charts."""
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
        if legend_h:
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
        else:
            fig.update_layout(
                legend=dict(
                    font=dict(color=LEGEND_TEXT, size=12, family=FONT_FAMILY),
                    title=dict(font=dict(color=LEGEND_TITLE, size=12, family=FONT_FAMILY))
                )
            )
    return fig


def create_revenue_trend_chart(df: pd.DataFrame, *args, **kwargs) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        return fig

    df_copy = df.copy()
    if "revenue" in df_copy.columns:
        df_copy["revenue"] = df_copy["revenue"].astype(float)

    fig.add_trace(go.Scatter(
        x=df_copy["order_year_month"],
        y=df_copy["revenue"],
        mode="lines+markers",
        name="Gross Revenue (USD)",
        line=dict(color="#38bdf8", width=2.8, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(56, 189, 248, 0.08)",
        marker=dict(size=6, color="#38bdf8", line=dict(width=1.5, color="#060911")),
        hovertemplate="<b>Month: %{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=240, show_legend=False)
    fig.update_layout(
        yaxis=dict(tickprefix="$", gridcolor=GRID_COLOR),
        hovermode="x unified"
    )
    return fig


def create_category_donut_chart(df: pd.DataFrame, top_n: int = 5, *args, **kwargs) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        return fig

    df_copy = df.copy()
    if "revenue" in df_copy.columns:
        df_copy["revenue"] = df_copy["revenue"].astype(float)

    df_sorted = df_copy.sort_values("revenue", ascending=False)
    df_top = df_sorted.head(top_n).copy()

    total_revenue = float(df_copy["revenue"].sum())
    top_revenue = float(df_top["revenue"].sum())
    other_revenue = max(0.0, total_revenue - top_revenue)

    if other_revenue > 0:
        other_df = pd.DataFrame([{"category": "Others", "revenue": other_revenue, "units": 0}])
        df_plot = pd.concat([df_top, other_df], ignore_index=True)
    else:
        df_plot = df_top

    colors = ["#a855f7", "#38bdf8", "#10b981", "#f59e0b", "#ec4899", "#818cf8"]

    fig = go.Figure(go.Pie(
        labels=df_plot["category"],
        values=df_plot["revenue"],
        hole=0.68,
        marker=dict(colors=colors, line=dict(color="#0d1322", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.2f}<br>Share: %{percent}<extra></extra>"
    ))

    fig.update_layout(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_SECONDARY, family=FONT_FAMILY, size=12),
        margin=dict(l=5, r=5, t=5, b=5),
        height=220,
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>${total_revenue/1e6:.2f}M</b><br><span style='font-size:10px; color:#AAB8CC;'>Total Revenue</span>",
                x=0.5, y=0.5,
                font=dict(size=14, color="#FFFFFF", family=FONT_FAMILY),
                showarrow=False
            )
        ]
    )
    return fig


def create_category_bar_chart(df: pd.DataFrame, top_n: int = 10, *args, **kwargs) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        return fig

    df_copy = df.copy()
    if "revenue" in df_copy.columns:
        df_copy["revenue"] = df_copy["revenue"].astype(float)

    df_top = df_copy.head(top_n).sort_values("revenue", ascending=True)
    fig = go.Figure(go.Bar(
        x=df_top["revenue"],
        y=df_top["category"],
        orientation="h",
        marker=dict(
            color=df_top["revenue"],
            colorscale=[[0, "#0284c7"], [1, "#38bdf8"]],
            line=dict(width=0)
        ),
        hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.2f}<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=260, show_legend=False)
    fig.update_layout(
        xaxis=dict(tickprefix="$", gridcolor=GRID_COLOR),
        yaxis=dict(showgrid=False, tickfont=dict(color=TEXT_PRIMARY, size=11))
    )
    return fig


def create_regional_bar_chart(df: pd.DataFrame, top_n: int = 10, *args, **kwargs) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        return fig

    df_copy = df.copy()
    if "revenue" in df_copy.columns:
        df_copy["revenue"] = df_copy["revenue"].astype(float)

    df_top = df_copy.head(top_n).sort_values("revenue", ascending=False)
    fig = go.Figure(go.Bar(
        x=df_top["state"],
        y=df_top["revenue"],
        marker=dict(
            color=df_top["revenue"],
            colorscale=[[0, "#059669"], [1, "#34d399"]],
            line=dict(width=0)
        ),
        hovertemplate="<b>State: %{x}</b><br>Volume: $%{y:,.2f}<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=260, show_legend=False)
    fig.update_layout(
        xaxis=dict(showgrid=False, tickfont=dict(color=TEXT_PRIMARY, size=11)),
        yaxis=dict(tickprefix="$", gridcolor=GRID_COLOR)
    )
    return fig


from dashboard.components.kpi_card import render_kpi_card


from dashboard.analytics.chart_engine import ChartEngine
create_dimension_donut_chart = ChartEngine.create_dimension_donut_chart
