"""
AUREVIX — End-to-End Integration Test for Real-Time Streaming Pipeline
"""

import os
import json
from pathlib import Path
import pytest
import pyarrow.parquet as pq

from src.batch.ingest_raw import get_spark_session
from src.streaming.spark_streaming_orders import SparkOrderStreamingProcessor
from src.streaming.order_event_producer import OrderEventSimulator


@pytest.fixture(scope="session")
def spark():
    spark_session = get_spark_session(app_name="AUREVIX-Streaming-Integration-Tests")
    yield spark_session
    spark_session.stop()


@pytest.mark.skipif(
    not (Path("data/gold/fact_sales").exists() and any(Path("data/gold/fact_sales").glob("*.parquet"))),
    reason="Gold fact_sales Parquet data not materialized in environment",
)
def test_streaming_end_to_end_replay_and_aggregation(spark):
    """Verify end-to-end event replay, parsing, deduplication, and streaming Silver write."""
    simulator = OrderEventSimulator()
    processor = SparkOrderStreamingProcessor(spark=spark)

    # Generate 100 events + 10 intentional duplicate test events
    events = simulator.generate_events_stream(total_events=100, inject_duplicates=10)
    assert len(events) == 110

    # Process through Spark Streaming Micro-batch Engine
    df_raw = spark.createDataFrame([(json.dumps(e),) for e in events], ["value"])
    report = processor.process_micro_batch(df_raw, batch_id=101)

    assert report["pipeline"] == "aurevix_spark_structured_streaming"
    assert report["status"] == "SUCCESS"
    assert report["metrics"]["input_events_count"] == 110
    assert report["metrics"]["valid_events_count"] == 100
    assert report["metrics"]["duplicate_events_filtered"] == 10
    assert report["metrics"]["quarantined_events_count"] == 0

    # Verify Streaming Silver Output
    silver_stream_dir = Path("data/streaming/silver")
    assert silver_stream_dir.is_dir()
    parquet_files = list(silver_stream_dir.rglob("*.parquet"))
    assert len(parquet_files) >= 1

    meta = pq.read_metadata(parquet_files[0])
    assert meta.row_group(0).column(0).compression == "SNAPPY"

    # Verify Monitoring Report
    report_file = Path("data/monitoring/streaming_metrics.json")
    assert report_file.is_file()
