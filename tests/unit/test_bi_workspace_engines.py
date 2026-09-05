"""
AUREVIX — Advanced BI Workspace Test Suite
Validates Workspaces, Multi-Dimensional Comparisons, Statistical Forecasting, Targets, Data Stories, Recommendations, and KPI Explainability.
"""

from pathlib import Path
import pandas as pd
import pytest
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.forecast_engine import ForecastEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.story_engine import DataStoryEngine
from dashboard.analytics.recommendation_engine import RecommendationEngine
from dashboard.analytics.kpi_explainer import KPIExplainer
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager


def test_workspace_manager_lifecycle():
    ws = WorkspaceManager.save_workspace(
        name="Q3 Test Analysis",
        dataset_id="hash_test_123",
        dataset_name="test_sales.csv",
        filters={"category": "Apparel"},
        targets={"revenue": 500000.0},
        dashboard_layout=["kpis", "trend", "story"],
        notes="Q3 retail validation workspace"
    )

    assert ws["name"] == "Q3 Test Analysis"
    assert ws["workspace_id"] == "q3_test_analysis"
    assert ws["dataset_id"] == "hash_test_123"

    # List
    all_ws = WorkspaceManager.list_workspaces()
    assert any(w["workspace_id"] == "q3_test_analysis" for w in all_ws)

    # Load
    loaded = WorkspaceManager.load_workspace("q3_test_analysis")
    assert loaded is not None
    assert loaded["targets"]["revenue"] == 500000.0

    # Delete
    deleted = WorkspaceManager.delete_workspace("q3_test_analysis")
    assert deleted is True
    assert WorkspaceManager.load_workspace("q3_test_analysis") is None


def test_comparison_engine_dimensions():
    df = pd.DataFrame({
        "Category": ["Apparel", "Apparel", "Electronics", "Electronics"],
        "Sales": [100.0, 150.0, 300.0, 200.0]
    })

    res = ComparisonEngine.compare_dimensions(df, "Category", "Electronics", "Apparel", "Sales")
    assert res["available"] is True
    assert res["val_a"] == 500.0
    assert res["val_b"] == 250.0
    assert res["diff_abs"] == 250.0
    assert res["diff_pct"] == 100.0
    assert res["leader"] == "Electronics"


def test_comparison_engine_periods():
    dates = pd.date_range("2024-01-01", periods=6, freq="MS")
    sales = [100.0, 100.0, 100.0, 200.0, 200.0, 200.0]
    df = pd.DataFrame({"Date": dates, "Sales": sales})

    res = ComparisonEngine.compare_periods(df, "Date", "Sales")
    assert res["available"] is True
    assert res["p1_val"] == 300.0
    assert res["p2_val"] == 600.0
    assert res["diff_pct"] == 100.0
    assert res["growth"] is True


def test_forecast_engine_projection():
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    sales = [1000.0 + (i * 100.0) for i in range(12)] # Upward trend: 1000 to 2100
    df = pd.DataFrame({"OrderDate": dates, "Revenue": sales})

    res = ForecastEngine.generate_forecast(df, "OrderDate", "Revenue", horizon=3)
    assert res["available"] is True
    assert res["trend_slope"] == "Upward"
    assert res["next_period_val"] > 2100.0
    assert res["figure"] is not None


def test_forecast_engine_insufficient_data():
    dates = pd.date_range("2023-01-01", periods=2, freq="MS")
    df = pd.DataFrame({"OrderDate": dates, "Revenue": [100.0, 200.0]})

    res = ForecastEngine.generate_forecast(df, "OrderDate", "Revenue", horizon=3)
    assert res["available"] is False
    assert "insufficient" in res["reason"].lower() or "at least 4" in res["reason"].lower()


def test_target_engine_evaluation():
    # 1. On Track / Attained
    res1 = TargetEngine.evaluate_target(850000.0, 1000000.0, "Revenue")
    assert res1["has_target"] is True
    assert res1["attainment_pct"] == 85.0
    assert res1["status"] == "ON TRACK"
    assert res1["remaining"] == 150000.0

    # 2. Exceeded
    res2 = TargetEngine.evaluate_target(1200000.0, 1000000.0, "Revenue")
    assert res2["status"] == "EXCEEDED"
    assert res2["remaining"] == 0.0


def test_data_story_engine_generation():
    sample_path = Path("data/samples/retail_sales.csv")
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    res = AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)

    story = DataStoryEngine.generate_story(res, df, active_filters={"Region": "North"})
    assert len(story) >= 4
    assert any("Performance" in ch["title"] for ch in story)
    assert any("North" in ch["narrative"] for ch in story)


def test_recommendation_engine_domains():
    # HR domain
    hr_recs = RecommendationEngine.get_analyst_recommendations("HR / Workforce Analytics", {})
    assert any("salary" in r.lower() or "compensation" in r.lower() for r in hr_recs)

    # Marketing domain
    mkt_recs = RecommendationEngine.get_analyst_recommendations("Marketing & Campaigns", {})
    assert any("campaign" in r.lower() or "conversion" in r.lower() for r in mkt_recs)


def test_kpi_explainer():
    exp = KPIExplainer.explain_kpi("GROSS REVENUE", "sales_amount", "SUM(sales_amount)", 125430, {"Region": "South"})
    assert exp["kpi_name"] == "GROSS REVENUE"
    assert exp["source_column"] == "sales_amount"
    assert "Region = South" in exp["active_filters"]
    assert "125,430" in exp["rows_included"]
