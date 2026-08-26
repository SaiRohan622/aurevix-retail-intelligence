"""
AUREVIX — Unit Tests for Streaming Event Schema Contract
Tests JSON schema validation, deterministic SHA-256 event ID generation, and type casting.
"""

import json
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.batch.ingest_raw import get_spark_session
from src.streaming.spark_streaming_orders import ORDER_EVENT_SCHEMA
from src.streaming.order_event_producer import generate_deterministic_event_id


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Streaming-Schema-Tests")
    yield spark_session
    spark_session.stop()


def test_deterministic_event_id_generation():
    """Verify that same business key always generates identical event ID."""
    id1 = generate_deterministic_event_id("ord_12345", 1)
    id2 = generate_deterministic_event_id("ord_12345", 1)
    id3 = generate_deterministic_event_id("ord_12345", 2)

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 64


def test_json_streaming_schema_parsing(spark):
    """Verify that JSON string parses into structured DataFrame with expected types."""
    payload = {
        "event_id": "evt_001",
        "event_type": "ORDER_ITEM_CREATED",
        "event_timestamp": "2018-05-01 10:00:00",
        "order_id": "ord_001",
        "order_item_id": 1,
        "customer_id": "cust_001",
        "product_id": "prod_001",
        "seller_id": "sell_001",
        "price": 150.75,
        "freight_value": 25.50,
        "quantity": 1,
        "order_status": "delivered",
        "source": "olist_replay",
        "schema_version": "1.0"
    }

    df_raw = spark.createDataFrame([(json.dumps(payload),)], ["value"])
    df_parsed = (
        df_raw
        .withColumn("data", F.from_json(F.col("value"), ORDER_EVENT_SCHEMA))
        .select("data.*")
    )

    assert df_parsed.count() == 1
    row = df_parsed.collect()[0]
    assert row.event_id == "evt_001"
    assert row.price == 150.75
    assert row.order_item_id == 1
