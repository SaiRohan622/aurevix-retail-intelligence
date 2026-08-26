"""
AUREVIX — Unit Tests for Microsoft Fabric Cloud Data Contract
"""

import pytest
from src.fabric.fabric_sync import FABRIC_DATA_CONTRACT, FabricLakehouseExporter


def test_fabric_data_contract_structure():
    contract = FABRIC_DATA_CONTRACT
    assert contract["lakehouse_name"] == "AUREVIX_Lakehouse"
    assert contract["schema_version"] == "1.0.0"

    tables = contract["tables"]
    assert "fact_sales" in tables
    assert "dim_customer" in tables
    assert "dim_product" in tables
    assert "dim_seller" in tables
    assert "dim_date" in tables
    assert "dim_location" in tables


def test_fact_sales_contract_grain_and_keys():
    fact_spec = FABRIC_DATA_CONTRACT["tables"]["fact_sales"]
    assert fact_spec["grain"] == ["order_id", "order_item_id"]
    assert "sales_fact_key" in fact_spec["primary_key"]
    assert "customer_key" in fact_spec["foreign_keys"]
    assert "product_key" in fact_spec["foreign_keys"]
    assert "order_date_key" in fact_spec["foreign_keys"]


def test_fabric_exporter_initialization():
    exporter = FabricLakehouseExporter()
    assert exporter.contract["lakehouse_name"] == "AUREVIX_Lakehouse"
    assert exporter.gold_dir.exists()
