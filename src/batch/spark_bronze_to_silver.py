"""
AUREVIX — Bronze to Silver PySpark Transformation Engine
Transforms Bronze Parquet tables into cleaned, strongly-typed, normalized,
deduplicated Silver Parquet models with Data Quality Firewall and Referential Integrity enforcement.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType, IntegerType, DoubleType, DecimalType, TimestampType, DateType, BooleanType
)

from src.config import settings
from src.common.logger import get_logger
from src.quality.data_quality_firewall import DataQualityFirewall
from src.batch.ingest_raw import get_spark_session

logger = get_logger("aurevix.bronze_to_silver")

VALID_BRAZILIAN_STATES = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]

VALID_ORDER_STATUSES = [
    'delivered', 'shipped', 'canceled', 'invoiced',
    'processing', 'created', 'approved', 'unavailable'
]


class SparkBronzeToSilverPipeline:
    def __init__(
        self,
        bronze_dir: Optional[Path] = None,
        silver_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
        monitoring_dir: Optional[Path] = None,
        spark: Optional[SparkSession] = None
    ):
        self.bronze_dir = Path(bronze_dir or settings.BRONZE_DATA_PATH)
        self.silver_dir = Path(silver_dir or settings.SILVER_DATA_PATH)
        self.quarantine_dir = Path(quarantine_dir or settings.QUARANTINE_DATA_PATH)
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)
        self._spark = spark
        self._owns_spark = spark is None
        self.firewall = DataQualityFirewall(quarantine_dir=self.quarantine_dir)
        self.batch_id = f"batch_{int(time.time())}"

    @property
    def spark(self) -> SparkSession:
        if self._spark is None:
            self._spark = get_spark_session(app_name="AUREVIX-Bronze-to-Silver")
        return self._spark

    def load_bronze(self, entity_name: str) -> DataFrame:
        """Reads a Bronze Parquet dataset."""
        path = self.bronze_dir / entity_name
        if not path.exists():
            raise FileNotFoundError(f"Bronze table not found: {path}")
        return self.spark.read.parquet(str(path))

    def write_silver(
        self,
        df: DataFrame,
        entity_name: str,
        partition_cols: Optional[List[str]] = None
    ) -> Path:
        """Writes clean Silver DataFrame to Snappy Parquet."""
        target_dir = self.silver_dir / entity_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        writer = df.write.mode("overwrite").option("compression", "snappy")
        if partition_cols:
            writer.partitionBy(*partition_cols).parquet(str(target_dir))
        else:
            writer.parquet(str(target_dir))
            
        logger.info(f"Wrote Silver table {entity_name} ({df.count():,} rows) -> {target_dir}")
        return target_dir

    # =========================================================================
    # 1. CATEGORY TRANSLATION
    # =========================================================================
    def transform_category_translation(self) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_category_translation")
        
        df_clean = (
            df
            .withColumn("product_category_name", F.trim(F.col("product_category_name")))
            .withColumn("product_category_name_english", F.trim(F.col("product_category_name_english")))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        # Deduplication on product_category_name
        df_dedup = df_clean.dropDuplicates(["product_category_name"])

        # DQ Rules
        rules = [
            {"id": "DQ001", "description": "Category name required", "condition": F.col("product_category_name").isNotNull() & (F.length("product_category_name") > 0)},
            {"id": "DQ002", "description": "English category name required", "condition": F.col("product_category_name_english").isNotNull() & (F.length("product_category_name_english") > 0)}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_dedup, rules, "silver_category_translation", self.batch_id)
        self.firewall.write_quarantine(df_quarantine, "silver_category_translation")
        self.write_silver(df_valid, "silver_category_translation")
        return df_valid, metrics

    # =========================================================================
    # 2. CUSTOMERS
    # =========================================================================
    def transform_customers(self) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_customers")

        df_clean = (
            df
            .withColumn("customer_id", F.trim(F.col("customer_id")))
            .withColumn("customer_unique_id", F.trim(F.col("customer_unique_id")))
            .withColumn("customer_zip_code_prefix", F.trim(F.col("customer_zip_code_prefix")))
            .withColumn("customer_city", F.initcap(F.trim(F.col("customer_city"))))
            .withColumn("customer_state", F.upper(F.trim(F.col("customer_state"))))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        # Deduplication on customer_id
        df_dedup = df_clean.dropDuplicates(["customer_id"])

        # DQ Rules
        rules = [
            {"id": "DQ002", "description": "Customer ID Required", "condition": F.col("customer_id").isNotNull() & (F.length("customer_id") > 0)},
            {"id": "DQ002", "description": "Customer Unique ID Required", "condition": F.col("customer_unique_id").isNotNull() & (F.length("customer_unique_id") > 0)},
            {"id": "DQ011", "description": "Valid Brazilian State Code", "condition": F.col("customer_state").isin(VALID_BRAZILIAN_STATES)}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_dedup, rules, "silver_customers", self.batch_id)
        self.firewall.write_quarantine(df_quarantine, "silver_customers")
        self.write_silver(df_valid, "silver_customers")
        return df_valid, metrics

    # =========================================================================
    # 3. SELLERS
    # =========================================================================
    def transform_sellers(self) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_sellers")

        df_clean = (
            df
            .withColumn("seller_id", F.trim(F.col("seller_id")))
            .withColumn("seller_zip_code_prefix", F.trim(F.col("seller_zip_code_prefix")))
            .withColumn("seller_city", F.initcap(F.trim(F.col("seller_city"))))
            .withColumn("seller_state", F.upper(F.trim(F.col("seller_state"))))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        df_dedup = df_clean.dropDuplicates(["seller_id"])

        rules = [
            {"id": "DQ001", "description": "Seller ID Required", "condition": F.col("seller_id").isNotNull() & (F.length("seller_id") > 0)},
            {"id": "DQ011", "description": "Valid Brazilian State Code", "condition": F.col("seller_state").isin(VALID_BRAZILIAN_STATES)}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_dedup, rules, "silver_sellers", self.batch_id)
        self.firewall.write_quarantine(df_quarantine, "silver_sellers")
        self.write_silver(df_valid, "silver_sellers")
        return df_valid, metrics

    # =========================================================================
    # 4. PRODUCTS
    # =========================================================================
    def transform_products(self, df_cat_trans: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_products")

        df_clean = (
            df
            .withColumn("product_id", F.trim(F.col("product_id")))
            .withColumn("product_category_name_pt", F.trim(F.col("product_category_name")))
            .withColumn("product_name_length", F.col("product_name_lenght").cast(IntegerType()))
            .withColumn("product_description_length", F.col("product_description_lenght").cast(IntegerType()))
            .withColumn("product_photos_qty", F.col("product_photos_qty").cast(IntegerType()))
            .withColumn("product_weight_g", F.col("product_weight_g").cast(DecimalType(10, 2)))
            .withColumn("product_length_cm", F.col("product_length_cm").cast(DecimalType(10, 2)))
            .withColumn("product_height_cm", F.col("product_height_cm").cast(DecimalType(10, 2)))
            .withColumn("product_width_cm", F.col("product_width_cm").cast(DecimalType(10, 2)))
        )

        # Compute volume: L * H * W
        df_clean = df_clean.withColumn(
            "product_volume_cm3",
            F.when(
                df_clean.product_length_cm.isNotNull() & df_clean.product_height_cm.isNotNull() & df_clean.product_width_cm.isNotNull(),
                (df_clean.product_length_cm * df_clean.product_height_cm * df_clean.product_width_cm).cast(DecimalType(12, 2))
            ).otherwise(F.lit(None))
        )

        # Left join category translation to enrich english name
        df_joined = df_clean.join(
            df_cat_trans.select(
                F.col("product_category_name").alias("_join_cat"),
                F.col("product_category_name_english")
            ),
            df_clean.product_category_name_pt == F.col("_join_cat"),
            how="left"
        ).drop("_join_cat")

        # Fallback category name if missing
        df_joined = (
            df_joined
            .withColumn(
                "product_category_name",
                F.coalesce(F.col("product_category_name_english"), F.col("product_category_name_pt"), F.lit("unclassified"))
            )
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        df_dedup = df_joined.dropDuplicates(["product_id"])

        rules = [
            {"id": "DQ003", "description": "Product ID Required", "condition": F.col("product_id").isNotNull() & (F.length("product_id") > 0)},
            {"id": "DQ004", "description": "Weight must be non-negative", "condition": F.col("product_weight_g").isNull() | (F.col("product_weight_g") >= 0)}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_dedup, rules, "silver_products", self.batch_id)
        self.firewall.write_quarantine(df_quarantine, "silver_products")
        self.write_silver(df_valid, "silver_products")
        return df_valid, metrics

    # =========================================================================
    # 5. GEOLOCATION
    # =========================================================================
    def transform_geolocation(self) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_geolocation")

        df_clean = (
            df
            .withColumn("geolocation_zip_code_prefix", F.trim(F.col("geolocation_zip_code_prefix")))
            .withColumn("geolocation_lat", F.col("geolocation_lat").cast(DoubleType()))
            .withColumn("geolocation_lng", F.col("geolocation_lng").cast(DoubleType()))
            .withColumn("geolocation_city", F.initcap(F.trim(F.col("geolocation_city"))))
            .withColumn("geolocation_state", F.upper(F.trim(F.col("geolocation_state"))))
        )

        # Coordinate filtering: Brazil geographic bounds (-35 to +6 lat, -75 to -30 lng)
        rules = [
            {"id": "DQ011", "description": "Valid State Code", "condition": F.col("geolocation_state").isin(VALID_BRAZILIAN_STATES)},
            {"id": "DQ004", "description": "Valid Latitude", "condition": F.col("geolocation_lat").between(-35.0, 6.0)},
            {"id": "DQ004", "description": "Valid Longitude", "condition": F.col("geolocation_lng").between(-75.0, -30.0)}
        ]

        df_valid_geo, df_quarantine, metrics = self.firewall.evaluate_rules(df_clean, rules, "silver_geolocation", self.batch_id)
        self.firewall.write_quarantine(df_quarantine, "silver_geolocation")

        # Deduplicate spatial records by computing centroid per zip code prefix
        df_centroid = (
            df_valid_geo
            .groupBy("geolocation_zip_code_prefix", "geolocation_state")
            .agg(
                F.first("geolocation_city").alias("geolocation_city"),
                F.round(F.avg("geolocation_lat"), 6).alias("latitude"),
                F.round(F.avg("geolocation_lng"), 6).alias("longitude"),
                F.count("*").alias("_coordinate_samples_count")
            )
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        self.write_silver(df_centroid, "silver_geolocation")
        return df_centroid, metrics

    # =========================================================================
    # 6. ORDERS
    # =========================================================================
    def transform_orders(self, df_valid_customers: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_orders")

        df_clean = (
            df
            .withColumn("order_id", F.trim(F.col("order_id")))
            .withColumn("customer_id", F.trim(F.col("customer_id")))
            .withColumn("order_status", F.lower(F.trim(F.col("order_status"))))
            .withColumn("order_purchase_timestamp", F.to_timestamp(F.col("order_purchase_timestamp"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_approved_at", F.to_timestamp(F.col("order_approved_at"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_delivered_carrier_date", F.to_timestamp(F.col("order_delivered_carrier_date"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_delivered_customer_date", F.to_timestamp(F.col("order_delivered_customer_date"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_estimated_delivery_date", F.to_timestamp(F.col("order_estimated_delivery_date"), "yyyy-MM-dd HH:mm:ss"))
        )

        # Derived fields
        df_clean = (
            df_clean
            .withColumn("order_year_month", F.date_format(F.col("order_purchase_timestamp"), "yyyy-MM"))
            .withColumn("delivery_days", F.datediff(F.col("order_delivered_customer_date"), F.col("order_purchase_timestamp")))
            .withColumn(
                "is_delayed",
                F.when(F.col("order_delivered_customer_date") > F.col("order_estimated_delivery_date"), F.lit(True))
                .when(F.col("order_delivered_customer_date").isNotNull(), F.lit(False))
                .otherwise(F.lit(None))
            )
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        # Deduplication on order_id
        df_dedup = df_clean.dropDuplicates(["order_id"])

        # Referential Integrity with Customers
        df_ref = df_dedup.join(
            df_valid_customers.select(F.col("customer_id").alias("_ref_cust_id")),
            df_dedup.customer_id == F.col("_ref_cust_id"),
            how="left"
        )

        # DQ Rules
        rules = [
            {"id": "DQ001", "description": "Order ID Required", "condition": F.col("order_id").isNotNull() & (F.length("order_id") > 0)},
            {"id": "DQ002", "description": "Customer ID Required", "condition": F.col("customer_id").isNotNull() & (F.length("customer_id") > 0)},
            {"id": "DQ007", "description": "Valid Order Status", "condition": F.col("order_status").isin(VALID_ORDER_STATUSES)},
            {"id": "DQ008", "description": "Valid Purchase Timestamp", "condition": F.col("order_purchase_timestamp").isNotNull() & (F.col("order_purchase_timestamp") >= "2016-01-01")},
            {"id": "DQ009", "description": "Timestamp Sequence", "condition": F.col("order_delivered_customer_date").isNull() | (F.col("order_delivered_customer_date") >= F.col("order_purchase_timestamp"))},
            {"id": "DQ010", "description": "Referential Integrity Customer", "condition": F.col("_ref_cust_id").isNotNull()}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_ref, rules, "silver_orders", self.batch_id)
        df_valid = df_valid.drop("_ref_cust_id")
        self.firewall.write_quarantine(df_quarantine, "silver_orders")
        self.write_silver(df_valid, "silver_orders", partition_cols=["order_year_month"])
        return df_valid, metrics

    # =========================================================================
    # 7. ORDER ITEMS
    # =========================================================================
    def transform_order_items(
        self,
        df_valid_orders: DataFrame,
        df_valid_products: DataFrame,
        df_valid_sellers: DataFrame
    ) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_order_items")

        df_clean = (
            df
            .withColumn("order_id", F.trim(F.col("order_id")))
            .withColumn("order_item_id", F.col("order_item_id").cast(IntegerType()))
            .withColumn("product_id", F.trim(F.col("product_id")))
            .withColumn("seller_id", F.trim(F.col("seller_id")))
            .withColumn("shipping_limit_date", F.to_timestamp(F.col("shipping_limit_date"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("price", F.col("price").cast(DecimalType(10, 2)))
            .withColumn("freight_value", F.col("freight_value").cast(DecimalType(10, 2)))
            .withColumn("total_item_amount", (F.col("price") + F.col("freight_value")).cast(DecimalType(10, 2)))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        df_dedup = df_clean.dropDuplicates(["order_id", "order_item_id"])

        # Referential integrity joins
        df_ref = (
            df_dedup
            .join(df_valid_orders.select(F.col("order_id").alias("_ref_order_id"), "order_year_month"), df_dedup.order_id == F.col("_ref_order_id"), how="left")
            .join(df_valid_products.select(F.col("product_id").alias("_ref_prod_id")), df_dedup.product_id == F.col("_ref_prod_id"), how="left")
            .join(df_valid_sellers.select(F.col("seller_id").alias("_ref_seller_id")), df_dedup.seller_id == F.col("_ref_seller_id"), how="left")
        )

        rules = [
            {"id": "DQ001", "description": "Order ID Required", "condition": F.col("order_id").isNotNull()},
            {"id": "DQ003", "description": "Product ID Required", "condition": F.col("product_id").isNotNull()},
            {"id": "DQ004", "description": "Price >= 0", "condition": F.col("price").isNotNull() & (F.col("price") >= 0.0)},
            {"id": "DQ005", "description": "Freight Value >= 0", "condition": F.col("freight_value").isNotNull() & (F.col("freight_value") >= 0.0)},
            {"id": "DQ006", "description": "Order Item ID >= 1", "condition": F.col("order_item_id").isNotNull() & (F.col("order_item_id") >= 1)},
            {"id": "DQ010", "description": "Referential Integrity Order", "condition": F.col("_ref_order_id").isNotNull()},
            {"id": "DQ010", "description": "Referential Integrity Product", "condition": F.col("_ref_prod_id").isNotNull()},
            {"id": "DQ010", "description": "Referential Integrity Seller", "condition": F.col("_ref_seller_id").isNotNull()}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_ref, rules, "silver_order_items", self.batch_id)
        df_valid = df_valid.drop("_ref_order_id", "_ref_prod_id", "_ref_seller_id")
        self.firewall.write_quarantine(df_quarantine, "silver_order_items")
        self.write_silver(df_valid, "silver_order_items", partition_cols=["order_year_month"])
        return df_valid, metrics

    # =========================================================================
    # 8. ORDER PAYMENTS
    # =========================================================================
    def transform_order_payments(self, df_valid_orders: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_order_payments")

        df_clean = (
            df
            .withColumn("order_id", F.trim(F.col("order_id")))
            .withColumn("payment_sequential", F.col("payment_sequential").cast(IntegerType()))
            .withColumn("payment_type", F.lower(F.trim(F.col("payment_type"))))
            .withColumn("payment_installments", F.col("payment_installments").cast(IntegerType()))
            .withColumn("payment_value", F.col("payment_value").cast(DecimalType(10, 2)))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        df_dedup = df_clean.dropDuplicates(["order_id", "payment_sequential"])

        df_ref = df_dedup.join(
            df_valid_orders.select(F.col("order_id").alias("_ref_order_id")),
            df_dedup.order_id == F.col("_ref_order_id"),
            how="left"
        )

        rules = [
            {"id": "DQ001", "description": "Order ID Required", "condition": F.col("order_id").isNotNull()},
            {"id": "DQ004", "description": "Payment Value >= 0", "condition": F.col("payment_value").isNotNull() & (F.col("payment_value") >= 0.0)},
            {"id": "DQ006", "description": "Payment Installments >= 0", "condition": F.col("payment_installments").isNotNull() & (F.col("payment_installments") >= 0)},
            {"id": "DQ010", "description": "Referential Integrity Order", "condition": F.col("_ref_order_id").isNotNull()}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_ref, rules, "silver_order_payments", self.batch_id)
        df_valid = df_valid.drop("_ref_order_id")
        self.firewall.write_quarantine(df_quarantine, "silver_order_payments")
        self.write_silver(df_valid, "silver_order_payments")
        return df_valid, metrics

    # =========================================================================
    # 9. ORDER REVIEWS
    # =========================================================================
    def transform_order_reviews(self, df_valid_orders: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        df = self.load_bronze("bronze_order_reviews")

        df_clean = (
            df
            .withColumn("review_id", F.trim(F.col("review_id")))
            .withColumn("order_id", F.trim(F.col("order_id")))
            .withColumn("review_score", F.col("review_score").cast(IntegerType()))
            .withColumn("review_comment_title", F.trim(F.col("review_comment_title")))
            .withColumn("review_comment_message", F.trim(F.col("review_comment_message")))
            .withColumn("review_creation_date", F.to_timestamp(F.col("review_creation_date"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("review_answer_timestamp", F.to_timestamp(F.col("review_answer_timestamp"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("_silver_processed_at", F.current_timestamp())
        )

        df_dedup = df_clean.dropDuplicates(["review_id", "order_id"])

        df_ref = df_dedup.join(
            df_valid_orders.select(F.col("order_id").alias("_ref_order_id")),
            df_dedup.order_id == F.col("_ref_order_id"),
            how="left"
        )

        rules = [
            {"id": "DQ001", "description": "Review ID and Order ID Required", "condition": F.col("review_id").isNotNull() & F.col("order_id").isNotNull()},
            {"id": "DQ012", "description": "Review score between 1 and 5", "condition": F.col("review_score").between(1, 5)},
            {"id": "DQ010", "description": "Referential Integrity Order", "condition": F.col("_ref_order_id").isNotNull()}
        ]

        df_valid, df_quarantine, metrics = self.firewall.evaluate_rules(df_ref, rules, "silver_order_reviews", self.batch_id)
        df_valid = df_valid.drop("_ref_order_id")
        self.firewall.write_quarantine(df_quarantine, "silver_order_reviews")
        self.write_silver(df_valid, "silver_order_reviews")
        return df_valid, metrics

    # =========================================================================
    # MASTER PIPELINE EXECUTION
    # =========================================================================
    def run(self) -> Dict[str, Any]:
        """Executes full Bronze -> Silver PySpark pipeline."""
        start_time = time.time()
        logger.info(f"=== Starting AUREVIX Bronze to Silver PySpark Pipeline [{self.batch_id}] ===")

        # 1. Independent Dimensions
        df_cat, m_cat = self.transform_category_translation()
        df_cust, m_cust = self.transform_customers()
        df_sellers, m_sellers = self.transform_sellers()
        df_geo, m_geo = self.transform_geolocation()
        df_prod, m_prod = self.transform_products(df_cat)

        # 2. Orders (Depends on Customers)
        df_orders, m_orders = self.transform_orders(df_cust)

        # 3. Order Items, Payments, Reviews (Depend on Orders, Products, Sellers)
        df_items, m_items = self.transform_order_items(df_orders, df_prod, df_sellers)
        df_pay, m_pay = self.transform_order_payments(df_orders)
        df_rev, m_rev = self.transform_order_reviews(df_orders)

        duration = round(time.time() - start_time, 3)

        all_metrics = [m_cat, m_cust, m_sellers, m_geo, m_prod, m_orders, m_items, m_pay, m_rev]
        total_input = sum(m["input_count"] for m in all_metrics)
        total_valid = sum(m["valid_count"] for m in all_metrics)
        total_quarantined = sum(m["quarantined_count"] for m in all_metrics)

        report = {
            "pipeline": "aurevix_bronze_to_silver_batch",
            "batch_id": self.batch_id,
            "engine": f"PySpark {self.spark.version}",
            "execution_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": duration,
            "total_entities_processed": len(all_metrics),
            "total_input_rows": total_input,
            "total_valid_rows": total_valid,
            "total_quarantined_rows": total_quarantined,
            "overall_quarantine_rate_pct": round((total_quarantined / total_input * 100.0), 4) if total_input > 0 else 0.0,
            "entities": all_metrics
        }

        # Write Data Quality Report
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.monitoring_dir / "silver_quality_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Silver Data Quality Report saved -> {report_path}")
        logger.info(
            f"=== Pipeline Complete in {duration}s: {total_valid:,} Valid, "
            f"{total_quarantined:,} Quarantined ==="
        )
        return report

    def close(self):
        if self._owns_spark and self._spark is not None:
            self._spark.stop()
            self._spark = None


if __name__ == "__main__":
    pipeline = SparkBronzeToSilverPipeline()
    try:
        report = pipeline.run()
        print(f"\nSilver Pipeline Success: {report['total_valid_rows']:,} rows loaded to Silver in {report['duration_seconds']}s")
    finally:
        pipeline.close()
