"""
AUREVIX — Unit Tests for Dashboard Data Loader & Fallback Query Engine
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from dashboard.components.data_loader import DashboardDataLoader


def test_dashboard_data_loader_initialization():
    loader = DashboardDataLoader()
    assert loader.gold_path.exists()
    assert loader.monitoring_path.exists()


def test_dashboard_executive_kpis_calculation():
    loader = DashboardDataLoader()
    kpis = loader.get_executive_kpis()
    assert "total_revenue" in kpis
    assert "total_orders" in kpis
    assert "average_order_value" in kpis
    assert kpis["total_revenue"] > 1000000.0
    assert kpis["total_orders"] > 50000


def test_dashboard_streaming_metrics_loader():
    loader = DashboardDataLoader()
    metrics = loader.get_streaming_metrics()
    assert "metrics" in metrics
    assert metrics["metrics"]["valid_events_count"] >= 100
