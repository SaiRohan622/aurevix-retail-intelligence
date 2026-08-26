# AUREVIX — Dashboard Architecture (Streamlit Enterprise)

## 1. Information Architecture & Page Layout

```mermaid
flowchart TD
    App[dashboard/app.py - Main Entrypoint]
    App --> P1[1. Executive Overview]
    App --> P2[2. Sales Intelligence]
    App --> P3[3. Customer Intelligence]
    App --> P4[4. Product Analytics]
    App --> P5[5. Regional Analytics]
    App --> P6[6. Real-Time Operations]
    App --> P7[7. Data Quality & Pipeline Health]
    App --> P8[8. Data Lineage & Architecture]
    App --> P9[9. System Information]

    DataLoader[(components/data_loader.py)]
    DataLoader --> PG[(PostgreSQL 16 DW)]
    DataLoader -. Fallback .-> Parquet[(data/gold/*.parquet)]

    DataLoader --> P1 & P2 & P3 & P4 & P5 & P6 & P7
```

## 2. Design System
- **Theme:** Enterprise Dark Mode (`#0b0f19` canvas, `#111827` cards, subtle glassmorphism borders).
- **Typography:** Inter for headings/metrics, JetBrains Mono for technical codes.
- **Latency & Caching:** `@st.cache_data(ttl=60)` with seamless PostgreSQL $ightarrow$ Local Parquet fallback.
