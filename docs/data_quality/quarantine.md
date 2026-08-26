# AUREVIX — Quarantine Subsystem Specification

## 1. Purpose
The Quarantine Subsystem provides automated isolation for defective or outlier records failing Data Quality Firewall rules. No defective records are silently discarded or allowed into downstream analytical models.

## 2. Storage & Partitioning
- **Path:** `data/quarantine/<entity_name>/`
- **Format:** Apache Parquet (Snappy Compressed)
- **Partitioning:** `_rejection_date=YYYY-MM-DD`

## 3. Quarantine Audit Metadata
Every quarantined record includes:
- `_quarantine_id`: Unique UUID generated for each rejected row
- `_source_entity`: Name of the source Silver model being evaluated
- `_dq_rule_id`: Semicolon-separated list of violated rule codes (e.g. `DQ004; DQ011`)
- `_dq_reason`: Human-readable explanation of why the record failed
- `_quarantine_timestamp`: UTC ISO-8601 timestamp of quarantine execution
- `_rejection_date`: UTC Date (`YYYY-MM-DD`) for storage partitioning
- `_processing_batch_id`: Batch identifier of the pipeline run
- `raw_payload`: Serialized JSON payload containing the complete raw record
