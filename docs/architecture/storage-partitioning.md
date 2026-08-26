# AUREVIX — Storage Partitioning Strategy

## 1. Partitioning Principles
Partitioning is vital for optimizing Parquet file size, avoiding the small-file problem, enabling efficient partition pruning, and accelerating PySpark / dbt query execution.

### Rules:
1. **Low-to-Medium Cardinality Only:** Never partition by high-cardinality keys like `customer_id`, `order_id`, or `product_id` (which creates millions of tiny files).
2. **Temporal Alignment:** Align partitions with natural analytical query patterns (e.g. monthly and daily bounds).

---

## 2. Layer Partitioning Matrix

| Layer / Table | Partition Key | Cardinality | Format & Compression | Target File Size |
| :--- | :--- | :--- | :--- | :--- |
| **Bronze Batch** | `ingestion_year_month` | ~25 partitions | Parquet / Snappy | 32 MB - 64 MB |
| **Bronze Stream** | `ingestion_date` (`YYYY-MM-DD`) | Daily (~30 active) | Parquet / Snappy | 16 MB - 32 MB |
| **Silver Orders** | `order_year_month` (`YYYY-MM`) | 25 partitions (2016-2018)| Parquet / Snappy | 64 MB - 128 MB |
| **Silver Order Items** | `order_year_month` (`YYYY-MM`) | 25 partitions | Parquet / Snappy | 64 MB - 128 MB |
| **Silver Products** | *Unpartitioned* (Dimension) | Single table (~32k rows) | Parquet / Snappy | ~5 MB |
| **Silver Customers** | `customer_state` (Optional) | 27 Brazilian states | Parquet / Snappy | ~10 MB |
| **Gold `fact_sales`** | `order_date_key` (Range) / `year_month` | 25 partitions | PostgreSQL Tables / Parquet | 64 MB - 128 MB |
| **Quarantine** | `rejection_date` (`YYYY-MM-DD`) | Daily partitions | Parquet / Snappy | Dynamic |

---

## 3. Query Predicate Pushdown
By partitioning Silver and Gold tables on `order_year_month`, Spark and PostgreSQL filter entire directory trees during date-bounded range scans, dramatically reducing disk I/O and query latency.
