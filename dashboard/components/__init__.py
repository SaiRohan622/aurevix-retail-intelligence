"""
AUREVIX — Dashboard Components Package
Exports all UI components, charts, KPI cards, sidebar, data loaders, HTML utilities, and WorkspaceEngine.
"""

from dashboard.components.kpi_card import render_kpi_card
from dashboard.components.charts import (
    create_revenue_trend_chart,
    create_category_donut_chart,
    create_category_bar_chart,
    create_regional_bar_chart
)
from dashboard.components.sidebar import render_sidebar
from dashboard.components.data_loader import DashboardDataLoader
from dashboard.components.html_utils import render_html
from dashboard.components.workspace_engine import WorkspaceEngine

__all__ = [
    "render_kpi_card",
    "create_revenue_trend_chart",
    "create_category_donut_chart",
    "create_category_bar_chart",
    "create_regional_bar_chart",
    "render_sidebar",
    "DashboardDataLoader",
    "render_html",
    "WorkspaceEngine"
]
