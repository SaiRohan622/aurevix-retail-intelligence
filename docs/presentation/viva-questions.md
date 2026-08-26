# AUREVIX — Comprehensive Viva Questions & Model Answers

### Q1: Why did you choose a Medallion Architecture (Bronze -> Silver -> Gold)?
**Answer:** Medallion provides clear separation of concerns:
- **Bronze:** Immutable raw audit layer preserving exact source state.
- **Silver:** Cleaned, typed, standardized, and deduplicated business entities with a strict Data Quality Firewall.
- **Gold:** Kimball-style star schema optimized for dimensional queries, analytics marts, and executive BI.

### Q2: How do you handle duplicate events in the streaming pipeline?
**Answer:** We implement deterministic SHA-256 event hashing on natural order business keys combined with Spark Structured Streaming `withWatermark("event_timestamp", "10 minutes")` and `dropDuplicates(["event_id"])`.

### Q3: How do you handle schema changes and historical tracking?
**Answer:** We implement Slowly Changing Dimensions Type 2 (SCD2) on `dim_customer` with surrogate keys, `effective_start_date`, `effective_end_date`, and an `is_current` flag.

### Q4: How is financial data reconciled across all layers?
**Answer:** We enforce zero financial variance ($0.00) between Silver line items, Gold `fact_sales` ($15,843,553.24), PostgreSQL DW, and Microsoft Fabric Cloud Data Contracts.
