"""
AUREVIX — Unit Tests for Streaming Data Quality Firewall
Tests rejection of invalid schema events, negative prices, missing keys, and quarantine routing.
"""

import json
import pytest
from pyspark.sql import SparkSession

from src.batch.ingest_raw import get_spark_session
from src.streaming.spark_streaming_orders import SparkOrderStreamingProcessor


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Streaming-Quality-Tests")
    yield spark_session
    spark_session.stop()


def test_streaming_dq_firewall_validation(spark):
    """Verify that defective streaming records are quarantined and valid records pass."""
    processor = SparkOrderStreamingProcessor(spark=spark)

    events = [
        # Valid event
        {"event_id": "e1", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": "o1", "order_item_id": 1, "price": 100.0, "freight_value": 10.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"},
        # Invalid: Negative price
        {"event_id": "e2", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": "o2", "order_item_id": 1, "price": -50.0, "freight_value": 10.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"},
        # Invalid: Missing order_id
        {"event_id": "e3", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": None, "order_item_id": 1, "price": 20.0, "freight_value": 5.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"},
        # Invalid: Quantity < 1
        {"event_id": "e4", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": "o4", "order_item_id": 1, "price": 20.0, "freight_value": 5.0, "quantity": 0, "order_status": "delivered", "source": "test", "schema_version": "1.0"}
    ]

    df_raw = spark.createDataFrame([(json.dumps(e),) for e in events], ["value"])
    df_valid, df_quarantine, metrics = processor.parse_and_validate_stream(df_raw)

    assert df_valid.count() == 1
    assert df_quarantine.count() == 3
    assert metrics["valid_events_count"] == 1
    assert metrics["quarantined_events_count"] == 3
