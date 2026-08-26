"""
AUREVIX — Raw Data Ingestion to Bronze Layer (PySpark Engine)
Reads raw Olist CSV datasets directly with Apache Spark, validates source schemas,
enriches records with technical audit metadata, writes Snappy-compressed Parquet,
and generates an expanded Ingestion Manifest for observability.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure HADOOP_HOME is configured for native Windows I/O
hadoop_dir = PROJECT_ROOT / "infrastructure" / "hadoop"
if hadoop_dir.exists():
    os.environ["HADOOP_HOME"] = str(hadoop_dir.resolve())
    os.environ["hadoop.home.dir"] = str(hadoop_dir.resolve())
    bin_dir = str((hadoop_dir / "bin").resolve())
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + ";" + os.environ.get("PATH", "")

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Import AUREVIX settings and schemas
from src.config import settings
from src.common.logger import get_logger
from src.common.schemas import (
    EXPECTED_SOURCE_SCHEMAS,
    RAW_FILE_TO_BRONZE_ENTITY,
    BRONZE_PARTITION_COLUMNS
)

logger = get_logger("aurevix.ingest_raw")


class RawDataIngestionError(Exception):
    """Custom exception for raw ingestion failures."""
    pass


def get_spark_session(app_name: str = "AUREVIX-Raw-to-Bronze-Ingestion") -> SparkSession:
    """Initializes and returns an optimized SparkSession for local batch ingestion."""
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    return (
        SparkSession.builder
        .appName(app_name)
        .master(settings.SPARK_MASTER)
        .config("spark.driver.memory", settings.SPARK_DRIVER_MEMORY)
        .config("spark.executor.memory", settings.SPARK_EXECUTOR_MEMORY)
        .config("spark.sql.shuffle.partitions", str(settings.SPARK_SQL_SHUFFLE_PARTITIONS))
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.python.worker.reuse", "true")
        .getOrCreate()
    )

class SparkRawToBronzeIngestor:
    def __init__(
        self,
        raw_dir: Optional[Path] = None,
        bronze_dir: Optional[Path] = None,
        monitoring_dir: Optional[Path] = None,
        schema_version: str = settings.SCHEMA_VERSION,
        source_system: str = settings.SOURCE_SYSTEM_BATCH,
        spark: Optional[SparkSession] = None
    ):
        self.raw_dir = Path(raw_dir or settings.RAW_DATA_PATH)
        self.bronze_dir = Path(bronze_dir or settings.BRONZE_DATA_PATH)
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)
        self.schema_version = schema_version
        self.source_system = source_system
        self._spark = spark
        self._owns_spark = spark is None

    @property
    def spark(self) -> SparkSession:
        if self._spark is None:
            self._spark = get_spark_session()
        return self._spark

    def validate_source_files_present(self) -> List[str]:
        """Verify all 9 expected source files exist in raw directory."""
        missing_files = []
        for filename in EXPECTED_SOURCE_SCHEMAS.keys():
            file_path = self.raw_dir / filename
            if not file_path.is_file():
                missing_files.append(filename)
        return missing_files

    def ingest_single_file(self, filename: str) -> Dict[str, Any]:
        """Ingest a single CSV file into Bronze Parquet using PySpark."""
        start_time = time.time()
        file_path = self.raw_dir / filename
        entity_name = RAW_FILE_TO_BRONZE_ENTITY[filename]
        expected_cols = EXPECTED_SOURCE_SCHEMAS[filename]

        logger.info(f"[PySpark] Ingesting {filename} -> {entity_name}")

        if not file_path.is_file():
            raise RawDataIngestionError(f"File does not exist: {file_path}")

        if file_path.stat().st_size == 0:
            raise RawDataIngestionError(f"File is empty (0 bytes): {file_path}")

        # Read CSV directly with Spark (Preserves source fidelity without Python-side conversion)
        df = (
            self.spark.read
            .option("header", "true")
            .option("inferSchema", "false")
            .option("multiLine", "true")
            .option("escape", "\"")
            .option("encoding", "UTF-8")
            .csv(str(file_path))
        )

        # Normalize column names: strip whitespace and BOM if present
        clean_columns = [col.strip().lstrip("\ufeff") for col in df.columns]
        for old_col, new_col in zip(df.columns, clean_columns):
            if old_col != new_col:
                df = df.withColumnRenamed(old_col, new_col)

        # Schema Validation
        actual_cols = df.columns
        missing_cols = [col for col in expected_cols if col not in actual_cols]
        if missing_cols:
            raise RawDataIngestionError(
                f"Schema mismatch in {filename}. Missing expected columns: {missing_cols}"
            )

        source_row_count = df.count()
        if source_row_count == 0:
            raise RawDataIngestionError(f"No data rows found in {filename}")

        # Ingestion audit metadata values
        ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ingestion_ym = datetime.now(timezone.utc).strftime("%Y-%m")

        # Inject Technical Metadata columns via PySpark
        df_bronze = (
            df
            .withColumn("_ingested_at", F.lit(ingested_at))
            .withColumn("_source_file", F.lit(filename))
            .withColumn("_source_system", F.lit(self.source_system))
            .withColumn("_schema_version", F.lit(self.schema_version))
            .withColumn("ingestion_year_month", F.lit(ingestion_ym))
        )

        # Write Parquet with Snappy Compression & Partitioning (Idempotent Overwrite)
        entity_dir = self.bronze_dir / entity_name
        partition_cols = BRONZE_PARTITION_COLUMNS.get(entity_name, [])

        writer = (
            df_bronze.write
            .mode("overwrite")
            .option("compression", "snappy")
        )

        if partition_cols:
            writer.partitionBy(*partition_cols).parquet(str(entity_dir))
        else:
            writer.parquet(str(entity_dir))

        # Validate written row count in Bronze Parquet
        df_written = self.spark.read.parquet(str(entity_dir))
        bronze_row_count = df_written.count()
        variance = bronze_row_count - source_row_count

        duration = round(time.time() - start_time, 3)
        logger.info(
            f"[PySpark] Successfully wrote {bronze_row_count:,} rows for {entity_name} "
            f"in {duration}s (variance: {variance})"
        )

        return {
            "entity": entity_name,
            "source_file": filename,
            "source_path": str(file_path),
            "output_path": str(entity_dir),
            "source_row_count": source_row_count,
            "bronze_row_count": bronze_row_count,
            "variance": variance,
            "column_count": len(df_bronze.columns),
            "partitioning": partition_cols if partition_cols else "unpartitioned",
            "compression": "SNAPPY",
            "ingested_at": ingested_at,
            "schema_version": self.schema_version,
            "duration_seconds": duration,
            "status": "SUCCESS"
        }

    def generate_manifest(
        self,
        manifest_data: List[Dict[str, Any]],
        total_duration: float
    ) -> Path:
        """Generate and write the comprehensive Ingestion Manifest for observability."""
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = self.monitoring_dir / "ingestion_manifest.json"

        total_source_rows = sum(item.get("source_row_count", 0) for item in manifest_data)
        total_bronze_rows = sum(item.get("bronze_row_count", 0) for item in manifest_data)

        manifest_payload = {
            "pipeline": "aurevix_raw_to_bronze_batch",
            "engine": f"PySpark {self.spark.version}",
            "status": "SUCCESS",
            "schema_version": self.schema_version,
            "execution_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": round(total_duration, 3),
            "total_entities_processed": len(manifest_data),
            "total_source_rows": total_source_rows,
            "total_rows_ingested": total_bronze_rows,
            "total_variance": total_bronze_rows - total_source_rows,
            "entities": manifest_data
        }

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_payload, f, indent=2)

        logger.info(f"Ingestion Manifest written to {manifest_file}")
        return manifest_file

    def run(self) -> Dict[str, Any]:
        """Execute full Bronze ingestion across all 9 source files using PySpark."""
        pipeline_start = time.time()
        missing = self.validate_source_files_present()
        if missing:
            logger.error(f"Missing {len(missing)} required raw files in {self.raw_dir}: {missing}")
            raise RawDataIngestionError(f"Missing required raw files: {missing}")

        results = []
        for filename in EXPECTED_SOURCE_SCHEMAS.keys():
            result = self.ingest_single_file(filename)
            results.append(result)

        total_duration = time.time() - pipeline_start
        manifest_path = self.generate_manifest(results, total_duration)

        return {
            "status": "SUCCESS",
            "manifest_path": str(manifest_path),
            "total_source_rows": sum(r["source_row_count"] for r in results),
            "total_bronze_rows": sum(r["bronze_row_count"] for r in results),
            "total_variance": sum(r["variance"] for r in results),
            "duration_seconds": round(total_duration, 3),
            "entities": results
        }

    def close(self):
        """Stop SparkSession if owned by this ingestor instance."""
        if self._owns_spark and self._spark is not None:
            self._spark.stop()
            self._spark = None


# Alias for backwards-compatibility
RawToBronzeIngestor = SparkRawToBronzeIngestor


if __name__ == "__main__":
    ingestor = SparkRawToBronzeIngestor()
    try:
        summary = ingestor.run()
        print(
            f"\n[PySpark Ingestion Complete] "
            f"Ingested {summary['total_bronze_rows']:,} rows across {len(summary['entities'])} tables "
            f"in {summary['duration_seconds']}s (Total Variance: {summary['total_variance']})"
        )
    except RawDataIngestionError as e:
        logger.error(f"Ingestion Failed: {e}")
        sys.exit(1)
    finally:
        ingestor.close()
