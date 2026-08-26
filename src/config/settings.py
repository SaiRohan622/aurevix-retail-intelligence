"""
AUREVIX — Centralized Environment & Production Settings Management
Supports 'development', 'testing', and 'production' profiles with fail-fast validation.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class EnvironmentConfigError(Exception):
    """Raised when mandatory production environment configuration is missing or invalid."""
    pass


class ProductionSettings:
    """Centralized typed configuration engine for AUREVIX Platform."""

    def __init__(self):
        self.ENV: str = os.getenv("AUREVIX_ENV", "development").lower()
        self.IS_PRODUCTION: bool = self.ENV == "production"
        self.IS_TESTING: bool = self.ENV == "testing"

        # Workspace paths
        self.WORKSPACE_ROOT: Path = Path(os.getenv("AUREVIX_WORKSPACE", str(PROJECT_ROOT)))
        self.DATA_DIR: Path = Path(os.getenv("AUREVIX_DATA_DIR", str(self.WORKSPACE_ROOT / "data")))
        self.RAW_DATA_PATH: Path = Path(os.getenv("RAW_DATA_PATH", str(self.DATA_DIR / "raw")))
        self.BRONZE_DATA_PATH: Path = Path(os.getenv("BRONZE_DATA_PATH", str(self.DATA_DIR / "bronze")))
        self.SILVER_DATA_PATH: Path = Path(os.getenv("SILVER_DATA_PATH", str(self.DATA_DIR / "silver")))
        self.GOLD_DATA_PATH: Path = Path(os.getenv("GOLD_DATA_PATH", str(self.DATA_DIR / "gold")))
        self.QUARANTINE_DATA_PATH: Path = Path(os.getenv("QUARANTINE_DATA_PATH", str(self.DATA_DIR / "quarantine")))
        self.MONITORING_DATA_PATH: Path = Path(os.getenv("MONITORING_DATA_PATH", str(self.DATA_DIR / "monitoring")))
        self.CHECKPOINT_PATH: Path = Path(os.getenv("CHECKPOINT_PATH", str(self.DATA_DIR / "checkpoints")))

        # Schema & Versioning
        self.SCHEMA_VERSION: str = os.getenv("AUREVIX_SCHEMA_VERSION", "1.0.0")
        self.SOURCE_SYSTEM_BATCH: str = "OLIST_BATCH_RAW"
        self.SOURCE_SYSTEM_STREAM: str = "OLIST_STREAM_ORDERS"

        # Streaming & Watermark
        self.WATERMARK_DELAY_MINUTES: int = int(os.getenv("WATERMARK_DELAY_MINUTES", "10"))

        # PostgreSQL Warehouse Configuration
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aurevix_dw")
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "aurevix_admin")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "aurevix_secure_password_change_me")
        self.POSTGRES_SCHEMA_GOLD: str = os.getenv("POSTGRES_SCHEMA_GOLD", "gold")
        self.POSTGRES_SCHEMA_MONITORING: str = os.getenv("POSTGRES_SCHEMA_MONITORING", "monitoring")

        # Kafka Configuration
        self.KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.KAFKA_EXTERNAL_PORT: int = int(os.getenv("KAFKA_EXTERNAL_PORT", "29092"))
        self.KAFKA_TOPIC_ORDERS: str = os.getenv("KAFKA_TOPIC_ORDERS", "aurevix.retail.orders")
        self.KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "aurevix-stream-processors")

        # Spark Execution
        self.SPARK_APP_NAME: str = os.getenv("SPARK_APP_NAME", "AUREVIX-Engine")
        self.SPARK_MASTER: str = os.getenv("SPARK_MASTER", "local[*]")
        self.SPARK_DRIVER_MEMORY: str = os.getenv("SPARK_DRIVER_MEMORY", "2g")
        self.SPARK_EXECUTOR_MEMORY: str = os.getenv("SPARK_EXECUTOR_MEMORY", "2g")
        self.SPARK_SQL_SHUFFLE_PARTITIONS: int = int(os.getenv("SPARK_SQL_SHUFFLE_PARTITIONS", "4"))

        # SLA & Freshness Thresholds
        self.SLA_MAX_LATENCY_MINUTES: int = int(os.getenv("SLA_MAX_LATENCY_MINUTES", "60"))
        self.SLA_MAX_QUARANTINE_PERCENT: float = float(os.getenv("SLA_MAX_QUARANTINE_PERCENT", "1.0"))

        if self.IS_PRODUCTION:
            self.validate_production_requirements()

    def validate_production_requirements(self):
        """Fail-fast verification for production deployments."""
        if self.POSTGRES_PASSWORD == "aurevix_secure_password_change_me":
            raise EnvironmentConfigError("Default password detected! Production requires custom POSTGRES_PASSWORD.")
        if not self.RAW_DATA_PATH.exists():
            raise EnvironmentConfigError(f"Mandatory RAW_DATA_PATH missing: {self.RAW_DATA_PATH}")

    def get_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


# Singleton instance
settings = ProductionSettings()
