"""
AUREVIX — Unit Tests for Phase 2 Raw to Bronze Ingestion (PySpark Engine)
Tests SparkSession initialization, schema validation, ingestion metadata,
Parquet output, partitioning, idempotency, and missing/empty file exception handling.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from pyspark.sql import SparkSession
from src.batch.ingest_raw import SparkRawToBronzeIngestor, RawDataIngestionError, get_spark_session
from src.common.schemas import EXPECTED_SOURCE_SCHEMAS, RAW_FILE_TO_BRONZE_ENTITY


@pytest.fixture(scope="session")
def spark():
    """Shared SparkSession fixture for the test session."""
    spark_session = get_spark_session(app_name="AUREVIX-Unit-Tests")
    yield spark_session
    spark_session.stop()


@pytest.fixture
def temp_environment(spark):
    """Creates temporary raw, bronze, and monitoring directories with sample data."""
    temp_dir = tempfile.mkdtemp()
    raw_dir = Path(temp_dir) / "raw"
    bronze_dir = Path(temp_dir) / "bronze"
    monitoring_dir = Path(temp_dir) / "monitoring"

    raw_dir.mkdir(parents=True)
    bronze_dir.mkdir(parents=True)
    monitoring_dir.mkdir(parents=True)

    # Copy test fixtures from tests/data to temp raw dir
    fixture_dir = Path("tests/data")
    for f in fixture_dir.glob("*.csv"):
        shutil.copy(f, raw_dir / f.name)

    yield {
        "raw_dir": raw_dir,
        "bronze_dir": bronze_dir,
        "monitoring_dir": monitoring_dir,
        "spark": spark
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_spark_session_creation(spark):
    """Verify SparkSession is active and configured correctly."""
    assert spark is not None
    assert isinstance(spark, SparkSession)
    df = spark.createDataFrame([(1, "test")], ["id", "val"])
    assert df.count() == 1


def test_expected_source_files(temp_environment):
    """Verify all expected 9 source files are detected in fixture environment."""
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    missing = ingestor.validate_source_files_present()
    assert missing == [], f"Expected 0 missing files, found: {missing}"


def test_bronze_metadata_and_parquet_output(temp_environment):
    """Verify that Bronze Parquet output contains required metadata audit columns via Spark."""
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    result = ingestor.ingest_single_file("olist_products_dataset.csv")
    assert result["status"] == "SUCCESS"
    assert result["source_row_count"] == 4
    assert result["bronze_row_count"] == 4
    assert result["variance"] == 0

    # Read back parquet file using Spark and verify columns
    df_read = temp_environment["spark"].read.parquet(result["output_path"])
    col_names = df_read.columns

    assert "_ingested_at" in col_names
    assert "_source_file" in col_names
    assert "_source_system" in col_names
    assert "_schema_version" in col_names
    assert "ingestion_year_month" in col_names


def test_partitioning(temp_environment):
    """Verify that partitioned tables write directory-based partitions."""
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    result = ingestor.ingest_single_file("olist_orders_dataset.csv")
    assert result["status"] == "SUCCESS"

    orders_bronze_dir = temp_environment["bronze_dir"] / "bronze_orders"
    assert orders_bronze_dir.is_dir()
    partition_dirs = list(orders_bronze_dir.glob("ingestion_year_month=*"))
    assert len(partition_dirs) >= 1


def test_ingestion_idempotency(temp_environment):
    """Verify that re-running ingestion overwrites/replaces without row inflation."""
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    res1 = ingestor.ingest_single_file("olist_customers_dataset.csv")
    res2 = ingestor.ingest_single_file("olist_customers_dataset.csv")

    assert res1["bronze_row_count"] == res2["bronze_row_count"] == 4
    df_read = temp_environment["spark"].read.parquet(res2["output_path"])
    assert df_read.count() == 4


def test_missing_file_failure(temp_environment):
    """Verify that missing required files raises RawDataIngestionError."""
    os.remove(temp_environment["raw_dir"] / "olist_orders_dataset.csv")
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    with pytest.raises(RawDataIngestionError, match="Missing required raw files"):
        ingestor.run()


def test_empty_file_failure(temp_environment):
    """Verify that an empty (0 byte) CSV raises RawDataIngestionError."""
    empty_file = temp_environment["raw_dir"] / "empty_test.csv"
    empty_file.touch()
    RAW_FILE_TO_BRONZE_ENTITY["empty_test.csv"] = "bronze_empty_test"
    EXPECTED_SOURCE_SCHEMAS["empty_test.csv"] = ["order_id"]

    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    with pytest.raises(RawDataIngestionError, match="File is empty"):
        ingestor.ingest_single_file("empty_test.csv")

    # Clean up test registration
    RAW_FILE_TO_BRONZE_ENTITY.pop("empty_test.csv", None)
    EXPECTED_SOURCE_SCHEMAS.pop("empty_test.csv", None)


def test_full_manifest_generation(temp_environment):
    """Verify that full run creates an enhanced Ingestion Manifest with Spark metadata."""
    ingestor = SparkRawToBronzeIngestor(
        raw_dir=temp_environment["raw_dir"],
        bronze_dir=temp_environment["bronze_dir"],
        monitoring_dir=temp_environment["monitoring_dir"],
        spark=temp_environment["spark"]
    )
    summary = ingestor.run()
    assert summary["status"] == "SUCCESS"
    assert summary["total_bronze_rows"] > 0
    assert summary["total_variance"] == 0

    manifest_file = temp_environment["monitoring_dir"] / "ingestion_manifest.json"
    assert manifest_file.is_file()
