"""
AUREVIX — Spark Structured Streaming Engine
Consumes real-time order events from Apache Kafka, evaluates Streaming Data Quality,
applies 10-minute watermarking, enforces deterministic deduplication on event_id,
writes streaming Silver Parquet, and computes real-time business aggregations.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType, DecimalType, TimestampType, DateType, BooleanType
)

from src.config import settings
from src.common.logger import get_logger
from src.batch.ingest_raw import get_spark_session

logger = get_logger("aurevix.spark_streaming")

# Explicit Streaming Event Schema (Contract)
ORDER_EVENT_SCHEMA = StructType([
    StructField("event_id", StringType(), False),
    StructField("event_type", StringType(), False),
    StructField("event_timestamp", StringType(), False),
    StructField("order_id", StringType(), False),
    StructField("order_item_id", IntegerType(), False),
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("seller_id", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("freight_value", DoubleType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("order_status", StringType(), True),
    StructField("source", StringType(), True),
    StructField("schema_version", StringType(), True)
])


class SparkOrderStreamingProcessor:
    def __init__(
        self,
        streaming_silver_dir: Optional[Path] = None,
        streaming_gold_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
        monitoring_dir: Optional[Path] = None,
        checkpoint_dir: Optional[Path] = None,
        watermark_minutes: int = settings.WATERMARK_DELAY_MINUTES,
        spark: Optional[SparkSession] = None
    ):
        self.streaming_silver_dir = Path(streaming_silver_dir or (settings.DATA_DIR / "streaming" / "silver"))
        self.streaming_gold_dir = Path(streaming_gold_dir or (settings.DATA_DIR / "streaming" / "gold"))
        self.quarantine_dir = Path(quarantine_dir or (settings.QUARANTINE_DATA_PATH / "streaming"))
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)
        self.checkpoint_dir = Path(checkpoint_dir or settings.CHECKPOINT_PATH)
        self.watermark_minutes = watermark_minutes
        self._spark = spark
        self._owns_spark = spark is None
        self.batch_id = f"stream_batch_{int(time.time())}"

    @property
    def spark(self) -> SparkSession:
        if self._spark is None:
            self._spark = get_spark_session(app_name="AUREVIX-Spark-Structured-Streaming")
        return self._spark

    def parse_and_validate_stream(self, df_raw: DataFrame) -> Tuple[DataFrame, DataFrame, Dict[str, Any]]:
        """
        Parses JSON Kafka payloads, evaluates DQ rules, enforces watermarking & deduplication.
        Returns: (df_valid, df_quarantined, metrics)
        """
        # 1. Parse JSON payload
        df_parsed = (
            df_raw
            .withColumn("data", F.from_json(F.col("value").cast("string"), ORDER_EVENT_SCHEMA))
            .select("data.*")
            .withColumn("event_timestamp", F.to_timestamp(F.col("event_timestamp"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("price", F.col("price").cast(DecimalType(10, 2)))
            .withColumn("freight_value", F.col("freight_value").cast(DecimalType(10, 2)))
            .withColumn("total_amount", (F.col("price") + F.col("freight_value")).cast(DecimalType(10, 2)))
            .withColumn("order_year_month", F.date_format("event_timestamp", "yyyy-MM"))
            .withColumn("_ingested_at", F.current_timestamp())
        )

        input_count = df_parsed.count()

        # 2. Streaming Data Quality Rules
        dq_cond = (
            F.col("event_id").isNotNull() &
            F.col("order_id").isNotNull() &
            (F.col("order_item_id") >= 1) &
            (F.col("price") >= 0.0) &
            (F.col("freight_value") >= 0.0) &
            (F.col("quantity") >= 1) &
            (F.col("event_type") == "ORDER_ITEM_CREATED") &
            (F.col("schema_version") == "1.0")
        )

        df_valid_raw = df_parsed.filter(dq_cond)
        df_quarantined = df_parsed.filter(~dq_cond | dq_cond.isNull())

        # 3. Deterministic Deduplication on event_id
        # dropDuplicates on event_id prevents replayed duplicate events from inflating metrics
        df_dedup = df_valid_raw.dropDuplicates(["event_id"])

        # 4. Watermarking
        df_watermarked = df_dedup.withWatermark("event_timestamp", f"{self.watermark_minutes} minutes")

        valid_count = df_watermarked.count()
        quarantine_count = df_quarantined.count()
        duplicate_count = df_valid_raw.count() - valid_count

        metrics = {
            "input_events_count": input_count,
            "valid_events_count": valid_count,
            "quarantined_events_count": quarantine_count,
            "duplicate_events_filtered": duplicate_count,
            "watermark_delay_minutes": self.watermark_minutes
        }

        logger.info(
            f"Streaming DQ & Dedup: {valid_count} Valid, {duplicate_count} Duplicates Filtered, "
            f"{quarantine_count} Quarantined out of {input_count} events"
        )

        return df_watermarked, df_quarantined, metrics

    def compute_realtime_aggregations(self, df_valid: DataFrame) -> DataFrame:
        """Computes real-time windowed and summary KPIs on the streaming dataset."""
        df_agg = (
            df_valid
            .groupBy(
                F.window("event_timestamp", "10 minutes", "5 minutes"),
                "order_status"
            )
            .agg(
                F.count("event_id").alias("events_count"),
                F.countDistinct("order_id").alias("unique_orders_count"),
                F.sum("quantity").alias("total_units_sold"),
                F.sum("price").alias("total_product_revenue"),
                F.sum("freight_value").alias("total_freight_revenue"),
                F.sum("total_amount").alias("total_gross_revenue"),
                F.avg("price").alias("avg_item_price")
            )
            .withColumn("avg_order_value", F.round(F.col("total_gross_revenue") / F.col("unique_orders_count"), 2))
            .withColumn("_computed_at", F.current_timestamp())
        )
        return df_agg

    def process_micro_batch(self, df_batch: DataFrame, batch_id: int) -> Dict[str, Any]:
        """Executes deterministic micro-batch processing logic for streaming sinks."""
        start_time = time.time()
        logger.info(f"Processing streaming micro-batch {batch_id}")

        df_valid, df_quarantine, dq_metrics = self.parse_and_validate_stream(df_batch)

        # 1. Write Streaming Silver Parquet
        if df_valid.count() > 0:
            self.streaming_silver_dir.mkdir(parents=True, exist_ok=True)
            (
                df_valid
                .write
                .mode("append")
                .option("compression", "snappy")
                .partitionBy("order_year_month")
                .parquet(str(self.streaming_silver_dir))
            )

        # 2. Write Streaming Quarantine
        if df_quarantine.count() > 0:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            rejection_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            df_q_out = (
                df_quarantine
                .withColumn("_quarantine_id", F.expr("uuid()"))
                .withColumn("_rejection_date", F.lit(rejection_date))
                .withColumn("_rejection_reason", F.lit("DQ Rule Violation in Event Contract"))
            )
            (
                df_q_out
                .write
                .mode("append")
                .option("compression", "snappy")
                .partitionBy("_rejection_date")
                .parquet(str(self.quarantine_dir))
            )

        # 3. Compute and Write Real-Time Gold Aggregations
        df_agg = self.compute_realtime_aggregations(df_valid)
        if df_agg.count() > 0:
            self.streaming_gold_dir.mkdir(parents=True, exist_ok=True)
            (
                df_agg
                .write
                .mode("append")
                .option("compression", "snappy")
                .parquet(str(self.streaming_gold_dir))
            )

        duration = round(time.time() - start_time, 3)

        # 4. Generate Monitoring Report
        total_rev = float(df_valid.select(F.sum("total_amount")).collect()[0][0] or 0.0)
        total_orders = df_valid.select("order_id").distinct().count()
        total_units = int(df_valid.select(F.sum("quantity")).collect()[0][0] or 0)

        report = {
            "pipeline": "aurevix_spark_structured_streaming",
            "batch_id": f"batch_{batch_id}",
            "execution_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": duration,
            "metrics": dq_metrics,
            "realtime_kpis": {
                "total_gross_revenue": round(total_rev, 2),
                "total_unique_orders": total_orders,
                "total_units_sold": total_units,
                "average_order_value_aov": round(total_rev / total_orders, 2) if total_orders > 0 else 0.0
            },
            "status": "SUCCESS"
        }

        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        report_file = self.monitoring_dir / "streaming_metrics.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Micro-batch {batch_id} complete in {duration}s: {dq_metrics['valid_events_count']} valid events, ${round(total_rev, 2)} gross revenue")
        return report

    def close(self):
        if self._owns_spark and self._spark is not None:
            self._spark.stop()
            self._spark = None


if __name__ == "__main__":
    from kafka.producer.order_event_producer import OrderEventSimulator

    processor = SparkOrderStreamingProcessor()
    simulator = OrderEventSimulator()

    try:
        print("Generating 100 test events + 10 duplicate test injections...")
        events = simulator.generate_events_stream(total_events=100, inject_duplicates=10)
        df_raw = processor.spark.createDataFrame([(json.dumps(e),) for e in events], ["value"])
        report = processor.process_micro_batch(df_raw, batch_id=1)
        print(f"\nStreaming Pipeline Success: {report['metrics']['valid_events_count']} valid events processed (Duplicates Filtered: {report['metrics']['duplicate_events_filtered']})")
    finally:
        processor.close()
