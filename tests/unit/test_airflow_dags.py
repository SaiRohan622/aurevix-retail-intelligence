"""
AUREVIX — Unit Tests for Airflow DAG Structure & Task Definitions
"""

import pytest
from pathlib import Path
from airflow.dags.aurevix_batch_pipeline import default_args, task_validate_raw_data, task_bronze_validation
from airflow.dags.aurevix_streaming_monitor import task_check_streaming_health
from airflow.dags.aurevix_data_quality import task_audit_all_layers


def test_airflow_batch_dag_defaults():
    """Verify DAG configuration defaults (retries, retry_delay)."""
    assert default_args["owner"] == "aurevix_data_platform"
    assert default_args["retries"] == 2
    assert default_args["retry_delay"].total_seconds() == 300


def test_airflow_raw_validation_task():
    """Verify task_validate_raw_data passes against existing raw files."""
    res = task_validate_raw_data()
    assert res == "Raw data validated successfully"


def test_airflow_bronze_validation_task():
    """Verify task_bronze_validation parses manifest.json."""
    res = task_bronze_validation()
    assert res == "Bronze validation passed"


def test_airflow_data_quality_audit_task():
    """Verify task_audit_all_layers generates quality audit report."""
    rep = task_audit_all_layers()
    assert rep["audit_pipeline"] == "aurevix_airflow_data_quality"
    assert rep["overall_quality_status"] == "PASSED"
