# AUREVIX — Streaming Data Quality Firewall

## 1. Streaming Rules Enforcement

| Rule ID | Field Evaluated | Validation Condition | Rejection Action |
| :--- | :--- | :--- | :--- |
| **DQ001** | `event_id` | `event_id IS NOT NULL` | Route to `data/quarantine/streaming/` |
| **DQ002** | `order_id` | `order_id IS NOT NULL` | Route to `data/quarantine/streaming/` |
| **DQ003** | `order_item_id` | `order_item_id >= 1` | Route to `data/quarantine/streaming/` |
| **DQ004** | `price` | `price >= 0.00` | Route to `data/quarantine/streaming/` |
| **DQ005** | `freight_value` | `freight_value >= 0.00` | Route to `data/quarantine/streaming/` |
| **DQ006** | `quantity` | `quantity >= 1` | Route to `data/quarantine/streaming/` |
| **DQ007** | `event_type` | `event_type == 'ORDER_ITEM_CREATED'` | Route to `data/quarantine/streaming/` |
| **DQ008** | `schema_version` | `schema_version == '1.0'` | Route to `data/quarantine/streaming/` |
| **DQ012** | `event_id` | Deterministic deduplication across watermark window | Filter duplicates silently from metrics |
