"""
AUREVIX — Order Event Simulation Script CLI
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.streaming.order_event_producer import OrderEventSimulator


def main():
    parser = argparse.ArgumentParser(description="AUREVIX Order Event Simulator")
    parser.add_argument("--count", type=int, default=100, help="Number of unique events to replay")
    parser.add_argument("--duplicates", type=int, default=10, help="Number of duplicate events to inject")
    parser.add_argument("--rate", type=float, default=50.0, help="Events per second replay rate")
    parser.add_argument("--topic", type=str, default="aurevix.retail.order-events", help="Kafka topic")
    args = parser.parse_args()

    simulator = OrderEventSimulator(topic=args.topic)
    events = simulator.generate_events_stream(total_events=args.count, inject_duplicates=args.duplicates)
    summary = simulator.publish_events(events, events_per_second=args.rate)
    print(f"\nSimulation Complete: {summary['published_count']} events processed in {summary['duration_seconds']}s")


if __name__ == "__main__":
    main()
