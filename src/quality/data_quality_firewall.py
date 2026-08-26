"""
AUREVIX — Data Quality Firewall Engine (PySpark)
Evaluates Spark DataFrames against the DQ001-DQ012 catalog, partitions records
into Valid and Quarantined datasets, and enriches rejected records with diagnostic audit metadata.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.config import settings
from src.common.logger import get_logger

logger = get_logger("aurevix.quality_firewall")


class DataQualityFirewall:
    """Reusable PySpark Data Quality Firewall with Quarantine Routing."""

    def __init__(self, quarantine_dir: Optional[Path] = None):
        self.quarantine_dir = Path(quarantine_dir or settings.QUARANTINE_DATA_PATH)

    @staticmethod
    def evaluate_rules(
        df: DataFrame,
        rule_conditions: List[Dict[str, Any]],
        entity_name: str,
        batch_id: str
    ) -> Tuple[DataFrame, DataFrame, Dict[str, Any]]:
        """
        Evaluates a set of boolean conditions on a DataFrame.
        Records meeting all conditions -> Valid DataFrame.
        Records violating any condition -> Quarantined DataFrame with audit columns.
        """
        quarantine_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rejection_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if not rule_conditions:
            metrics = {
                "entity": entity_name,
                "input_count": df.count(),
                "valid_count": df.count(),
                "quarantined_count": 0,
                "quarantine_pct": 0.0
            }
            return df, df.limit(0), metrics

        failure_reasons = []
        failed_rule_ids = []

        for rule in rule_conditions:
            cond = rule["condition"]  # Condition that MUST BE TRUE for a record to be valid
            rule_id = rule["id"]
            desc = rule["description"]

            # If cond is False or NULL -> it's a failure
            is_failure = (~cond) | (cond.isNull())
            failure_reasons.append(
                F.when(is_failure, F.lit(f"{rule_id}: {desc}")).otherwise(F.lit(None))
            )
            failed_rule_ids.append(
                F.when(is_failure, F.lit(rule_id)).otherwise(F.lit(None))
            )

        # Use array_compact to remove null elements from the array
        df_evaluated = (
            df
            .withColumn("_failed_reasons_arr", F.array_compact(F.array(*failure_reasons)))
            .withColumn("_failed_rule_ids_arr", F.array_compact(F.array(*failed_rule_ids)))
        )

        df_evaluated = df_evaluated.withColumn(
            "_has_failures",
            F.size(F.col("_failed_rule_ids_arr")) > 0
        )

        # Valid Records
        df_valid = (
            df_evaluated
            .filter(~F.col("_has_failures"))
            .drop("_failed_reasons_arr", "_failed_rule_ids_arr", "_has_failures")
        )

        # Quarantined Records
        df_raw_json = F.to_json(F.struct([F.col(c) for c in df.columns]))

        df_quarantined = (
            df_evaluated
            .filter(F.col("_has_failures"))
            .withColumn("_quarantine_id", F.expr("uuid()"))
            .withColumn("_source_entity", F.lit(entity_name))
            .withColumn("_dq_rule_id", F.array_join(F.col("_failed_rule_ids_arr"), "; "))
            .withColumn("_dq_reason", F.array_join(F.col("_failed_reasons_arr"), "; "))
            .withColumn("_quarantine_timestamp", F.lit(quarantine_timestamp))
            .withColumn("_rejection_date", F.lit(rejection_date))
            .withColumn("_processing_batch_id", F.lit(batch_id))
            .withColumn("raw_payload", df_raw_json)
            .drop("_failed_reasons_arr", "_failed_rule_ids_arr", "_has_failures")
        )

        input_count = df.count()
        valid_count = df_valid.count()
        quarantine_count = df_quarantined.count()

        metrics = {
            "entity": entity_name,
            "input_count": input_count,
            "valid_count": valid_count,
            "quarantined_count": quarantine_count,
            "quarantine_pct": round((quarantine_count / input_count * 100.0), 2) if input_count > 0 else 0.0
        }

        logger.info(
            f"[{entity_name}] DQ Firewall: {valid_count:,} Valid, "
            f"{quarantine_count:,} Quarantined ({metrics['quarantine_pct']}%) out of {input_count:,}"
        )

        return df_valid, df_quarantined, metrics

    def write_quarantine(self, df_quarantined: DataFrame, entity_name: str):
        """Writes quarantined records to Snappy Parquet in data/quarantine/."""
        if df_quarantined.count() > 0:
            target_dir = self.quarantine_dir / entity_name
            target_dir.mkdir(parents=True, exist_ok=True)
            (
                df_quarantined
                .write
                .mode("append")
                .option("compression", "snappy")
                .partitionBy("_rejection_date")
                .parquet(str(target_dir))
            )
            logger.info(f"Appended {df_quarantined.count():,} records to quarantine: {target_dir}")
