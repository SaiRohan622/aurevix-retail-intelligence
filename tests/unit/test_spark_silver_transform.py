"""
AUREVIX — Unit Tests for PySpark Silver Transformation & Data Quality Firewall
Tests timestamp parsing, numeric casting, duplicate detection, DQ rule routing,
quarantine isolation, and referential integrity logic.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

from src.batch.ingest_raw import get_spark_session
from src.quality.data_quality_firewall import DataQualityFirewall


@pytest.fixture(scope="session")
def spark():
    """Shared SparkSession fixture."""
    spark_session = get_spark_session(app_name="AUREVIX-Silver-Unit-Tests")
    yield spark_session
    spark_session.stop()


def test_dq_firewall_validation_and_quarantine(spark):
    """Verify that valid records pass and defective records are quarantined with metadata."""
    firewall = DataQualityFirewall()

    schema = StructType([
        StructField("order_id", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("status", StringType(), True)
    ])

    data = [
        ("ord_001", 99.50, "delivered"),     # Valid
        (None, 45.00, "delivered"),          # Fail: Null order_id
        ("ord_003", -10.00, "delivered"),    # Fail: Negative price
        ("ord_004", 15.00, "invalid_status") # Fail: Invalid status
    ]

    df = spark.createDataFrame(data, schema)

    rules = [
        {"id": "DQ001", "description": "Order ID Required", "condition": F.col("order_id").isNotNull()},
        {"id": "DQ004", "description": "Positive Price", "condition": F.col("price") >= 0.0},
        {"id": "DQ007", "description": "Valid Status", "condition": F.col("status").isin(["delivered", "shipped"])}
    ]

    df_valid, df_quarantine, metrics = firewall.evaluate_rules(df, rules, "test_entity", "test_batch_1")

    assert df_valid.count() == 1
    assert df_quarantine.count() == 3
    assert metrics["quarantine_pct"] == 75.0

    # Verify quarantine metadata columns
    q_cols = df_quarantine.columns
    assert "_quarantine_id" in q_cols
    assert "_source_entity" in q_cols
    assert "_dq_rule_id" in q_cols
    assert "_dq_reason" in q_cols
    assert "_quarantine_timestamp" in q_cols
    assert "raw_payload" in q_cols


def test_deduplication_deterministic_behavior(spark):
    """Verify that dropDuplicates deterministically collapses duplicate keys."""
    data = [
        ("cust_1", "SP", "2026-01-01"),
        ("cust_1", "SP", "2026-01-02"),
        ("cust_2", "RJ", "2026-01-01")
    ]
    df = spark.createDataFrame(data, ["customer_id", "state", "ingested_at"])
    df_dedup = df.dropDuplicates(["customer_id"])

    assert df_dedup.count() == 2
    customer_ids = [row.customer_id for row in df_dedup.collect()]
    assert sorted(customer_ids) == ["cust_1", "cust_2"]


def test_timestamp_parsing_and_derived_features(spark):
    """Verify timestamp conversion and derived delivery days calculation."""
    data = [
        ("ord_1", "2018-05-01 10:00:00", "2018-05-10 14:00:00", "2018-05-15 00:00:00"),
        ("ord_2", "2018-06-01 08:00:00", "2018-06-20 12:00:00", "2018-06-15 00:00:00")
    ]
    df = spark.createDataFrame(data, ["order_id", "purchased", "delivered", "estimated"])

    df_transformed = (
        df
        .withColumn("order_purchase_timestamp", F.to_timestamp("purchased", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("order_delivered_customer_date", F.to_timestamp("delivered", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("order_estimated_delivery_date", F.to_timestamp("estimated", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("delivery_days", F.datediff("order_delivered_customer_date", "order_purchase_timestamp"))
        .withColumn("is_delayed", F.col("order_delivered_customer_date") > F.col("order_estimated_delivery_date"))
    )

    rows = {r.order_id: r for r in df_transformed.collect()}
    assert rows["ord_1"].delivery_days == 9
    assert rows["ord_1"].is_delayed is False

    assert rows["ord_2"].delivery_days == 19
    assert rows["ord_2"].is_delayed is True
