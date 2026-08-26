"""
AUREVIX — Platform Health & Readiness Probe Engine
Provides unified liveness and readiness diagnostic checks for PostgreSQL, Kafka,
Parquet Lakehouse storage, and Airflow orchestration metadata.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.health")


class PlatformHealthChecker:
    """Unified diagnostic probe engine for platform liveness and readiness."""

    def __init__(self):
        self.settings = settings

    def check_liveness(self) -> Dict[str, Any]:
        """Liveness probe: verifies the host process and Python runtime are responsive."""
        return {
            "status": "UP",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime": {
                "python_version": sys.version.split()[0],
                "environment": self.settings.ENV
            }
        }

    def check_postgres(self) -> Dict[str, Any]:
        """Validates PostgreSQL database connection and query response time."""
        start = time.time()
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.settings.POSTGRES_HOST,
                port=self.settings.POSTGRES_PORT,
                dbname=self.settings.POSTGRES_DB,
                user=self.settings.POSTGRES_USER,
                password=self.settings.POSTGRES_PASSWORD,
                connect_timeout=2
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            conn.close()
            latency = round((time.time() - start) * 1000, 2)
            return {"status": "HEALTHY", "latency_ms": latency, "target": f"{self.settings.POSTGRES_HOST}:{self.settings.POSTGRES_PORT}"}
        except Exception as e:
            return {"status": "UNHEALTHY", "error": str(e), "target": f"{self.settings.POSTGRES_HOST}:{self.settings.POSTGRES_PORT}"}

    def check_kafka(self) -> Dict[str, Any]:
        """Validates Apache Kafka broker responsiveness."""
        start = time.time()
        try:
            from kafka import KafkaAdminClient
            client = KafkaAdminClient(
                bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                request_timeout_ms=2000
            )
            topics = client.list_topics()
            client.close()
            latency = round((time.time() - start) * 1000, 2)
            return {"status": "HEALTHY", "latency_ms": latency, "available_topics": len(topics)}
        except Exception as e:
            return {"status": "UNAVAILABLE", "error": str(e), "target": self.settings.KAFKA_BOOTSTRAP_SERVERS}

    def check_storage_lakehouse(self) -> Dict[str, Any]:
        """Verifies lakehouse Parquet partitions exist and are readable."""
        gold_fact = self.settings.GOLD_DATA_PATH / "fact_sales"
        silver_orders = self.settings.SILVER_DATA_PATH / "silver_orders"
        bronze_orders = self.settings.BRONZE_DATA_PATH / "bronze_orders"

        exists_gold = gold_fact.exists()
        exists_silver = silver_orders.exists()
        exists_bronze = bronze_orders.exists()

        all_ready = exists_gold and exists_silver and exists_bronze
        return {
            "status": "HEALTHY" if all_ready else "DEGRADED",
            "gold_ready": exists_gold,
            "silver_ready": exists_silver,
            "bronze_ready": exists_bronze
        }

    def check_readiness(self) -> Dict[str, Any]:
        """Readiness probe: validates all operational dependencies for serving traffic."""
        liveness = self.check_liveness()
        storage = self.check_storage_lakehouse()
        pg = self.check_postgres()
        kafka = self.check_kafka()

        # Platform is ready if core analytical data and lakehouse storage are functional
        is_ready = storage["status"] == "HEALTHY"

        return {
            "ready": is_ready,
            "status": "READY" if is_ready else "NOT_READY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "liveness": liveness,
                "storage": storage,
                "postgres": pg,
                "kafka": kafka
            }
        }
