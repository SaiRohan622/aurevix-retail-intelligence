"""
AUREVIX — Order Event Simulator & Kafka Producer Re-export
"""
from src.streaming.order_event_producer import OrderEventSimulator, generate_deterministic_event_id

__all__ = ["OrderEventSimulator", "generate_deterministic_event_id"]
