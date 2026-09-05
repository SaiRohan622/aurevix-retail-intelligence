"""
AUREVIX — Comprehensive Unit & Integration Tests for Generic BI Analytics Platform
Covers: Domain Intelligence, 4-Pillar Quality, Anomaly Detection, Ask Your Data NLP,
Executive Reporting, Dataset Switching, and Global Slicers.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pytest

from dashboard.analytics.column_mapper import ColumnMapper
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.insight_engine import InsightEngine
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager


@pytest.fixture(autouse=True)
def reset_analytics_state():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def test_retail_sales_analysis_and_domain():
    sample_path = Path("data/samples/retail_sales.csv")
    assert sample_path.exists()
    
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    assert len(df) == 36
    
    res = AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)
    assert AnalyticsManager.is_user_mode() is True
    assert res["dataset_name"] == "retail_sales.csv"
    assert res["kpis"]["primary_metric_col"] == "Sales"
    assert res["kpis"]["total_revenue"] > 100000
    assert res["schema"]["domain"] == "Retail & E-Commerce"
    assert res["profile"]["completeness_score"] == 100.0


def test_employee_dataset_analysis_and_domain():
    sample_path = Path("data/samples/employee_data.xlsx")
    assert sample_path.exists()

    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "employee_data.xlsx")
    assert len(df) == 50

    res = AnalyticsManager.activate_user_dataset(df, "employee_data.xlsx", fhash)
    assert AnalyticsManager.is_user_mode() is True
    assert res["dataset_name"] == "employee_data.xlsx"
    assert res["kpis"]["primary_metric_col"] == "Salary"
    assert res["schema"]["domain"] == "HR / Workforce Analytics"
    assert res["kpis"]["category_col"] == "Department"
    assert res["kpis"]["region_col"] == "Location"


def test_marketing_campaign_analysis_and_domain():
    sample_path = Path("data/samples/marketing_campaign.csv")
    assert sample_path.exists()

    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "marketing_campaign.csv")
    assert len(df) == 30

    res = AnalyticsManager.activate_user_dataset(df, "marketing_campaign.csv", fhash)
    assert AnalyticsManager.is_user_mode() is True
    assert res["schema"]["domain"] == "Marketing & Campaigns"
    assert res["kpis"]["category_col"] == "Channel"


def test_ask_your_data_nlp_query():
    sample_path = Path("data/samples/retail_sales.csv")
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    res = AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)

    # 1. Ask about highest revenue category
    ans1 = AskYourDataEngine.answer_question(df, "Which category generated the highest revenue?", res["schema"], res["kpis"])
    assert "top" in ans1["answer"].lower() or "apparel" in ans1["answer"].lower()
    assert ans1["figure"] is not None

    # 2. Ask about monthly sales trend
    ans2 = AskYourDataEngine.answer_question(df, "Show monthly sales trend", res["schema"], res["kpis"])
    assert "time-series" in ans2["answer"].lower() or "sales" in ans2["answer"].lower()


def test_anomaly_detection_engine():
    # Construct dataframe with deliberate spike
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    vals = [1000.0] * 11 + [10000.0] # 10x spike in month 12
    df_spike = pd.DataFrame({"Date": dates, "Sales": vals, "Category": ["A"] * 12})
    
    schema = SchemaDetector.detect_schema(df_spike)
    metrics = MetricEngine.calculate_metrics(df_spike, schema)
    anomalies = AnomalyEngine.detect_anomalies(df_spike, schema, metrics)
    
    assert len(anomalies) > 0
    assert any(a["type"] == "spike" for a in anomalies)


def test_executive_report_generation():
    sample_path = Path("data/samples/retail_sales.csv")
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    res = AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)

    rep = ExecutiveReportGenerator.generate_report(res, df)
    assert "AUREVIX — Executive Business Intelligence Report" in rep
    assert "retail_sales.csv" in rep
    assert "Retail & E-Commerce" in rep


def test_dataset_filtering():
    sample_path = Path("data/samples/retail_sales.csv")
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)

    # Apply filter on Category = 'Apparel'
    AnalyticsManager.apply_filters({"Category": ["Apparel"]})
    df_filtered = AnalyticsManager.get_active_df()
    assert len(df_filtered) < len(df)
    assert set(df_filtered["Category"].unique()) == {"Apparel"}

    # Reset filter
    AnalyticsManager.apply_filters({})
    assert len(AnalyticsManager.get_active_df()) == len(df)


def test_dataset_switching_clears_stale_data():
    retail_path = Path("data/samples/retail_sales.csv")
    emp_path = Path("data/samples/employee_data.xlsx")

    # 1. Load Retail Sales
    df_ret, h_ret = UniversalDataLoader.load_and_fingerprint(str(retail_path), "retail_sales.csv")
    res_ret = AnalyticsManager.activate_user_dataset(df_ret, "retail_sales.csv", h_ret)
    assert res_ret["kpis"]["primary_metric_col"] == "Sales"

    # 2. Switch to Employee Data WITHOUT restarting session
    df_emp, h_emp = UniversalDataLoader.load_and_fingerprint(str(emp_path), "employee_data.xlsx")
    res_emp = AnalyticsManager.activate_user_dataset(df_emp, "employee_data.xlsx", h_emp)
    
    # 3. Assert NO retail columns or metrics exist in current results
    assert res_emp["dataset_name"] == "employee_data.xlsx"
    assert res_emp["kpis"]["primary_metric_col"] == "Salary"
    assert res_emp["kpis"]["category_col"] == "Department"
    assert "Sales" not in res_emp["schema"]["columns"]


def test_demo_mode_reversion_preserves_olist():
    sample_path = Path("data/samples/retail_sales.csv")
    df, fhash = UniversalDataLoader.load_and_fingerprint(str(sample_path), "retail_sales.csv")
    AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash)
    assert AnalyticsManager.is_user_mode() is True

    AnalyticsManager.revert_to_demo()
    assert AnalyticsManager.is_demo_mode() is True
    
    demo_res = AnalyticsManager.get_analysis_results()
    assert demo_res["dataset_name"] == "Olist Brazilian E-Commerce"
    assert round(demo_res["kpis"]["total_revenue"], 2) == 15843553.24
    assert demo_res["kpis"]["total_transactions"] == 98666
