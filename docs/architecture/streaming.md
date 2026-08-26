# AUREVIX — Real-Time Streaming Architecture

## 1. Technical Honesty & Simulation Model
The historical Olist dataset is static and does not originate from a live streaming message broker. To evaluate real-time retail streaming processing truthfully:

> **Architecture Principle:** Historical Olist records from Gold `fact_sales` are replayed through a controlled Python Event Simulator (`kafka/producer/order_event_producer.py`) as synthetic live retail JSON events into Apache Kafka, which are then processed continuously by Spark Structured Streaming.

---

## 2. Streaming Data Flow Architecture (Mermaid)

```mermaid
flowchart TD
    subgraph GoldFact ["1. Historical Data Foundation"]
        G1[(Gold fact_sales Parquet)]
    end

    subgraph Simulation ["2. Event Simulator & Broker"]
        SIM[Python Order Simulator\nkafka/producer/order_event_producer.py]
        KAFKA{{Apache Kafka\naurevix.retail.order-events}}
    end

    subgraph StreamingEngine ["3. Spark Structured Streaming Engine"]
        SSS[Spark Structured Streaming Consumer]
        DQ{Streaming DQ Firewall\nDQ001-DQ012}
        WM[Watermarking\n10 Minutes Delay]
        DEDUP[Deterministic Deduplication\nSHA-256 event_id]
        AGG[Real-Time Aggregations\n10-Min Tumbling Windows]
    end

    subgraph StreamingSinks ["4. Storage & Serving Layer"]
        SSILVER[(data/streaming/silver/\nSnappy Parquet)]
        SQUAR[(data/quarantine/streaming/\nSnappy Parquet)]
        SGOLD[(data/streaming/gold/\nSnappy Parquet)]
        PG[(PostgreSQL 16\nrealtime_sales_metrics)]
    end

    G1 -->|Replay Batch| SIM
    SIM -->|JSON Events| KAFKA
    KAFKA -->|Continuous Ingestion| SSS
    SSS --> DQ
    DQ -->|Violations| SQUAR
    DQ -->|Valid Events| WM
    WM --> DEDUP
    DEDUP --> SSILVER
    DEDUP --> AGG
    AGG --> SGOLD
    AGG --> PG
```
