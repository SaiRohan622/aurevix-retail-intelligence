# AUREVIX — Phase 1 Test Plan & Acceptance Matrix

This document defines the automated testing suite and verification plan for all upcoming pipeline phases (Phase 2 to Phase 18).

---

## 1. Test Suite Categories

### Category A: Schema & Data Integrity Tests
- **Target:** Verify Bronze, Silver, and Gold schemas match documented data types and nullability constraints.
- **Tools:** `pytest`, PySpark DataFrame schema assertions, `dbt test`.
- **Key Assertions:**
  - `fact_sales.sales_key` is NOT NULL and unique.
  - `dim_customer.current_flag` contains only boolean values.
  - `dim_date.date_key` correctly matches format `YYYYMMDD`.

### Category B: Data Quality Firewall Tests
- **Target:** Ensure DQ rules (`DQ001` to `DQ012`) correctly divert defective payloads to Quarantine.
- **Test Scenarios:**
  - Negative prices -> Diverted to Quarantine with `DQ004`.
  - Null `order_id` -> Diverted to Quarantine with `DQ001`.
  - Corrupt timestamp -> Diverted to Quarantine with `DQ008`.
  - Valid records -> Passed directly to Silver Parquet.

### Category C: Deduplication & Idempotency Tests
- **Target:** Ensure duplicate arrivals do not produce duplicate facts.
- **Test Scenarios:**
  - Replaying 100 identical order records -> Resulting row count in Silver/Gold increases by 0.
  - Re-running Airflow pipeline -> Gold record count remains unchanged.

### Category D: Slowly Changing Dimension (SCD2) Tests
- **Target:** Verify customer profile updates generate new version rows while closing old versions.
- **Test Scenarios:**
  - Customer moves from SP to RJ -> Old record has `current_flag = FALSE`, `valid_to = change_date`; New record has `current_flag = TRUE`, `valid_to = 9999-12-31`.

### Category E: Streaming Event & Watermark Tests
- **Target:** Verify Kafka order events deserialize correctly and late arrivals within watermark are processed.
- **Test Scenarios:**
  - Event with SHA-256 `event_id` passes schema validator.
  - Out-of-order event arriving within 10-minute watermark is included in window aggregation.
