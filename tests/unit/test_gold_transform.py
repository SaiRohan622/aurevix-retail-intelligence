"""
AUREVIX — Unit Tests for PySpark Gold Layer (Star Schema + SCD2 Mechanics)
Tests calendar generation, surrogate key creation, fact measure formulas,
and controlled SCD Type 2 demonstration mechanics.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType, TimestampType, BooleanType
)

from src.batch.ingest_raw import get_spark_session
from src.batch.spark_silver_to_gold import SparkSilverToGoldPipeline


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Gold-Unit-Tests")
    yield spark_session
    spark_session.stop()


def test_dim_date_generation(spark, tmp_path):
    """Verify calendar dimension generated correctly with date keys and weekend flags (Hermetic tmp_path)."""
    pipeline = SparkSilverToGoldPipeline(gold_dir=tmp_path, spark=spark)
    dim_date = pipeline.build_dim_date(start_date="2018-01-01", end_date="2018-01-07")

    assert dim_date.count() == 7
    rows = {r.date_key: r for r in dim_date.collect()}

    # Check 2018-01-01 (Monday)
    assert 20180101 in rows
    assert rows[20180101].day_name == "Monday"
    assert rows[20180101].is_weekend is False
    assert rows[20180101].quarter == 1

    # Check 2018-01-06 (Saturday) and 2018-01-07 (Sunday)
    assert rows[20180106].is_weekend is True
    assert rows[20180107].is_weekend is True


def test_fact_sales_measure_formulas(spark):
    """Verify calculation of total item amount and gross values."""
    data = [
        (100.00, 15.50),
        (50.00, 0.00)
    ]
    df = spark.createDataFrame(data, ["price", "freight_value"])
    df_calc = (
        df
        .withColumn("order_item_quantity", F.lit(1))
        .withColumn("gross_item_value", F.col("price"))
        .withColumn("total_item_value", F.col("price") + F.col("freight_value"))
    )

    rows = df_calc.collect()
    assert rows[0].total_item_value == 115.50
    assert rows[0].order_item_quantity == 1
    assert rows[1].total_item_value == 50.00


def test_scd2_versioning_controlled_fixture(spark):
    """Verify controlled SCD Type 2 versioning transition logic."""
    v1_data = [
        ("cust_001", "user_123", "01310", "SP", True, "2016-01-01 00:00:00", "9999-12-31 23:59:59")
    ]
    schema = StructType([
        StructField("customer_id", StringType()),
        StructField("customer_unique_id", StringType()),
        StructField("zip_code", StringType()),
        StructField("state", StringType()),
        StructField("is_current", BooleanType()),
        StructField("effective_start_date", StringType()),
        StructField("effective_end_date", StringType())
    ])

    df_v1 = spark.createDataFrame(v1_data, schema)
    change_timestamp = "2018-06-01 00:00:00"

    df_closed_v1 = df_v1.withColumn("is_current", F.lit(False)).withColumn("effective_end_date", F.lit(change_timestamp))
    v2_data = [
        ("cust_001", "user_123", "22041", "RJ", True, change_timestamp, "9999-12-31 23:59:59")
    ]
    df_new_v2 = spark.createDataFrame(v2_data, schema)
    df_scd2 = df_closed_v1.union(df_new_v2)

    assert df_scd2.count() == 2
    records = df_scd2.collect()

    rec_v1 = [r for r in records if not r.is_current][0]
    assert rec_v1.state == "SP"
    assert rec_v1.effective_end_date == change_timestamp

    rec_v2 = [r for r in records if r.is_current][0]
    assert rec_v2.state == "RJ"
    assert rec_v2.effective_start_date == change_timestamp
