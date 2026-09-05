"""
AUREVIX — Universal Analytics Architecture & Central Analytical Contract
Standardized end-to-end data pipeline orchestrator and single universal dataset context.

Pipeline Flow:
UPLOAD -> DATA LOADER -> SCHEMA DETECTION -> DATA QUALITY PROFILING ->
DATA CLEANING -> COLUMN SEMANTICS -> DATASET FINGERPRINT -> KPI ENGINE ->
CHART ENGINE -> INSIGHT ENGINE -> ANOMALY ENGINE -> NLP / ASK YOUR DATA -> EXPORT
"""
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
import numpy as np

from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.insight_engine import InsightEngine
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.audit_trail import AuditTrail
from dashboard.analytics.data_cache import AnalyticsManager


@dataclass
class UniversalAnalyticsContext:
    """
    Standardized universal dataset contract encapsulating data, semantics,
    data quality, cleaning history, KPIs, insights, anomalies, and active slices.
    """
    dataframe: pd.DataFrame
    original_dataframe: pd.DataFrame
    dataset_id: str
    dataset_name: str
    row_count: int
    column_count: int
    schema: Dict[str, Any]
    semantic_columns: Dict[str, str]
    quality_profile: Dict[str, Any]
    cleaning_state: Dict[str, Any] = field(default_factory=dict)
    available_metrics: List[str] = field(default_factory=list)
    available_dimensions: List[str] = field(default_factory=list)
    date_columns: List[str] = field(default_factory=list)
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    id_columns: List[str] = field(default_factory=list)
    currency_columns: List[str] = field(default_factory=list)
    percentage_columns: List[str] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    generated_kpis: Dict[str, Any] = field(default_factory=dict)
    generated_insights: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    cached_aggregations: Dict[str, Any] = field(default_factory=dict)
    domain: str = "Enterprise Operations / General Tabular"
    domain_confidence: int = 50
    is_user_mode: bool = True
    analysis_time_ms: float = 0.0

    @property
    def is_empty(self) -> bool:
        return self.dataframe is None or self.dataframe.empty

    @property
    def quality_score(self) -> float:
        return float(self.quality_profile.get("quality_score", 100.0))

    @property
    def primary_metric(self) -> Optional[str]:
        return self.generated_kpis.get("primary_metric_col") or (self.numeric_columns[0] if self.numeric_columns else None)

    @property
    def primary_date(self) -> Optional[str]:
        return self.generated_kpis.get("date_col") or (self.date_columns[0] if self.date_columns else None)

    @property
    def primary_category(self) -> Optional[str]:
        return self.generated_kpis.get("category_col") or (self.categorical_columns[0] if self.categorical_columns else None)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the analytics context to a dictionary representation."""
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "domain": self.domain,
            "domain_confidence": self.domain_confidence,
            "is_user_mode": self.is_user_mode,
            "schema": self.schema,
            "profile": self.quality_profile,
            "kpis": self.generated_kpis,
            "insights": self.generated_insights,
            "anomalies": self.anomalies,
            "available_metrics": self.available_metrics,
            "available_dimensions": self.available_dimensions,
            "date_columns": self.date_columns,
            "active_filters": self.active_filters,
            "cleaning_steps_count": len(self.cleaning_state.get("recipe", [])),
            "analysis_time_ms": self.analysis_time_ms,
        }

    def get_column_semantic_type(self, col: str) -> str:
        return self.semantic_columns.get(col, "unknown")

    def get_summary_report(self) -> str:
        return ExecutiveReportGenerator.generate_report(self.to_dict(), self.dataframe)


class UniversalAnalytics:
    """
    Central orchestrator implementing the Universal Analytics Contract.
    Standardizes ingestion, classification, profiling, KPIs, insights, and queries.
    """

    @classmethod
    def compute_fingerprint(cls, df: pd.DataFrame, filename: str = "", extra_meta: Optional[Dict] = None) -> str:
        """Generates a deterministic SHA-256 fingerprint for a DataFrame and its metadata."""
        if df is None or df.empty:
            return "empty_dataset"
        
        hasher = hashlib.sha256()
        hasher.update(filename.encode("utf-8"))
        hasher.update(str(len(df)).encode("utf-8"))
        hasher.update(str(len(df.columns)).encode("utf-8"))
        hasher.update(",".join(sorted(str(c) for c in df.columns)).encode("utf-8"))
        
        # Sample representative values
        sample_str = str(df.head(5).to_dict())
        hasher.update(sample_str.encode("utf-8", errors="ignore"))
        
        if extra_meta:
            hasher.update(str(sorted(extra_meta.items())).encode("utf-8"))
            
        return hasher.hexdigest()[:16]

    @classmethod
    def build_context(
        cls,
        df: pd.DataFrame,
        filename: str = "dataset.csv",
        file_hash: Optional[str] = None,
        data_source: str = "user_upload",
        original_df: Optional[pd.DataFrame] = None
    ) -> UniversalAnalyticsContext:
        """Executes the complete universal analytics pipeline on a DataFrame."""
        t0 = time.time()
        
        if df is None or df.empty:
            return UniversalAnalyticsContext(
                dataframe=pd.DataFrame(),
                original_dataframe=pd.DataFrame(),
                dataset_id=file_hash or "empty",
                dataset_name=filename,
                row_count=0,
                column_count=0,
                schema={},
                semantic_columns={},
                quality_profile={},
                domain="Empty Dataset",
                is_user_mode=False
            )

        fhash = file_hash or cls.compute_fingerprint(df, filename)
        orig_df = original_df if original_df is not None else df.copy()

        # 1. Schema Detection & Semantic Column Inference
        schema_meta = SchemaDetector.detect_schema(df)
        sem_cols = {
            col: meta.get("fine_type", meta.get("semantic_type", "unknown"))
            for col, meta in schema_meta.get("columns", {}).items()
        }

        # 2. Data Quality Profiling (4 Pillars)
        profile_meta = DataProfiler.profile(df, schema_meta)

        # 3. Dynamic Domain-Aware KPIs
        metrics = MetricEngine.calculate_metrics(df, schema_meta)

        # 4. Business Insights & Anomaly Detection
        insights = InsightEngine.generate_insights(df, schema_meta, metrics)
        anomalies = AnomalyEngine.detect_anomalies(df, schema_meta, metrics)

        duration_ms = round((time.time() - t0) * 1000, 2)

        return UniversalAnalyticsContext(
            dataframe=df,
            original_dataframe=orig_df,
            dataset_id=fhash,
            dataset_name=filename,
            row_count=len(df),
            column_count=len(df.columns),
            schema=schema_meta,
            semantic_columns=sem_cols,
            quality_profile=profile_meta,
            cleaning_state={"recipe": [], "version": 1},
            available_metrics=schema_meta.get("numeric_columns", []),
            available_dimensions=schema_meta.get("categorical_columns", []),
            date_columns=schema_meta.get("date_columns", []),
            numeric_columns=schema_meta.get("numeric_columns", []),
            categorical_columns=schema_meta.get("categorical_columns", []),
            id_columns=schema_meta.get("id_columns", []),
            currency_columns=schema_meta.get("currency_columns", []),
            percentage_columns=schema_meta.get("percentage_columns", []),
            active_filters={},
            generated_kpis=metrics,
            generated_insights=insights,
            anomalies=anomalies,
            cached_aggregations={},
            domain=schema_meta.get("domain", "Enterprise Operations / General Tabular"),
            domain_confidence=schema_meta.get("domain_confidence", 50),
            is_user_mode=True,
            analysis_time_ms=duration_ms
        )

    @classmethod
    def get_active_context(cls) -> UniversalAnalyticsContext:
        """Retrieves the current UniversalAnalyticsContext from session state."""
        AnalyticsManager.initialize()
        df = AnalyticsManager.get_active_df()
        orig_df = AnalyticsManager.get_original_raw_df()
        res = AnalyticsManager.get_analysis_results()
        ws_state = AnalyticsManager.get_workspace_state()

        if not ws_state.get("user_mode") or df.empty:
            return UniversalAnalyticsContext(
                dataframe=pd.DataFrame(),
                original_dataframe=pd.DataFrame(),
                dataset_id="demo_mode",
                dataset_name="Demo Dataset",
                row_count=0,
                column_count=0,
                schema=res.get("schema", {}),
                semantic_columns={},
                quality_profile=res.get("profile", {}),
                generated_kpis=res.get("kpis", {}),
                generated_insights=res.get("insights", []),
                anomalies=res.get("anomalies", []),
                domain="Demo",
                is_user_mode=False
            )

        schema = res.get("schema", {})
        sem_cols = {
            col: meta.get("fine_type", meta.get("semantic_type", "unknown"))
            for col, meta in schema.get("columns", {}).items()
        }

        return UniversalAnalyticsContext(
            dataframe=df,
            original_dataframe=orig_df,
            dataset_id=res.get("dataset_id", "active_id"),
            dataset_name=res.get("dataset_name", "active_dataset"),
            row_count=len(df),
            column_count=len(df.columns),
            schema=schema,
            semantic_columns=sem_cols,
            quality_profile=res.get("profile", {}),
            cleaning_state={"recipe": AnalyticsManager.get_cleaning_recipe(), "version": AnalyticsManager.get_dataset_version()},
            available_metrics=schema.get("numeric_columns", []),
            available_dimensions=schema.get("categorical_columns", []),
            date_columns=schema.get("date_columns", []),
            numeric_columns=schema.get("numeric_columns", []),
            categorical_columns=schema.get("categorical_columns", []),
            id_columns=schema.get("id_columns", []),
            currency_columns=schema.get("currency_columns", []),
            percentage_columns=schema.get("percentage_columns", []),
            active_filters=ws_state.get("active_filters", {}),
            generated_kpis=res.get("kpis", {}),
            generated_insights=res.get("insights", []),
            anomalies=res.get("anomalies", []),
            cached_aggregations={},
            domain=schema.get("domain", "Enterprise Operations"),
            domain_confidence=schema.get("domain_confidence", 85),
            is_user_mode=True,
            analysis_time_ms=res.get("analysis_time_ms", 0.0)
        )

    @classmethod
    def activate(cls, df: pd.DataFrame, filename: str, file_hash: Optional[str] = None, data_source: str = "user_upload") -> UniversalAnalyticsContext:
        """Activates a dataset into central session state and returns its UniversalAnalyticsContext."""
        fhash = file_hash or cls.compute_fingerprint(df, filename)
        AnalyticsManager.activate_user_dataset(df, filename, fhash, data_source=data_source)
        return cls.get_active_context()

    @classmethod
    def clear(cls) -> None:
        """Clears active dataset and resets session state to clean demo baseline."""
        AnalyticsManager.clear_active_dataset()
