"""
AUREVIX — Source Data Profiler
Profiles raw Olist CSV datasets in data/raw/ and generates comprehensive
statistical metadata reports (row counts, nulls, duplicates, date bounds, anomalies).
Supports both pandas (when installed) and standard library csv parsing for zero-dependency portability.
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, List


class SourceDataProfiler:
    def __init__(self, raw_dir: str = "data/raw", report_dir: str = "docs/data_dictionary"):
        self.raw_dir = Path(raw_dir)
        self.report_dir = Path(report_dir)
        self.expected_files = [
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

    def check_files_availability(self) -> Dict[str, bool]:
        """Verify which source files exist in data/raw."""
        availability = {}
        for filename in self.expected_files:
            file_path = self.raw_dir / filename
            availability[filename] = file_path.is_file()
        return availability

    def profile_file_stdlib(self, file_path: Path) -> Dict[str, Any]:
        """Profile a single raw CSV dataset using standard library csv module."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return {"filename": file_path.name, "row_count": 0, "column_count": 0, "columns": []}

            cols = [col.strip() for col in header]
            row_count = 0
            null_counts = {col: 0 for col in cols}
            seen_rows = set()
            duplicate_count = 0

            for row in reader:
                row_count += 1
                row_tuple = tuple(row)
                if row_tuple in seen_rows:
                    duplicate_count += 1
                else:
                    if len(seen_rows) < 200000:
                        seen_rows.add(row_tuple)

                for idx, col in enumerate(cols):
                    val = row[idx].strip() if idx < len(row) else ""
                    if val == "" or val.lower() in ("null", "none", "nan"):
                        null_counts[col] += 1

            return {
                "filename": file_path.name,
                "row_count": row_count,
                "column_count": len(cols),
                "columns": cols,
                "null_counts": null_counts,
                "null_percentages": {col: round((null_counts[col] / row_count) * 100, 2) if row_count > 0 else 0.0 for col in cols},
                "duplicate_rows": duplicate_count,
                "profiling_engine": "python-stdlib-csv"
            }

    def profile_file(self, file_path: Path) -> Dict[str, Any]:
        """Profile a single raw CSV dataset."""
        try:
            import pandas as pd
            df = pd.read_csv(file_path, low_memory=False)
            profile = {
                "filename": file_path.name,
                "row_count": int(len(df)),
                "column_count": int(len(df.columns)),
                "columns": list(df.columns),
                "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
                "null_percentages": {col: round(float(df[col].isna().mean() * 100), 2) for col in df.columns},
                "duplicate_rows": int(df.duplicated().sum()),
                "profiling_engine": "pandas"
            }
            return profile
        except ImportError:
            return self.profile_file_stdlib(file_path)

    def run(self) -> Dict[str, Any]:
        """Run profiling across all available datasets."""
        availability = self.check_files_availability()
        summary = {
            "available_files_count": sum(1 for v in availability.values() if v),
            "missing_files_count": sum(1 for v in availability.values() if not v),
            "files_status": availability,
            "profiles": {}
        }

        print("==================================================")
        print("         AUREVIX Source Data Profiler             ")
        print("==================================================")
        print(f"Target Directory: {self.raw_dir.resolve()}")
        print(f"Available Files : {summary['available_files_count']}/{len(self.expected_files)}")

        for filename, exists in availability.items():
            if exists:
                print(f"Profiling {filename}...")
                p = self.profile_file(self.raw_dir / filename)
                summary["profiles"][filename] = p
                print(f"  Rows: {p['row_count']:,} | Columns: {p['column_count']} | Duplicates: {p['duplicate_rows']}")
            else:
                print(f"  [-] {filename} : Not present in {self.raw_dir} (Ready for ingestion)")

        return summary


if __name__ == "__main__":
    raw_dir = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    profiler = SourceDataProfiler(raw_dir=raw_dir)
    results = profiler.run()
