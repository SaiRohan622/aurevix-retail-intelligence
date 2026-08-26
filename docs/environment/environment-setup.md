# AUREVIX — Environment Configuration & Setup Guide

## 1. Verified Runtime Compatibility Matrix

| Runtime Layer | Verified Version | Execution Context | Notes |
| :--- | :--- | :--- | :--- |
| **Host Python** | `3.14.4` | Windows Host CLI | General host utilities and launcher |
| **AUREVIX Project Python** | `3.12.10` | Isolated Virtual Environment (`.venv`) | **PERMANENTLY LOCKED** project runtime for PySpark, Airflow & dbt |
| **PySpark Engine** | `4.2.0` | `.venv` | Configured with `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` synced |
| **Java JDK Runtime** | `25.0.1 LTS` / `17+` | Local Host & Docker Containers | Vector incubator enabled, Windows winutils configured |
| **Hadoop Windows I/O** | `3.3.6 Binaries` | `infrastructure/hadoop/bin` | Native `winutils.exe` and `hadoop.dll` for Parquet I/O |
| **Docker Engine** | `29.7.2` / `Compose v5.4.0`| Windows Host (WSL2 Engine) | Containerized services runtime (Phase 14) |
| **Database Storage** | PostgreSQL `16` | Port `5432` | Relational Analytical Warehouse |
| **Streaming Broker** | Apache Kafka `3.7` | Ports `9092` / `29092` | Real-time event bus (`aurevix.retail.orders`) |

---

## 2. Python 3.12 Virtual Environment Activation

To activate the isolated Python 3.12 runtime:

```powershell
cd D:\Projects\aurevix
# Activate existing Python 3.12 virtual environment
.\.venv\Scripts\Activate.ps1

# Verify version
python --version
# Expected Output: Python 3.12.10
```

---

## 3. Host Memory Budget & Configuration
- **Host Physical RAM:** 16 GB Total
- **Windows OS / IDE Reservation:** ~6.0 GB RAM
- **Docker / PySpark Local Budget:** ~8.0 GB - 10.0 GB RAM
  - `spark.driver.memory=2g`
  - `spark.executor.memory=2g`
  - `spark.sql.shuffle.partitions=4`
