# AUREVIX — Analytics Serving & Data Delivery Layer

```mermaid
flowchart LR
    subgraph Storage ["Gold Parquet / Snappy"]
        FS[(fact_sales)]
        DC[(dim_customer)]
        DP[(dim_product)]
    end

    subgraph Warehouse ["PostgreSQL 16 DW"]
        PG[(gold schema)]
        DBT[(analytics marts)]
    end

    subgraph Serving ["Application Layer"]
        ST[Streamlit Dashboard (Port 8501)]
        PB[Power BI / OneLake DirectLake]
    end

    Storage --> PG --> DBT --> ST & PB
```
