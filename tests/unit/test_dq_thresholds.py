"""
AUREVIX — Unit Tests for Data Quality Threshold Enforcement
"""

import pytest
from airflow.dags.aurevix_batch_pipeline import task_silver_quality_validation


def test_silver_quality_threshold_enforcement():
    """Verify silver quality task passes within 1.0% quarantine threshold."""
    res = task_silver_quality_validation()
    assert res == "Silver quality passed"
