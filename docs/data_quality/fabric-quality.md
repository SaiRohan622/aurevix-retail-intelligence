# AUREVIX — Cloud Data Quality & Reconciliation Guarantees

## 1. Zero-Variance Reconciliation Thresholds
- **Gross Revenue Reconciliation:** Gold Parquet ($15,843,553.24) $\leftrightarrow$ Fabric Delta ($15,843,553.24) [Variance = $0.00].
- **Fact Row Count Reconciliation:** Gold Parquet (112,650 rows) $\leftrightarrow$ Fabric Delta (112,650 rows) [Variance = 0].
- **Order Count Reconciliation:** Gold Parquet (98,666 orders) $\leftrightarrow$ Fabric Delta (98,666 orders) [Variance = 0].

## 2. Integrity Rules Enforced
1. **Fact Grain Preservation:** Every line item uniquely identifiable by composite `(order_id, order_item_id)`.
2. **Referential Integrity:** 100% of foreign keys resolve to corresponding surrogate keys in dimension tables.
3. **Quarantine Traceability:** 29 invalid raw records quarantined during Silver ingestion remain safely isolated from Gold/Fabric layers.
