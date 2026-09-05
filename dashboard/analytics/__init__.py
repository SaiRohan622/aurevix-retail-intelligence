"""
AUREVIX — Dynamic Central Analytics Package
Exports all modular analytics engines, diagnostic tools, and the central AnalyticsManager.
"""

from dashboard.analytics.universal_analytics import UniversalAnalytics, UniversalAnalyticsContext
from dashboard.analytics.column_mapper import ColumnMapper
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.insight_engine import InsightEngine
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.forecast_engine import ForecastEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.story_engine import DataStoryEngine
from dashboard.analytics.recommendation_engine import RecommendationEngine
from dashboard.analytics.kpi_explainer import KPIExplainer

__all__ = [
    "UniversalAnalytics",
    "UniversalAnalyticsContext",
    "ColumnMapper",
    "SchemaDetector",
    "DataProfiler",
    "MetricEngine",
    "InsightEngine",
    "AnomalyEngine",
    "AskYourDataEngine",
    "ExecutiveReportGenerator",
    "ChartEngine",
    "UniversalDataLoader",
    "AnalyticsManager",
    "WorkspaceManager",
    "ComparisonEngine",
    "ForecastEngine",
    "TargetEngine",
    "DataStoryEngine",
    "RecommendationEngine",
    "KPIExplainer"
]
