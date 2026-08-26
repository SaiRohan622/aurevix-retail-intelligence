"""
AUREVIX — Order Event Simulator & Kafka Producer
Replays historical Olist orders from Gold fact_sales as real-time JSON streaming events.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.config import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.order_producer")


def generate_deterministic_event_id(order_id: str, order_item_id: int) -> str:
    """Generates a deterministic SHA-256 event ID based on business key."""
    raw_key = f"{order_id}||{order_item_id}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class OrderEventSimulator:
    """Simulator that streams Gold fact_sales records as JSON order events."""

    def __init__(
        self,
        gold_dir: Optional[Path] = None,
        topic: str = "aurevix.retail.order-events",
        bootstrap_servers: Optional[str] = None
    ):
        self.gold_dir = Path(gold_dir or settings.GOLD_DATA_PATH)
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer = None

    def get_kafka_producer(self):
        """Lazy initialization of KafkaProducer."""
        if self._producer is None:
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    retries=3,
                    request_timeout_ms=5000
                )
                logger.info(f"Connected to Kafka broker at {self.bootstrap_servers}")
            except Exception as e:
                logger.warning(f"Kafka unavailable at {self.bootstrap_servers}: {e}")
                self._producer = None
        return self._producer

    def load_replay_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads transactional records from Gold fact_sales Parquet for simulation."""
        import pyarrow.parquet as pq

        fact_sales_dir = self.gold_dir / "fact_sales"
        if not fact_sales_dir.exists():
            raise FileNotFoundError(f"Gold fact_sales not found at {fact_sales_dir}")

        parquet_files = list(fact_sales_dir.rglob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No Parquet files found in {fact_sales_dir}")

        events = []
        for pfile in parquet_files:
            table = pq.read_table(pfile)
            pylist = table.to_pylist()
            for row in pylist:
                order_id = str(row["order_id"])
                item_id = int(row["order_item_id"])
                event_id = generate_deterministic_event_id(order_id, item_id)

                ts = row.get("order_purchase_timestamp")
                if isinstance(ts, datetime):
                    event_ts = ts.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    event_ts = str(ts or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

                event = {
                    "event_id": event_id,
                    "event_type": "ORDER_ITEM_CREATED",
                    "event_timestamp": event_ts,
                    "order_id": order_id,
                    "order_item_id": item_id,
                    "customer_id": str(row.get("customer_key") or "cust_unknown")[:32],
                    "product_id": str(row.get("product_key") or "prod_unknown")[:32],
                    "seller_id": str(row.get("seller_key") or "seller_unknown")[:32],
                    "price": float(row.get("item_price") or 0.0),
                    "freight_value": float(row.get("freight_value") or 0.0),
                    "quantity": int(row.get("order_item_quantity") or 1),
                    "order_status": str(row.get("order_status") or "delivered"),
                    "source": "olist_replay",
                    "schema_version": "1.0"
                }
                events.append(event)
                if limit and len(events) >= limit:
                    return events
        return events

    def generate_events_stream(
        self,
        total_events: int = 100,
        inject_duplicates: int = 10
    ) -> List[Dict[str, Any]]:
        """Generates a controlled list of events including intentional duplicates for testing."""
        base_events = self.load_replay_records(limit=total_events)
        all_events = list(base_events)

        if inject_duplicates > 0 and base_events:
            for i in range(min(inject_duplicates, len(base_events))):
                dup_event = dict(base_events[i])
                all_events.append(dup_event)

        logger.info(
            f"Generated {len(all_events)} simulation events ({len(base_events)} unique + "
            f"{len(all_events) - len(base_events)} duplicate test injections)"
        )
        return all_events

    def publish_events(
        self,
        events: List[Dict[str, Any]],
        events_per_second: Optional[float] = None
    ) -> Dict[str, Any]:
        """Publishes events to Kafka topic or returns simulation payload."""
        producer = self.get_kafka_producer()
        published_count = 0
        failed_count = 0
        start_time = time.time()

        for event in events:
            key = event["order_id"]
            if producer:
                try:
                    producer.send(self.topic, key=key, value=event)
                    published_count += 1
                except Exception as e:
                    logger.error(f"Failed to publish event {event['event_id']}: {e}")
                    failed_count += 1
            else:
                published_count += 1

            if events_per_second and events_per_second > 0:
                time.sleep(1.0 / events_per_second)

        if producer:
            producer.flush()

        duration = round(time.time() - start_time, 3)
        rate = round(published_count / duration, 2) if duration > 0 else published_count

        summary = {
            "status": "SUCCESS" if failed_count == 0 else "PARTIAL_FAILURE",
            "topic": self.topic,
            "total_events": len(events),
            "published_count": published_count,
            "failed_count": failed_count,
            "duration_seconds": duration,
            "events_per_second": rate
        }
        logger.info(f"Published {published_count} events to {self.topic} in {duration}s ({rate} events/s)")
        return summary
