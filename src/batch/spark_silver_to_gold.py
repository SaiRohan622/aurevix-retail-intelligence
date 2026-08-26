"""
AUREVIX — Silver to Gold PySpark Transformation Engine (Star Schema)
Builds dimensional warehouse models (dim_date, dim_customer, dim_product, dim_seller, dim_location)
and fact_sales (grain: 1 row per order-item transaction) with surrogate keys, measures, and KPI reporting.
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

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType, IntegerType, DoubleType, DecimalType, TimestampType, DateType, BooleanType, LongType
)

from src.config import settings
from src.common.logger import get_logger
from src.batch.ingest_raw import get_spark_session

logger = get_logger("aurevix.silver_to_gold")


class SparkSilverToGoldPipeline:
    def __init__(
        self,
        silver_dir: Optional[Path] = None,
        gold_dir: Optional[Path] = None,
        monitoring_dir: Optional[Path] = None,
        spark: Optional[SparkSession] = None
    ):
        self.silver_dir = Path(silver_dir or settings.SILVER_DATA_PATH)
        self.gold_dir = Path(gold_dir or settings.GOLD_DATA_PATH)
        self.monitoring_dir = Path(monitoring_dir or settings.MONITORING_DATA_PATH)
        self._spark = spark
        self._owns_spark = spark is None
        self.batch_id = f"gold_batch_{int(time.time())}"

    @property
    def spark(self) -> SparkSession:
        if self._spark is None:
            self._spark = get_spark_session(app_name="AUREVIX-Silver-to-Gold-StarSchema")
        return self._spark

    def load_silver(self, entity_name: str) -> DataFrame:
        path = self.silver_dir / entity_name
        if not path.exists():
            raise FileNotFoundError(f"Silver table not found at: {path}")
        return self.spark.read.parquet(str(path))

    def write_gold(
        self,
        df: DataFrame,
        entity_name: str,
        partition_cols: Optional[List[str]] = None
    ) -> Path:
        target_dir = self.gold_dir / entity_name
        target_dir.mkdir(parents=True, exist_ok=True)

        writer = df.write.mode("overwrite").option("compression", "snappy")
        if partition_cols:
            writer.partitionBy(*partition_cols).parquet(str(target_dir))
        else:
            writer.parquet(str(target_dir))

        count = df.count()
        logger.info(f"Wrote Gold table {entity_name} ({count:,} rows) -> {target_dir}")
        return target_dir

    # =========================================================================
    # 1. DIM_DATE (Calendar Dimension 2016-2020)
    # =========================================================================
    def build_dim_date(self, start_date: str = "2016-01-01", end_date: str = "2020-12-31") -> DataFrame:
        logger.info(f"Generating dim_date from {start_date} to {end_date}")
        df_dates = (
            self.spark.sql(f"SELECT explode(sequence(to_date('{start_date}'), to_date('{end_date}'), interval 1 day)) as full_date")
        )

        dim_date = (
            df_dates
            .withColumn("date_key", F.date_format("full_date", "yyyyMMdd").cast(IntegerType()))
            .withColumn("day_of_month", F.dayofmonth("full_date"))
            .withColumn("day_of_week", F.dayofweek("full_date"))
            .withColumn("day_name", F.date_format("full_date", "EEEE"))
            .withColumn("week_of_year", F.weekofyear("full_date"))
            .withColumn("month_number", F.month("full_date"))
            .withColumn("month_name", F.date_format("full_date", "MMMM"))
            .withColumn("quarter", F.quarter("full_date"))
            .withColumn("year", F.year("full_date"))
            .withColumn("is_weekend", F.when(F.dayofweek("full_date").isin([1, 7]), True).otherwise(False))
            .withColumn("_gold_processed_at", F.current_timestamp())
        )

        self.write_gold(dim_date, "dim_date")
        return dim_date

    # =========================================================================
    # 2. DIM_LOCATION (Conformed Geographic Dimension)
    # =========================================================================
    def build_dim_location(self) -> DataFrame:
        logger.info("Building dim_location from silver_geolocation")
        df_geo = self.load_silver("silver_geolocation")

        dim_location = (
            df_geo
            .withColumn(
                "location_key",
                F.sha2(F.concat_ws("||", F.col("geolocation_zip_code_prefix"), F.col("geolocation_state")), 256)
            )
            .withColumnRenamed("geolocation_zip_code_prefix", "zip_code_prefix")
            .withColumnRenamed("geolocation_city", "city")
            .withColumnRenamed("geolocation_state", "state")
            .withColumnRenamed("_coordinate_samples_count", "coordinate_samples_count")
            .withColumn("_gold_processed_at", F.current_timestamp())
        )

        self.write_gold(dim_location, "dim_location")
        return dim_location

    # =========================================================================
    # 3. DIM_CUSTOMER (Customer Dimension + SCD Type 2 Audit Columns)
    # =========================================================================
    def build_dim_customer(self) -> DataFrame:
        logger.info("Building dim_customer from silver_customers")
        df_cust = self.load_silver("silver_customers")

        dim_customer = (
            df_cust
            .withColumn("customer_key", F.sha2(F.concat_ws("||", F.col("customer_id"), F.lit("v1")), 256))
            .withColumn("location_key", F.sha2(F.concat_ws("||", F.col("customer_zip_code_prefix"), F.col("customer_state")), 256))
            .withColumn("is_current", F.lit(True))
            .withColumn("effective_start_date", F.to_timestamp(F.lit("2016-01-01 00:00:00")))
            .withColumn("effective_end_date", F.to_timestamp(F.lit("9999-12-31 23:59:59")))
            .withColumn("_gold_processed_at", F.current_timestamp())
        )

        self.write_gold(dim_customer, "dim_customer")
        return dim_customer

    # =========================================================================
    # 4. DIM_PRODUCT (Product Dimension)
    # =========================================================================
    def build_dim_product(self) -> DataFrame:
        logger.info("Building dim_product from silver_products")
        df_prod = self.load_silver("silver_products")

        dim_product = (
            df_prod
            .withColumn("product_key", F.sha2(F.col("product_id"), 256))
            .withColumn("_gold_processed_at", F.current_timestamp())
        )

        self.write_gold(dim_product, "dim_product")
        return dim_product

    # =========================================================================
    # 5. DIM_SELLER (Seller Dimension)
    # =========================================================================
    def build_dim_seller(self) -> DataFrame:
        logger.info("Building dim_seller from silver_sellers")
        df_sellers = self.load_silver("silver_sellers")

        dim_seller = (
            df_sellers
            .withColumn("seller_key", F.sha2(F.col("seller_id"), 256))
            .withColumn("location_key", F.sha2(F.concat_ws("||", F.col("seller_zip_code_prefix"), F.col("seller_state")), 256))
            .withColumn("_gold_processed_at", F.current_timestamp())
        )

        self.write_gold(dim_seller, "dim_seller")
        return dim_seller

    # =========================================================================
    # 6. FACT_SALES (Grain: One row per order-item line transaction)
    # =========================================================================
    def build_fact_sales(
        self,
        dim_cust: DataFrame,
        dim_prod: DataFrame,
        dim_sell: DataFrame,
        dim_date: DataFrame,
        dim_loc: DataFrame
    ) -> Tuple[DataFrame, Dict[str, Any]]:
        logger.info("Building fact_sales (Grain: 1 row per order_item)")

        df_items = self.load_silver("silver_order_items")
        df_orders = self.load_silver("silver_orders")

        # Join order items with parent orders (omit duplicate order_year_month)
        df_joined = df_items.join(
            df_orders.select(
                "order_id",
                "customer_id",
                "order_status",
                "order_purchase_timestamp",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
                "delivery_days",
                "is_delayed"
            ),
            on="order_id",
            how="inner"
        )

        # Join with dim_customer to resolve customer_key & customer location_key
        df_with_cust = df_joined.join(
            dim_cust.select("customer_id", "customer_key", F.col("location_key").alias("customer_location_key")),
            on="customer_id",
            how="left"
        )

        # Join with dim_product to resolve product_key
        df_with_prod = df_with_cust.join(
            dim_prod.select("product_id", "product_key"),
            on="product_id",
            how="left"
        )

        # Join with dim_seller to resolve seller_key
        df_with_sell = df_with_prod.join(
            dim_sell.select("seller_id", "seller_key"),
            on="seller_id",
            how="left"
        )

        # Construct fact_sales
        fact_sales = (
            df_with_sell
            .withColumn("sales_fact_key", F.sha2(F.concat_ws("||", F.col("order_id"), F.col("order_item_id")), 256))
            .withColumn("order_date_key", F.date_format("order_purchase_timestamp", "yyyyMMdd").cast(IntegerType()))
            .withColumn("location_key", F.col("customer_location_key"))
            .withColumn("order_item_quantity", F.lit(1).cast(IntegerType()))
            .withColumn("item_price", F.col("price").cast(DecimalType(10, 2)))
            .withColumn("freight_value", F.col("freight_value").cast(DecimalType(10, 2)))
            .withColumn("gross_item_value", F.col("price").cast(DecimalType(10, 2)))
            .withColumn("total_item_value", (F.col("price") + F.col("freight_value")).cast(DecimalType(10, 2)))
            .withColumn("_gold_processed_at", F.current_timestamp())
            .select(
                "sales_fact_key",
                "order_id",
                "order_item_id",
                "customer_key",
                "product_key",
                "seller_key",
                "order_date_key",
                "location_key",
                "order_status",
                "order_purchase_timestamp",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
                "delivery_days",
                "is_delayed",
                "order_item_quantity",
                "item_price",
                "freight_value",
                "gross_item_value",
                "total_item_value",
                "order_year_month",
                "_gold_processed_at"
            )
        )

        self.write_gold(fact_sales, "fact_sales", partition_cols=["order_year_month"])

        # Metrics calculation
        fact_count = fact_sales.count()
        distinct_fact_keys = fact_sales.select("sales_fact_key").distinct().count()
        total_revenue_item = float(fact_sales.select(F.sum("item_price")).collect()[0][0] or 0.0)
        total_freight = float(fact_sales.select(F.sum("freight_value")).collect()[0][0] or 0.0)
        total_revenue_gross = float(fact_sales.select(F.sum("total_item_value")).collect()[0][0] or 0.0)
        total_orders = fact_sales.select("order_id").distinct().count()
        total_units = int(fact_sales.select(F.sum("order_item_quantity")).collect()[0][0] or 0)
        aov = round(total_revenue_gross / total_orders, 2) if total_orders > 0 else 0.0

        # Referential integrity check
        null_cust_keys = fact_sales.filter(F.col("customer_key").isNull()).count()
        null_prod_keys = fact_sales.filter(F.col("product_key").isNull()).count()
        null_sell_keys = fact_sales.filter(F.col("seller_key").isNull()).count()

        fact_metrics = {
            "entity": "fact_sales",
            "fact_row_count": fact_count,
            "distinct_fact_keys": distinct_fact_keys,
            "grain_violations_count": fact_count - distinct_fact_keys,
            "total_orders_count": total_orders,
            "total_units_sold": total_units,
            "total_item_revenue": round(total_revenue_item, 2),
            "total_freight_revenue": round(total_freight, 2),
            "total_gross_revenue": round(total_revenue_gross, 2),
            "average_order_value_aov": aov,
            "orphan_customer_keys": null_cust_keys,
            "orphan_product_keys": null_prod_keys,
            "orphan_seller_keys": null_sell_keys
        }

        return fact_sales, fact_metrics

    # =========================================================================
    # MASTER PIPELINE EXECUTION
    # =========================================================================
    def run(self) -> Dict[str, Any]:
        pipeline_start = time.time()
        logger.info(f"=== Starting AUREVIX Silver to Gold Star Schema Pipeline [{self.batch_id}] ===")

        # 1. Build Conformed Dimensions
        dim_date = self.build_dim_date()
        dim_location = self.build_dim_location()
        dim_cust = self.build_dim_customer()
        dim_prod = self.build_dim_product()
        dim_sell = self.build_dim_seller()

        # 2. Build Fact Sales
        fact_sales, fact_metrics = self.build_fact_sales(
            dim_cust=dim_cust,
            dim_prod=dim_prod,
            dim_sell=dim_sell,
            dim_date=dim_date,
            dim_loc=dim_location
        )

        # 3. Revenue Reconciliation against Silver
        df_silver_items = self.load_silver("silver_order_items")
        silver_item_rev = float(df_silver_items.select(F.sum("price")).collect()[0][0] or 0.0)
        silver_freight_rev = float(df_silver_items.select(F.sum("freight_value")).collect()[0][0] or 0.0)
        silver_total_rev = float(df_silver_items.select(F.sum("total_item_amount")).collect()[0][0] or 0.0)

        gold_item_rev = fact_metrics["total_item_revenue"]
        gold_total_rev = fact_metrics["total_gross_revenue"]
        revenue_variance = round(gold_total_rev - silver_total_rev, 2)

        duration = round(time.time() - pipeline_start, 3)

        report = {
            "pipeline": "aurevix_silver_to_gold_batch",
            "batch_id": self.batch_id,
            "engine": f"PySpark {self.spark.version}",
            "execution_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": duration,
            "dimensions": {
                "dim_date_rows": dim_date.count(),
                "dim_location_rows": dim_location.count(),
                "dim_customer_rows": dim_cust.count(),
                "dim_product_rows": dim_prod.count(),
                "dim_seller_rows": dim_sell.count()
            },
            "fact_sales": fact_metrics,
            "revenue_reconciliation": {
                "silver_source_item_revenue": round(silver_item_rev, 2),
                "silver_source_freight_revenue": round(silver_freight_rev, 2),
                "silver_source_total_revenue": round(silver_total_rev, 2),
                "gold_fact_item_revenue": round(gold_item_rev, 2),
                "gold_fact_total_revenue": round(gold_total_rev, 2),
                "revenue_variance": revenue_variance,
                "reconciliation_status": "EXACT_MATCH" if abs(revenue_variance) < 0.01 else "VARIANCE_DETECTED"
            },
            "business_kpis": {
                "total_gross_revenue": fact_metrics["total_gross_revenue"],
                "total_orders": fact_metrics["total_orders_count"],
                "units_sold": fact_metrics["total_units_sold"],
                "average_order_value_aov": fact_metrics["average_order_value_aov"],
                "average_freight_per_item": round(fact_metrics["total_freight_revenue"] / fact_metrics["total_units_sold"], 2) if fact_metrics["total_units_sold"] > 0 else 0.0
            },
            "status": "SUCCESS"
        }

        # Write Gold Quality Report
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.monitoring_dir / "gold_quality_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Gold Quality Report saved -> {report_path}")
        logger.info(
            f"=== Gold Star Schema Complete in {duration}s: {fact_metrics['fact_row_count']:,} Fact Rows, "
            f"Revenue Variance: ${revenue_variance} ==="
        )
        return report

    def close(self):
        if self._owns_spark and self._spark is not None:
            self._spark.stop()
            self._spark = None


if __name__ == "__main__":
    pipeline = SparkSilverToGoldPipeline()
    try:
        report = pipeline.run()
        print(f"\nGold Pipeline Success: {report['fact_sales']['fact_row_count']:,} rows in fact_sales in {report['duration_seconds']}s")
    finally:
        pipeline.close()
