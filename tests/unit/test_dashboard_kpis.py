"""
AUREVIX — Unit Tests for Dashboard Analytical Aggregations
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from dashboard.components.data_loader import DashboardDataLoader


def test_monthly_sales_trend_aggregation():
    loader = DashboardDataLoader()
    df = loader.get_monthly_sales_trend()
    assert not df.empty
    assert "order_year_month" in df.columns
    assert "revenue" in df.columns


def test_category_performance_aggregation():
    loader = DashboardDataLoader()
    df = loader.get_category_performance()
    assert not df.empty
    assert "category" in df.columns
    assert "revenue" in df.columns


def test_regional_sales_aggregation():
    loader = DashboardDataLoader()
    df = loader.get_regional_sales()
    assert not df.empty
    assert "state" in df.columns
    assert "revenue" in df.columns
