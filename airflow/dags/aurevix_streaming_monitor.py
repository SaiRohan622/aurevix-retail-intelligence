"""
AUREVIX — Streaming Pipeline Health & Latency Monitor DAG
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.logger import get_logger

logger = get_logger("aurevix.airflow_streaming_monitor")

default_args = {
    "owner": "aurevix_data_platform",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def task_check_streaming_health(**kwargs):
    metrics_path = Path("data/monitoring/streaming_metrics.json")
    if not metrics_path.exists():
        logger.warning("No active streaming metrics report found.")
        return {"status": "NO_RUN_DATA"}

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    exec_time_str = metrics.get("execution_timestamp")
    if exec_time_str:
        exec_dt = datetime.fromisoformat(exec_time_str.replace("Z", "+00:00"))
        latency_mins = (datetime.now(timezone.utc) - exec_dt).total_seconds() / 60.0
    else:
        latency_mins = 0.0

    valid_events = metrics.get("metrics", {}).get("valid_events_count", 0)
    logger.info(f"Streaming Health: {valid_events} valid events processed. Latency: {round(latency_mins, 1)}m")
    return {"status": "HEALTHY", "latency_minutes": round(latency_mins, 1), "valid_events": valid_events}
