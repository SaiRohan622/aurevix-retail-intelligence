"""
AUREVIX — Unit Tests for Data Freshness & SLA Evaluation
"""

from pathlib import Path
import pytest
from src.common.freshness import DataFreshnessMonitor


@pytest.mark.skipif(
    not (Path("data/monitoring/ingestion_manifest.json").exists() or Path("data/monitoring/silver_quality_report.json").exists()),
    reason="Monitoring reports not present in environment",
)
def test_data_freshness_evaluation():
    monitor = DataFreshnessMonitor()
    res = monitor.compute_layer_freshness()
    assert "evaluation_timestamp" in res
    assert "sla_tier" in res
    assert res["sla_tier"] in ["GREEN", "YELLOW", "RED"]
    assert "bronze" in res["layers"] or "silver" in res["layers"] or "gold" in res["layers"]
