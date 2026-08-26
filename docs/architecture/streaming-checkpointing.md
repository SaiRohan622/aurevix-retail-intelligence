# AUREVIX — Structured Streaming Checkpointing

## 1. Checkpoint Directory Strategy
- **Base Checkpoint Location:** `data/checkpoints/`
- **Subdirectories:**
  - `data/checkpoints/streaming_orders/`: Offsets and state storage for order events streaming ingestion
  - `data/checkpoints/realtime_metrics/`: State store for windowed aggregations

## 2. Fault Tolerance & Offset Management
- Checkpoints persist micro-batch commit logs and Kafka consumer group offsets (`startingOffsets`).
- When Spark Structured Streaming restarts, it reads the latest committed offset from `data/checkpoints/` and resumes exactly from where it stopped without duplicating stream outputs.
