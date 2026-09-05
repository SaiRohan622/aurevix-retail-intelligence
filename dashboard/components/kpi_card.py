"""
AUREVIX — Universal Enterprise KPI Card Component
Flawless HTML rendering without Markdown indentation code-block interference.
"""

import streamlit as st
from dashboard.components.html_utils import render_html


def render_kpi_card(
    title: str = "",
    value: str = "",
    subtext: str = "",
    delta: str = "",
    is_positive: bool = True,
    tooltip: str = "",
    icon: str = "⚡",
    color: str = "blue",
    raw_value: str = "",
    *args,
    **kwargs
):
    # Absorb any positional extras
    if len(args) >= 1 and not tooltip:
        tooltip = str(args[0])
    if len(args) >= 2 and icon == "⚡":
        icon = str(args[1])
    if len(args) >= 3 and color == "blue":
        color = str(args[2])
    if len(args) >= 4 and not raw_value:
        raw_value = str(args[3])

    # Handle keyword aliases
    subtext = kwargs.get("subtitle", subtext)
    delta = kwargs.get("trend", delta)
    if "positive" in kwargs and kwargs["positive"] is not None:
        is_positive = bool(kwargs["positive"])
    tooltip = kwargs.get("help", tooltip)
    if "icon" in kwargs and kwargs["icon"]:
        icon = str(kwargs["icon"])
    if "color" in kwargs and kwargs["color"]:
        color = str(kwargs["color"])
    if "raw_value" in kwargs and kwargs["raw_value"]:
        raw_value = str(kwargs["raw_value"])

    color_map = {
        "purple": {"bg": "rgba(168, 85, 247, 0.12)", "border": "rgba(168, 85, 247, 0.3)", "text": "#a855f7", "spark": "#a855f7"},
        "blue": {"bg": "rgba(56, 189, 248, 0.12)", "border": "rgba(56, 189, 248, 0.3)", "text": "#38bdf8", "spark": "#38bdf8"},
        "emerald": {"bg": "rgba(16, 185, 129, 0.12)", "border": "rgba(16, 185, 129, 0.3)", "text": "#10b981", "spark": "#10b981"},
        "gold": {"bg": "rgba(245, 158, 11, 0.12)", "border": "rgba(245, 158, 11, 0.3)", "text": "#f59e0b", "spark": "#f59e0b"},
        "orange": {"bg": "rgba(249, 115, 22, 0.12)", "border": "rgba(249, 115, 22, 0.3)", "text": "#f97316", "spark": "#f97316"},
        "cyan": {"bg": "rgba(6, 182, 212, 0.12)", "border": "rgba(6, 182, 212, 0.3)", "text": "#06b6d4", "spark": "#06b6d4"}
    }
    c_style = color_map.get(color.lower() if isinstance(color, str) else "blue", color_map["blue"])

    delta_class = "positive" if is_positive else "neutral"
    delta_html = f'<div class="ref-kpi-tag {delta_class}">{delta}</div>' if delta else ""
    raw_html = f'<div class="ref-kpi-value-secondary">{raw_value}</div>' if raw_value else ""
    sub_html = f'<div class="ref-kpi-subdesc">{subtext}</div>' if subtext else ""
    title_attr = f'title="{tooltip}"' if tooltip else ""

    spark_svg = (
        f'<svg class="sparkline-svg" viewBox="0 0 100 25" preserveAspectRatio="none">'
        f'<path d="M0 20 Q 25 5, 50 15 T 100 8" fill="none" stroke="{c_style["spark"]}" stroke-width="2.5" />'
        f'</svg>'
    )

    html = (
        f'<div class="ref-kpi-card" {title_attr}>'
        f'<div>'
        f'<div class="ref-kpi-top">'
        f'<div class="ref-kpi-icon-wrap" style="background: {c_style["bg"]}; border: 1px solid {c_style["border"]}; color: {c_style["text"]};">'
        f'{icon}'
        f'</div>'
        f'<div class="ref-kpi-label">{title}</div>'
        f'</div>'
        f'<div class="ref-kpi-value-primary">{value}</div>'
        f'{raw_html}'
        f'</div>'
        f'<div class="ref-kpi-bottom">'
        f'{delta_html}'
        f'{sub_html}'
        f'</div>'
        f'{spark_svg}'
        f'</div>'
    )
    render_html(html)
