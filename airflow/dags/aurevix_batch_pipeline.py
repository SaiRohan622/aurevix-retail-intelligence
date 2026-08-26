"""
AUREVIX — Master Production Batch DAG
Orchestrates: Raw Validation -> Bronze -> Silver -> Gold -> PostgreSQL -> dbt Models -> dbt Tests.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.batch.ingest_raw import SparkRawToBronzeIngestor
from src.batch.spark_bronze_to_silver import SparkBronzeToSilverPipeline
from src.batch.spark_silver_to_gold import SparkSilverToGoldPipeline
from src.warehouse.postgres_loader import PostgresWarehouseLoader
from src.common.observability import PipelineObserver

# Default DAG Arguments
default_args = {
    "owner": "aurevix_data_platform",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def task_validate_raw_data(**kwargs):
    raw_path = Path("data/raw")
    expected_files = [
        "olist_orders_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_products_dataset.csv",
        "olist_customers_dataset.csv",
        "olist_order_payments_dataset.csv",
        "olist_order_reviews_dataset.csv",
        "olist_sellers_dataset.csv",
        "olist_geolocation_dataset.csv",
        "product_category_name_translation.csv"
    ]
    for fname in expected_files:
        f = raw_path / fname
        if not f.exists() or f.stat().st_size == 0:
            raise FileNotFoundError(f"Critical raw dataset missing or empty: {f}")
    return "Raw data validated successfully"


def task_bronze_ingestion(**kwargs):
    pipeline = SparkRawToBronzeIngestor()
    manifest = pipeline.run()
    pipeline.close()
    return manifest


def task_bronze_validation(**kwargs):
    manifest_path = Path("data/monitoring/ingestion_manifest.json")
    if not manifest_path.exists():
        manifest_path = Path("data/bronze/manifest.json")
    if not manifest_path.exists():
        raise FileNotFoundError("Bronze ingestion manifest missing")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("total_rows_ingested") != 1550922 and manifest.get("total_records") != 1550922:
        raise ValueError(f"Bronze row count mismatch: {manifest}")
    return "Bronze validation passed"


def task_silver_transformation(**kwargs):
    pipeline = SparkBronzeToSilverPipeline()
    report = pipeline.run()
    pipeline.close()
    return report


def task_silver_quality_validation(**kwargs):
    report_path = Path("data/monitoring/silver_quality_report.json")
    if not report_path.exists():
        raise FileNotFoundError("Silver quality report missing")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    q_rate = report.get("quarantine_rate_percentage", 0.0)
    if q_rate > 1.0:  # Max 1.0% quarantine threshold
        raise ValueError(f"Silver quarantine rate {q_rate}% exceeds max threshold 1.0%")
    return "Silver quality passed"


def task_gold_transformation(**kwargs):
    pipeline = SparkSilverToGoldPipeline()
    report = pipeline.run()
    pipeline.close()
    return report


def task_gold_reconciliation(**kwargs):
    report_path = Path("data/monitoring/gold_quality_report.json")
    if not report_path.exists():
        raise FileNotFoundError("Gold quality report missing")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    if report["revenue_reconciliation"]["reconciliation_status"] != "EXACT_MATCH":
        raise ValueError("Gold revenue reconciliation failed")
    if report["fact_sales"]["grain_violations_count"] > 0:
        raise ValueError("Fact sales grain violations detected")
    return "Gold reconciliation passed"


def task_load_postgres(**kwargs):
    loader = PostgresWarehouseLoader()
    return loader.load_gold_to_postgres()


def task_dbt_run(**kwargs):
    import subprocess
    dbt_bin = Path(sys.executable).parent / "dbt.exe"
    cmd = [str(dbt_bin), "run", "--project-dir", "dbt_aurevix", "--profiles-dir", "dbt_aurevix"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"dbt run failed: {res.stderr or res.stdout}")
    return "dbt models executed successfully"


def task_dbt_test(**kwargs):
    import subprocess
    dbt_bin = Path(sys.executable).parent / "dbt.exe"
    cmd = [str(dbt_bin), "test", "--project-dir", "dbt_aurevix", "--profiles-dir", "dbt_aurevix"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"dbt test failed: {res.stderr or res.stdout}")
    return "dbt tests passed successfully"
