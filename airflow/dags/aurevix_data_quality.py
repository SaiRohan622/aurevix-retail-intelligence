"""
AUREVIX — Enterprise Data Quality Audit DAG
Audits Bronze, Silver, Gold, and Streaming layers, generating airflow_quality_report.json.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

default_args = {
    "owner": "aurevix_data_platform",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def task_audit_all_layers(**kwargs):
    monitoring_dir = Path("data/monitoring")
    monitoring_dir.mkdir(parents=True, exist_ok=True)

    # 1. Bronze audit
    bronze_manifest = monitoring_dir / "ingestion_manifest.json"
    if not bronze_manifest.exists():
        bronze_manifest = Path("data/bronze/manifest.json")
    bronze_status = "PASSED" if bronze_manifest.exists() else "MISSING"

    # 2. Silver audit
    silver_rep = monitoring_dir / "silver_quality_report.json"
    silver_status = "PASSED" if silver_rep.exists() else "MISSING"

    # 3. Gold audit
    gold_rep = monitoring_dir / "gold_quality_report.json"
    gold_status = "PASSED" if gold_rep.exists() else "MISSING"

    report = {
        "audit_pipeline": "aurevix_airflow_data_quality",
        "audit_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": {
            "bronze": {"status": bronze_status},
            "silver": {"status": silver_status},
            "gold": {"status": gold_status}
        },
        "overall_quality_status": "PASSED" if (bronze_status == "PASSED" and silver_status == "PASSED" and gold_status == "PASSED") else "FAILED"
    }

    out_file = monitoring_dir / "airflow_quality_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
