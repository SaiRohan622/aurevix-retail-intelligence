"""
AUREVIX — Integration Tests for PySpark Gold Star Schema Pipeline
Executes pipeline against Silver Parquet datasets, verifies fact_sales grain (112,650 rows),
dimensions, referential integrity, Snappy Parquet compression, revenue reconciliation, and idempotency.
"""

import os
import json
from pathlib import Path
import pytest
import pyarrow.parquet as pq

from src.batch.ingest_raw import get_spark_session
from src.batch.spark_silver_to_gold import SparkSilverToGoldPipeline


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Gold-Integration-Tests")
    yield spark_session
    spark_session.stop()


def test_gold_pipeline_execution(spark):
    """Verify that the complete Silver -> Gold Star Schema pipeline runs successfully."""
    pipeline = SparkSilverToGoldPipeline(spark=spark)
    report = pipeline.run()

    assert report["pipeline"] == "aurevix_silver_to_gold_batch"
    assert report["status"] == "SUCCESS"
    assert report["fact_sales"]["fact_row_count"] == 112650
    assert report["fact_sales"]["grain_violations_count"] == 0
    assert report["fact_sales"]["orphan_customer_keys"] == 0
    assert report["fact_sales"]["orphan_product_keys"] == 0
    assert report["fact_sales"]["orphan_seller_keys"] == 0

    # Revenue Reconciliation Verification
    recon = report["revenue_reconciliation"]
    assert recon["reconciliation_status"] == "EXACT_MATCH"
    assert abs(recon["revenue_variance"]) < 0.01

    # Report verification
    report_file = Path("data/monitoring/gold_quality_report.json")
    assert report_file.is_file()


def test_gold_parquet_snappy_compression(spark):
    """Verify all generated Gold tables are Snappy-compressed Parquet datasets."""
    gold_dir = Path("data/gold")
    entities = [
        "dim_date",
        "dim_location",
        "dim_customer",
        "dim_product",
        "dim_seller",
        "fact_sales"
    ]

    for ent in entities:
        ent_path = gold_dir / ent
        assert ent_path.is_dir(), f"Missing Gold directory: {ent_path}"
        parquet_files = list(ent_path.rglob("*.parquet"))
        assert len(parquet_files) >= 1, f"No Parquet files found in {ent_path}"

        meta = pq.read_metadata(parquet_files[0])
        compression = meta.row_group(0).column(0).compression
        assert compression == "SNAPPY", f"Expected SNAPPY compression in {ent}, found {compression}"


def test_gold_idempotency(spark):
    """Verify running Gold pipeline twice produces identical fact rows and dimensions."""
    pipeline = SparkSilverToGoldPipeline(spark=spark)
    res1 = pipeline.run()
    res2 = pipeline.run()

    assert res1["fact_sales"]["fact_row_count"] == res2["fact_sales"]["fact_row_count"] == 112650
    assert res1["fact_sales"]["total_gross_revenue"] == res2["fact_sales"]["total_gross_revenue"]
    assert res1["dimensions"] == res2["dimensions"]
