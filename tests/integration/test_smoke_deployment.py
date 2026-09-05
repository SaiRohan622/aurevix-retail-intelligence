"""
AUREVIX — Deployment Smoke Test
Validates end-to-end availability of configuration, health probes,
lakehouse Parquet tables, and dashboard queries.
"""

import pytest
from src.config.settings import settings
from src.common.health import PlatformHealthChecker
from dashboard.components.data_loader import DashboardDataLoader

lakehouse_ready = (settings.GOLD_DATA_PATH / "fact_sales").exists()


@pytest.mark.skipif(not lakehouse_ready, reason="Lakehouse partitions not present in CI environment")
def test_deployment_smoke_sequence():
    # 1. Config Check
    assert settings.RAW_DATA_PATH.exists()
    assert settings.GOLD_DATA_PATH.exists()

    # 2. Health & Readiness Probe Check
    checker = PlatformHealthChecker()
    liveness = checker.check_liveness()
    assert liveness["status"] == "UP"

    readiness = checker.check_readiness()
    assert readiness["ready"] is True

    # 3. Data Serving & KPI Verification
    loader = DashboardDataLoader()
    kpis = loader.get_executive_kpis()
    assert kpis["total_revenue"] == 15843553.24
    assert kpis["units_sold"] == 112650
    assert kpis["total_orders"] == 98666
