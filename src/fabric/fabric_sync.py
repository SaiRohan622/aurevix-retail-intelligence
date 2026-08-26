"""
AUREVIX — Microsoft Fabric Lakehouse Synchronization & Data Contract Exporter
Prepares and synchronizes Gold Star Schema tables and analytics marts into
OneLake/Fabric Delta Lakehouse format. Supports local mock/validation and cloud export.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pyarrow.parquet as pq
import pyarrow as pa

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.fabric_sync")

# Formal Fabric Cloud Data Contract
FABRIC_DATA_CONTRACT = {
    "lakehouse_name": "AUREVIX_Lakehouse",
    "schema_version": "1.0.0",
    "tables": {
        "fact_sales": {
            "source": "gold/fact_sales",
            "grain": ["order_id", "order_item_id"],
            "primary_key": ["sales_fact_key"],
            "foreign_keys": {
                "customer_key": "dim_customer.customer_key",
                "product_key": "dim_product.product_key",
                "seller_key": "dim_seller.seller_key",
                "order_date_key": "dim_date.date_key",
                "location_key": "dim_location.location_key"
            },
            "required_columns": [
                "sales_fact_key", "order_id", "order_item_id", "customer_key",
                "product_key", "seller_key", "order_date_key", "location_key",
                "order_purchase_timestamp", "order_status", "item_price",
                "freight_value", "total_item_value"
            ]
        },
        "dim_customer": {
            "source": "gold/dim_customer",
            "grain": ["customer_key"],
            "primary_key": ["customer_key"],
            "required_columns": [
                "customer_key", "customer_id", "customer_unique_id",
                "customer_city", "customer_state", "is_current",
                "effective_start_date", "effective_end_date"
            ]
        },
        "dim_product": {
            "source": "gold/dim_product",
            "grain": ["product_key"],
            "primary_key": ["product_key"],
            "required_columns": [
                "product_key", "product_id", "product_category_name",
                "product_category_name_english", "product_volume_cm3"
            ]
        },
        "dim_seller": {
            "source": "gold/dim_seller",
            "grain": ["seller_key"],
            "primary_key": ["seller_key"],
            "required_columns": [
                "seller_key", "seller_id", "seller_city", "seller_state", "location_key"
            ]
        },
        "dim_date": {
            "source": "gold/dim_date",
            "grain": ["date_key"],
            "primary_key": ["date_key"],
            "required_columns": [
                "date_key", "full_date", "year", "quarter", "month_number",
                "month_name", "day_of_month", "day_name", "is_weekend"
            ]
        },
        "dim_location": {
            "source": "gold/dim_location",
            "grain": ["location_key"],
            "primary_key": ["location_key"],
            "required_columns": [
                "location_key", "zip_code_prefix", "city", "state", "latitude", "longitude"
            ]
        }
    }
}


class FabricLakehouseExporter:
    """Handles validation, metadata extraction, and export package generation for Microsoft Fabric."""

    def __init__(self, gold_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.gold_dir = Path(gold_dir or settings.GOLD_DATA_PATH)
        self.output_dir = Path(output_dir or settings.DATA_DIR / "fabric_export")
        self.contract = FABRIC_DATA_CONTRACT

    def validate_gold_contract_compatibility(self) -> Dict[str, Any]:
        """Validates that local Gold Parquet files satisfy all Fabric Data Contract requirements."""
        results = {"status": "VALID", "tables": {}, "validation_errors": []}

        for table_name, spec in self.contract["tables"].items():
            table_path = self.gold_dir / table_name
            if not table_path.exists():
                err = f"Table {table_name} missing in Gold directory: {table_path}"
                results["validation_errors"].append(err)
                results["tables"][table_name] = {"status": "MISSING", "error": err}
                continue

            parquet_files = list(table_path.rglob("*.parquet"))
            if not parquet_files:
                err = f"No Parquet files found for table {table_name} in {table_path}"
                results["validation_errors"].append(err)
                results["tables"][table_name] = {"status": "EMPTY", "error": err}
                continue

            schema = pq.read_schema(parquet_files[0])
            available_cols = set(schema.names)
            missing_cols = [col for col in spec["required_columns"] if col not in available_cols]

            if missing_cols:
                err = f"Table {table_name} missing contract columns: {missing_cols}"
                results["validation_errors"].append(err)
                results["tables"][table_name] = {"status": "SCHEMA_MISMATCH", "missing_columns": missing_cols}
            else:
                results["tables"][table_name] = {
                    "status": "COMPATIBLE",
                    "file_count": len(parquet_files),
                    "column_count": len(schema.names)
                }

        if results["validation_errors"]:
            results["status"] = "INVALID"

        return results

    def compute_contract_metrics(self) -> Dict[str, Any]:
        """Computes exact reconciliation metrics for Fabric cloud staging."""
        fact_path = self.gold_dir / "fact_sales"
        if not fact_path.exists():
            return {"status": "ERROR", "message": "fact_sales not found"}

        fact_table = pq.read_table(fact_path)
        df_fact = fact_table.to_pandas()

        total_revenue = round(float(df_fact["total_item_value"].sum()), 2)
        total_freight = round(float(df_fact["freight_value"].sum()), 2)
        total_items = int(len(df_fact))
        total_orders = int(df_fact["order_id"].nunique())
        aov = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

        return {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "target_lakehouse": self.contract["lakehouse_name"],
            "metrics": {
                "total_gross_revenue": total_revenue,
                "total_freight_revenue": total_freight,
                "total_fact_rows": total_items,
                "total_distinct_orders": total_orders,
                "average_order_value": aov
            }
        }

    def generate_fabric_manifest(self) -> Path:
        """Generates a OneLake-compliant deployment manifest."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.output_dir / "fabric_manifest.json"

        compat = self.validate_gold_contract_compatibility()
        metrics = self.compute_contract_metrics()

        manifest_data = {
            "platform": "AUREVIX",
            "target_lakehouse": self.contract["lakehouse_name"],
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "contract": self.contract,
            "compatibility": compat,
            "reconciled_metrics": metrics
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Generated Fabric Lakehouse deployment manifest at {manifest_path}")
        return manifest_path
