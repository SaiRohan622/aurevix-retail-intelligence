"""
AUREVIX — Integration Test for Airflow Master Batch DAG Task Sequence & Idempotency
"""

import pytest
from airflow.dags.aurevix_batch_pipeline import (
    task_validate_raw_data,
    task_bronze_validation,
    task_silver_quality_validation,
    task_gold_reconciliation,
    task_load_postgres
)


from pathlib import Path

raw_has_data = (Path("data/raw") / "olist_orders_dataset.csv").exists()


@pytest.mark.skipif(not raw_has_data, reason="Raw Olist CSV datasets not present in CI environment")
def test_airflow_batch_task_sequence_execution():
    """Verify sequential execution of all validation and loading tasks in Airflow DAG."""
    r1 = task_validate_raw_data()
    assert "successfully" in r1

    r2 = task_bronze_validation()
    assert "passed" in r2

    r3 = task_silver_quality_validation()
    assert "passed" in r3

    r4 = task_gold_reconciliation()
    assert "passed" in r4

    r5 = task_load_postgres()
    assert r5["status"] == "SUCCESS"
    assert r5["total_rows_loaded"] == 268983  # 1827 + 19019 + 99441 + 32951 + 3095 + 112650
