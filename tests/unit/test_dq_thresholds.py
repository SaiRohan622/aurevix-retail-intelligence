"""
AUREVIX — Unit Tests for Data Quality Threshold Enforcement
"""

from pathlib import Path
import pytest
from airflow.dags.aurevix_batch_pipeline import task_silver_quality_validation


@pytest.mark.skipif(
    not Path("data/monitoring/silver_quality_report.json").exists(),
    reason="Silver quality report not present in environment",
)
def test_silver_quality_threshold_enforcement():
    """Verify silver quality task passes within 1.0% quarantine threshold."""
    res = task_silver_quality_validation()
    assert res == "Silver quality passed"
