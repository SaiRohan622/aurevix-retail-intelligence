"""
AUREVIX — Unit Tests for Streaming Deterministic Deduplication & Watermarking
"""

import json
import pytest
from pyspark.sql import SparkSession

from src.batch.ingest_raw import get_spark_session
from src.streaming.spark_streaming_orders import SparkOrderStreamingProcessor


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Streaming-Dedup-Tests")
    yield spark_session
    spark_session.stop()


def test_deterministic_deduplication(spark):
    """Verify that duplicate event_ids are filtered and do not inflate metrics."""
    processor = SparkOrderStreamingProcessor(spark=spark)

    events = [
        {"event_id": "dup_1", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": "o1", "order_item_id": 1, "price": 100.0, "freight_value": 10.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"},
        {"event_id": "dup_1", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:00:00", "order_id": "o1", "order_item_id": 1, "price": 100.0, "freight_value": 10.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"},
        {"event_id": "unique_2", "event_type": "ORDER_ITEM_CREATED", "event_timestamp": "2018-05-01 10:05:00", "order_id": "o2", "order_item_id": 1, "price": 50.0, "freight_value": 5.0, "quantity": 1, "order_status": "delivered", "source": "test", "schema_version": "1.0"}
    ]

    df_raw = spark.createDataFrame([(json.dumps(e),) for e in events], ["value"])
    df_valid, df_quarantine, metrics = processor.parse_and_validate_stream(df_raw)

    assert df_valid.count() == 2
    assert metrics["duplicate_events_filtered"] == 1
