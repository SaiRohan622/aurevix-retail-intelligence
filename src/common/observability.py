"""
AUREVIX — Pipeline Observability & Run Tracking Module
Captures structured execution metrics, durations, row counts, DQ statuses,
and appends immutable audit records to data/monitoring/pipeline_run_history.jsonl.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.config import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.observability")


class PipelineObserver:
    def __init__(self, monitoring_dir: Optional[Path] = None):
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.monitoring_dir / "pipeline_run_history.jsonl"

    def record_run(
        self,
        pipeline_name: str,
        run_id: str,
        start_time: float,
        end_time: float,
        status: str,
        rows_processed: int = 0,
        rows_failed: int = 0,
        rows_quarantined: int = 0,
        data_quality_status: str = "PASSED",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        duration = round(end_time - start_time, 3)
        start_iso = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat()

        record = {
            "pipeline_name": pipeline_name,
            "run_id": run_id,
            "start_time": start_iso,
            "end_time": end_iso,
            "duration_seconds": duration,
            "status": status,
            "rows_processed": rows_processed,
            "rows_failed": rows_failed,
            "rows_quarantined": rows_quarantined,
            "data_quality_status": data_quality_status,
            "error_message": error_message,
            "metadata": metadata or {}
        }

        # Append-only write to JSONL
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"Recorded pipeline run [{pipeline_name}] ({run_id}) -> {status} in {duration}s")
        return record
