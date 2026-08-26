"""
AUREVIX — Integration Test for Microsoft Fabric Lakehouse Reconciliation
Reconciles Gold Parquet data against the formal Fabric Cloud Data Contract.
"""

import json
from pathlib import Path
from src.fabric.fabric_sync import FabricLakehouseExporter


def test_gold_to_fabric_contract_compatibility():
    exporter = FabricLakehouseExporter()
    compat = exporter.validate_gold_contract_compatibility()

    assert compat["status"] == "VALID"
    assert len(compat["validation_errors"]) == 0
    for table_name in ["fact_sales", "dim_customer", "dim_product", "dim_seller", "dim_date", "dim_location"]:
        assert table_name in compat["tables"]
        assert compat["tables"][table_name]["status"] == "COMPATIBLE"


def test_gold_to_fabric_revenue_and_grain_reconciliation():
    exporter = FabricLakehouseExporter()
    metrics = exporter.compute_contract_metrics()

    m = metrics["metrics"]
    # Verify exact Kimball Star Schema Gold figures
    assert m["total_gross_revenue"] == 15843553.24
    assert m["total_fact_rows"] == 112650
    assert m["total_distinct_orders"] == 98666
    assert m["average_order_value"] == 160.58


def test_fabric_deployment_manifest_generation(tmp_path):
    exporter = FabricLakehouseExporter(output_dir=tmp_path)
    manifest_path = exporter.generate_fabric_manifest()

    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["platform"] == "AUREVIX"
    assert data["target_lakehouse"] == "AUREVIX_Lakehouse"
    assert data["compatibility"]["status"] == "VALID"
    assert data["reconciled_metrics"]["metrics"]["total_gross_revenue"] == 15843553.24
