"""
AUREVIX — Data Freshness & Pipeline SLA Monitor
Tracks data latency across Bronze, Silver, Gold, and Streaming layers
and computes SLA compliance statuses (GREEN / YELLOW / RED).
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.freshness")


class DataFreshnessMonitor:
    def __init__(self, monitoring_dir: Optional[Path] = None):
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)

    def compute_layer_freshness(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        results = {}

        # 1. Bronze Freshness
        manifest = self.monitoring_dir / "ingestion_manifest.json"
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ts_str = data.get("execution_timestamp")
                if ts_str:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    latency_mins = (now - dt).total_seconds() / 60.0
                    results["bronze"] = {
                        "last_ingested_at": ts_str,
                        "latency_minutes": round(latency_mins, 1),
                        "status": "FRESH" if latency_mins <= settings.SLA_MAX_LATENCY_MINUTES else "STALE"
                    }
            except Exception:
                pass

        # 2. Silver Quality Freshness
        silver_rep = self.monitoring_dir / "silver_quality_report.json"
        if silver_rep.exists():
            try:
                with open(silver_rep, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ts_str = data.get("execution_timestamp")
                if ts_str:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    latency_mins = (now - dt).total_seconds() / 60.0
                    results["silver"] = {
                        "last_transformed_at": ts_str,
                        "quarantine_rate": data.get("quarantine_rate_percentage", 0.0),
                        "latency_minutes": round(latency_mins, 1),
                        "status": "FRESH" if latency_mins <= settings.SLA_MAX_LATENCY_MINUTES else "STALE"
                    }
            except Exception:
                pass

        # 3. Gold Star Schema Freshness
        gold_rep = self.monitoring_dir / "gold_quality_report.json"
        if gold_rep.exists():
            try:
                with open(gold_rep, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ts_str = data.get("execution_timestamp")
                if ts_str:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    latency_mins = (now - dt).total_seconds() / 60.0
                    results["gold"] = {
                        "last_reconciled_at": ts_str,
                        "reconciliation": data.get("revenue_reconciliation", {}).get("reconciliation_status", "UNKNOWN"),
                        "latency_minutes": round(latency_mins, 1),
                        "status": "FRESH" if latency_mins <= settings.SLA_MAX_LATENCY_MINUTES else "STALE"
                    }
            except Exception:
                pass

        # 4. Overall SLA Status Determination
        sla_tier = "GREEN"
        for layer, info in results.items():
            if info.get("status") == "STALE":
                sla_tier = "YELLOW"

        return {
            "evaluation_timestamp": now.isoformat(),
            "sla_tier": sla_tier,
            "max_sla_latency_threshold_minutes": settings.SLA_MAX_LATENCY_MINUTES,
            "layers": results
        }
