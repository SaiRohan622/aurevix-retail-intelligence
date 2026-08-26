# AUREVIX — Final Project Demonstration Flow (Viva / Presentation)

## Act 1: The Problem & Architecture (2 mins)
- Introduce Olist Brazilian e-commerce dataset: 1.55M records across 9 source entities.
- Explain enterprise challenge: Reconciling high-velocity streaming events with rigorous financial batch accounting.
- Highlight locked architecture: PySpark 4.2.0, Kafka, Airflow, dbt, PostgreSQL 16, Streamlit, Microsoft Fabric.

## Act 2: Medallion Lakehouse & DQ Firewall (3 mins)
- Demonstrate Bronze raw ingestion (0 byte variance).
- Demonstrate Silver Data Quality Firewall (29 quarantined payments out of 103,886; 0.0019% quarantine rate).
- Showcase Gold Kimball Star Schema: `fact_sales` (112,650 rows, $15,843,553.24 revenue) with SCD2 customer versioning.

## Act 3: Real-Time Streaming Pipeline (3 mins)
- Run `order_event_producer.py` and `spark_streaming_orders.py`.
- Show deterministic SHA-256 event ID generation.
- Demonstrate 10-minute watermark deduplication filtering 10 duplicate injections.

## Act 4: Orchestration & Transformation-as-Code (2 mins)
- Showcase Apache Airflow DAGs (`aurevix_batch_pipeline`, `aurevix_streaming_monitor`, `aurevix_data_quality`).
- Showcase dbt-postgres marts and automated assertions.

## Act 5: Enterprise Operations Dashboard & Cloud BI (3 mins)
- Open Streamlit Dashboard (`http://localhost:8501`).
- Walk through Executive Overview, Real-Time Streaming Pulse, and Platform Health.
- Demonstrate Microsoft Fabric Lakehouse OneLake contract & Power BI DirectLake semantic model.

## Act 6: 100% Automated Test Suite & CI/CD (2 mins)
- Show Pytest execution: **56 / 56 PASSED (100%)**.
- Highlight GitHub Actions CI/CD workflows and Docker containerization.
