# AUREVIX — Dual Analytics & Serving Architecture

## 1. Distinct Separation of Roles

| Capability | Streamlit Operations Dashboard | Power BI Cloud Analytics |
| :--- | :--- | :--- |
| **Primary Audience** | Data Engineers, Platform Operators | Executive Leadership, Business Analysts |
| **Primary Focus** | Live operational health, pipeline telemetry, Kafka streams | Historical business trends, commercial analytics, forecasting |
| **Data Source** | PostgreSQL DW + Live JSON telemetry + Parquet fallback | Microsoft Fabric OneLake / DirectLake Semantic Model |
| **Latency Profile** | Real-time / Sub-second to 60s cache | Scheduled DirectLake / Hourly micro-batches |
| **Port / Hosting** | Port 8501 (Docker Container) | Power BI Service (Cloud Workspace) |
