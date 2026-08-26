"""
AUREVIX — Unit Tests for Pipeline Observability & Run Tracking
"""

import json
import time
from pathlib import Path
from src.common.observability import PipelineObserver


def test_pipeline_observer_run_record(tmp_path):
    """Verify that observer logs runs to immutable JSONL history."""
    observer = PipelineObserver(monitoring_dir=tmp_path)
    t_start = time.time()
    time.sleep(0.01)
    t_end = time.time()

    record = observer.record_run(
        pipeline_name="unit_test_pipeline",
        run_id="test_run_001",
        start_time=t_start,
        end_time=t_end,
        status="SUCCESS",
        rows_processed=5000,
        data_quality_status="PASSED"
    )

    assert record["pipeline_name"] == "unit_test_pipeline"
    assert record["status"] == "SUCCESS"
    assert record["rows_processed"] == 5000
    assert record["duration_seconds"] >= 0.01

    history_file = tmp_path / "pipeline_run_history.jsonl"
    assert history_file.is_file()

    with open(history_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert len(lines) == 1
    assert lines[0]["run_id"] == "test_run_001"
