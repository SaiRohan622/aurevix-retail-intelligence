"""
AUREVIX — Next-Generation Business Intelligence Platform Test Suite
Tests Schema Intelligence, Dynamic KPIs, Chart Recommendations, Autonomous Insights,
Hierarchical Drill-Down, Why Analysis, AI Business Analyst, Target Tracking, Forecasting, and Audit Governance.
"""
import pytest
import pandas as pd
import numpy as np

from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.insight_engine import InsightEngine
from dashboard.analytics.drilldown_engine import DrillDownEngine
from dashboard.analytics.kpi_explainer import KPIExplainer
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.forecast_engine import ForecastEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.audit_trail import AuditTrail
from dashboard.analytics.data_cache import AnalyticsManager


@pytest.fixture(autouse=True)
def reset_state():
    AnalyticsManager.revert_to_demo()
    AuditTrail.clear_logs()
    yield
    AnalyticsManager.revert_to_demo()
    AuditTrail.clear_logs()


def test_schema_intelligence_column_classification():
    df = pd.DataFrame({
        "order_id": [f"ORD_{i:04d}" for i in range(100)],
        "order_date": pd.date_range("2024-01-01", periods=100, freq="D").astype(str),
        "customer_city": [["New York", "London", "Tokyo"][i % 3] for i in range(100)],
        "revenue": np.random.uniform(50, 500, 100).round(2),
        "discount_rate": np.random.uniform(0.05, 0.25, 100).round(2),
        "is_priority": [i % 2 == 0 for i in range(100)],
        "product_category": [["Laptops", "Phones", "Accessories"][i % 3] for i in range(100)]
    })

    schema = SchemaDetector.detect_schema(df)
    cols = schema["columns"]

    assert cols["order_id"]["semantic_type"] == "id"
    assert cols["order_date"]["semantic_type"] == "date"
    assert cols["customer_city"]["fine_type"] == "geographic"
    assert cols["revenue"]["fine_type"] == "currency"
    assert cols["discount_rate"]["fine_type"] == "percentage"
    assert cols["is_priority"]["semantic_type"] == "boolean"
    assert schema["domain"] == "Retail & E-Commerce"


def test_hr_workforce_dynamic_kpis():
    hr_df = pd.DataFrame({
        "emp_id": [f"E{i:03d}" for i in range(50)],
        "salary": np.random.uniform(50000, 120000, 50).round(2),
        "department": [["Engineering", "Marketing", "Sales", "HR"][i % 4] for i in range(50)],
        "joining_date": pd.date_range("2021-01-01", periods=50, freq="W").astype(str)
    })

    schema = SchemaDetector.detect_schema(hr_df)
    assert schema["domain"] == "HR / Workforce Analytics"

    metrics = MetricEngine.calculate_metrics(hr_df, schema)
    cards = metrics.get("kpi_cards", [])
    labels = [c["label"] for c in cards]

    assert "Total Headcount" in labels
    assert "Average Compensation" in labels
    assert "Total Payroll Commitment" in labels
    assert "Active Departments" in labels


def test_automatic_chart_recommendations():
    df = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=60, freq="D").astype(str),
        "category": [["Apparel", "Beauty", "Home"][i % 3] for i in range(60)],
        "region": [["North", "South"][i % 2] for i in range(60)],
        "sales": np.random.uniform(100, 1000, 60),
        "profit": np.random.uniform(10, 200, 60)
    })

    schema = SchemaDetector.detect_schema(df)
    metrics = MetricEngine.calculate_metrics(df, schema)
    recs = ChartEngine.recommend_visualizations(df, schema, metrics)

    assert len(recs) >= 3
    rec_types = [r["chart_type"] for r in recs]
    assert "Area / Trend Chart" in rec_types
    assert "Ranked Bar Chart" in rec_types
    assert "Scatter Plot" in rec_types


def test_hierarchical_drilldown_time_and_dimension():
    df = pd.DataFrame({
        "tx_date": pd.date_range("2024-01-01", periods=120, freq="D").astype(str),
        "department": [["Tech", "Retail"][i % 2] for i in range(120)],
        "sub_category": [["Laptops", "Mice", "Shirts", "Pants"][i % 4] for i in range(120)],
        "amount": np.random.uniform(10, 100, 120)
    })
    schema = SchemaDetector.detect_schema(df)
    hierarchies = DrillDownEngine.get_supported_hierarchies(df, schema)

    assert "Time Hierarchy" in hierarchies
    assert "Product Hierarchy" in hierarchies

    # Drill into time month
    time_res = DrillDownEngine.drill_into_time(df, "tx_date", "amount", level="Month")
    assert len(time_res["data"]) >= 3

    # Drill into department
    dim_res = DrillDownEngine.drill_into_dimension(df, "department", "sub_category", "Tech", "amount")
    assert len(dim_res["data"]) >= 1


def test_why_analysis_driver_decomposition():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=100, freq="D").astype(str),
        "category": [["Laptops", "Books"][i % 2] for i in range(100)],
        "revenue": [100.0 if i < 50 else 20.0 for i in range(100)]
    })
    why_res = KPIExplainer.explain_why_variance(df, "revenue", "date", "category")
    assert why_res["available"] is True
    assert len(why_res["drivers"]) >= 1


def test_ai_business_analyst_qa():
    df = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=50, freq="D").astype(str),
        "category": [["Electronics", "Apparel"][i % 2] for i in range(50)],
        "sales": [500 if i % 2 == 0 else 100 for i in range(50)]
    })
    schema = SchemaDetector.detect_schema(df)
    metrics = MetricEngine.calculate_metrics(df, schema)

    # 1. Total sales question
    ans1 = AskYourDataEngine.answer_question(df, "What are my total sales?", schema, metrics)
    assert "total" in ans1["answer"].lower()

    # 2. Best category
    ans2 = AskYourDataEngine.answer_question(df, "Which category is performing best?", schema, metrics)
    assert "electronics" in ans2["answer"].lower()

    # 3. Why analysis query
    ans3 = AskYourDataEngine.answer_question(df, "Why did sales fall?", schema, metrics)
    assert "analytical driver" in ans3["answer"].lower()


def test_target_tracking_and_statuses():
    res_achieved = TargetEngine.evaluate_target(120000, 100000, "Revenue")
    assert res_achieved["status"] in ["ACHIEVED", "EXCEEDED"]

    res_on_track = TargetEngine.evaluate_target(85000, 100000, "Revenue")
    assert res_on_track["status"] == "ON TRACK"

    res_at_risk = TargetEngine.evaluate_target(65000, 100000, "Revenue")
    assert res_at_risk["status"] == "AT RISK"

    res_behind = TargetEngine.evaluate_target(30000, 100000, "Revenue")
    assert res_behind["status"] == "BEHIND"


def test_statistical_forecast_engine():
    dates = pd.date_range("2023-01-01", periods=12, freq="MS").astype(str)
    df = pd.DataFrame({
        "order_date": dates,
        "revenue": [10000 + i * 1500 for i in range(12)]
    })
    fore_res = ForecastEngine.generate_forecast(df, "order_date", "revenue", horizon=3)
    assert fore_res["available"] is True
    assert fore_res["figure"] is not None


def test_audit_trail_logging():
    AuditTrail.log_event("TEST_EVENT", "hash_test_123", "Test details recorded")
    logs = AuditTrail.get_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["action"] == "TEST_EVENT"
    assert "hash_test" in logs[0]["dataset_id"]
