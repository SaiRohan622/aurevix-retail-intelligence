# AUREVIX — Platform Observability & SLA Monitoring

## 1. Telemetry Datastores
- **Pipeline Run History:** `data/monitoring/pipeline_run_history.jsonl`
- **Data Freshness Monitor:** Evaluates `data_latency_minutes` across Bronze, Silver, Gold, and Streaming.
- **SLA Alert Tiers:**
  - `GREEN`: Pipeline latency <= 60 minutes, quarantine rate < 1.0%.
  - `YELLOW`: Pipeline latency > 60 minutes.
  - `RED`: Pipeline failure or data unavailability.
