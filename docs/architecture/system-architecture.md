# AUREVIX - System Architecture

## 1. High-Level Architecture Overview

AUREVIX is an enterprise-grade hybrid Batch and Real-Time Streaming Data Engineering platform that ingests raw retail events, enforces a strict Data Quality Firewall, processes data across the Medallion layers (Bronze -> Silver -> Gold), models analytical dimensions and facts with dbt, orchestrates batch pipelines via Apache Airflow, computes real-time streaming metrics via Spark Structured Streaming, persists data in PostgreSQL and Microsoft Fabric, and visualizes KPIs through a high-performance Streamlit SaaS dashboard and Power BI.

```mermaid
flowchart TD
    subgraph INGESTION [Data Sources & Ingestion Layer]
        DS1[Olist Public Retail Dataset] -->|Batch Ingestion| B_ING[Batch Ingestor]
        SIM[Python Order Simulator] -->|Stream Events| KAFKA[(Apache Kafka
aurevix.retail.orders)]
    end

    subgraph STORAGE_BRONZE [Bronze Layer - Raw Storage]
        B_ING --> BRONZE_BATCH[(Bronze Batch Parquet
+ Ingestion Metadata)]
        KAFKA -->|Spark Structured Streaming| BRONZE_STREAM[(Bronze Stream Parquet)]
    end

    subgraph PROCESSING_SILVER [Silver Layer - PySpark & Data Quality Firewall]
        BRONZE_BATCH --> DQ_FIREWALL{Data Quality Firewall}
        BRONZE_STREAM --> DQ_FIREWALL
        DQ_FIREWALL -->|Violations / Corrupt| QUARANTINE[(Quarantine Parquet
+ Failure Reason)]
        DQ_FIREWALL -->|Validated & Deduplicated| SILVER_STORE[(Silver Parquet
Cleaned, Typed, Deduplicated)]
    end

    subgraph MODELING_GOLD [Gold Layer - dbt Transformations & Star Schema]
        SILVER_STORE --> DBT[dbt Core / dbt-postgres]
        DBT --> STG[Staging Views]
        STG --> INT[Intermediate Tables]
        INT --> GOLD_DIM_CUST[dim_customer - SCD Type 2]
        INT --> GOLD_DIM_PROD[dim_product]
        INT --> GOLD_DIM_DATE[dim_date]
        INT --> GOLD_DIM_LOC[dim_location]
        INT --> GOLD_FACT[fact_sales]
    end

    subgraph SERVING [Serving & Analytical Layer]
        GOLD_FACT --> PG[(PostgreSQL
aurevix_dw)]
        GOLD_DIM_CUST --> PG
        GOLD_DIM_PROD --> PG
        GOLD_DIM_DATE --> PG
        GOLD_DIM_LOC --> PG
        PG --> FABRIC[(Microsoft Fabric
OneLake / Lakehouse)]
    end

    subgraph ANALYTICS_UI [Presentation & Real-Time Analytics]
        PG --> ST_DASH[AUREVIX Executive Dashboard
Streamlit Enterprise SaaS]
        KAFKA --> STREAM_METRICS[Real-Time Streaming Engine
Orders/min, Revenue/min, Anomalies]
        STREAM_METRICS --> ST_DASH
        FABRIC --> POWER_BI[Power BI DirectLake / Semantic Model]
    end

    subgraph ORCHESTRATION [Orchestration & Governance]
        AIRFLOW[Apache Airflow DAG
aurevix_batch_pipeline] -.->|Orchestrates| B_ING
        AIRFLOW -.->|Orchestrates| DQ_FIREWALL
        AIRFLOW -.->|Orchestrates| DBT
        AIRFLOW -.->|Loads| PG
    end
```

---

## 2. Permanently Locked Technology Stack

| Layer | Locked Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python (3.12.x locked) | Pipeline logic, simulator, and ingestion scripts |
| **Transformation Language** | SQL | Declarative dimensional modeling and testing |
| **Batch Engine** | Apache Spark / PySpark | Distributed ETL, schema enforcement, deduplication |
| **Streaming Broker** | Apache Kafka | Real-time event broker (`aurevix.retail.orders`) |
| **Streaming Processing** | Spark Structured Streaming | Event-time windowing, watermarks, micro-batching |
| **Orchestration** | Apache Airflow | Batch workflow orchestration, retries, and SLAs |
| **Transformation-as-Code** | dbt (dbt-postgres) | Staging, intermediate, and marts models & tests |
| **Analytical Warehouse** | PostgreSQL | Local relational serving warehouse (`aurevix_dw`) |
| **Storage / Format** | Apache Parquet | Snappy-compressed columnar format |
| **Cloud Analytics** | Microsoft Fabric | OneLake Lakehouse architecture |
| **Business Intelligence** | Power BI | Primary enterprise semantic modeling |
| **Operational UI** | Streamlit | 9-page real-time executive dashboard |
| **Containerization** | Docker + Docker Compose | Isolated, reproducible multi-service execution |
| **Testing** | pytest + dbt tests | Unit, integration, and data quality tests |
| **CI/CD** | GitHub Actions | Automated lint, test, and container build pipelines |
| **Documentation** | Markdown + Mermaid | Architecture diagrams and runbooks |

---

## 3. Host and Deployment Architecture

To ensure cross-platform reproducibility and isolate dependencies (such as Java 17 for Spark and Python 3.12 for Airflow), AUREVIX uses a containerized deployment architecture:

```mermaid
flowchart TD
    HOST[Windows Host System
IDE, Workspace D:/Projects/aurevix, Git] --> DOCKER[Docker Desktop / WSL2 Engine]
    subgraph CONTAINERS [Linux Containerized Infrastructure]
        KAFKA_C[Apache Kafka Broker]
        SPARK_C[Apache Spark 3.5.1 / Java 17]
        PG_C[PostgreSQL 16 DW]
        AIRFLOW_C[Apache Airflow 2.8.3]
        STREAMLIT_C[Streamlit Dashboard UI]
    end
    DOCKER --> CONTAINERS
```
