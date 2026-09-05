"""
AUREVIX — Universal Analytics Architecture & Multi-Domain Contract Test Suite
Verifies schema intelligence, fine-grained semantics, multi-domain KPIs, dataset fingerprinting,
dataset switching isolation, NLP intelligence, high-cardinality protection, and error-proofing.
"""
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from dashboard.analytics.universal_analytics import UniversalAnalytics, UniversalAnalyticsContext
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.data_cache import AnalyticsManager


# -----------------------------------------------------------------------------
# 1. UNIVERSAL CONTRACT & CONTEXT CREATION
# -----------------------------------------------------------------------------

def test_universal_context_creation():
    df = pd.DataFrame({
        "order_id": [101, 102, 103],
        "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "category": ["Electronics", "Apparel", "Electronics"],
        "sales": [500.0, 150.0, 300.0]
    })
    ctx = UniversalAnalytics.build_context(df, "sales_data.csv")
    
    assert isinstance(ctx, UniversalAnalyticsContext)
    assert ctx.dataset_name == "sales_data.csv"
    assert ctx.row_count == 3
    assert ctx.column_count == 4
    assert ctx.is_user_mode is True
    assert ctx.quality_score > 90.0
    assert "sales" in ctx.numeric_columns
    assert "category" in ctx.categorical_columns
    assert "order_date" in ctx.date_columns
    assert ctx.generated_kpis.get("total_revenue") == 950.0


def test_empty_dataset_context():
    df_empty = pd.DataFrame()
    ctx = UniversalAnalytics.build_context(df_empty, "empty.csv")
    assert ctx.is_empty is True
    assert ctx.row_count == 0
    assert ctx.column_count == 0
    assert ctx.primary_metric is None


# -----------------------------------------------------------------------------
# 2. FINE-GRAINED SEMANTIC CLASSIFICATION
# -----------------------------------------------------------------------------

def test_fine_grained_semantic_types():
    df = pd.DataFrame({
        "emp_id": ["E001", "E002", "E003", "E004"],
        "email": ["alice@company.com", "bob@company.com", "charlie@company.com", "david@company.com"],
        "phone": ["+1-555-0192", "+1-555-0193", "+1-555-0194", "+1-555-0195"],
        "is_active": [True, True, False, True],
        "hire_date": ["2022-03-15", "2021-06-01", "2023-01-10", "2020-11-20"],
        "salary": ["$95,000", "$110,000", "$85,000", "$130,000"],
        "commission_rate": [0.05, 0.08, 0.04, 0.10],
        "years_experience": [3, 7, 2, 12],
        "performance_score": [4.2, 4.8, 3.9, 4.9],
        "department": ["Engineering", "Sales", "Support", "Engineering"],
        "notes": [
            "Senior software engineer leading platform reliability and architecture.",
            "Account executive exceeding annual quota for enterprise clients.",
            "Customer support engineer with high satisfaction scores.",
            "Principal architect designing distributed streaming systems."
        ]
    })
    schema = SchemaDetector.detect_schema(df)
    cols = schema["columns"]

    assert cols["emp_id"]["fine_type"] == "id"
    assert cols["email"]["fine_type"] == "email"
    assert cols["phone"]["fine_type"] == "phone"
    assert cols["is_active"]["fine_type"] == "boolean"
    assert cols["hire_date"]["fine_type"] in ["date", "datetime"]
    assert cols["salary"]["fine_type"] == "currency"
    assert cols["commission_rate"]["fine_type"] == "percentage"
    assert cols["years_experience"]["fine_type"] == "integer"
    assert cols["performance_score"]["fine_type"] == "float"
    assert cols["department"]["fine_type"] == "categorical"
    assert cols["notes"]["fine_type"] == "text"


# -----------------------------------------------------------------------------
# 3. MULTI-DOMAIN KPI ENGINES
# -----------------------------------------------------------------------------

def test_hr_workforce_kpi_model():
    df_hr = pd.DataFrame({
        "emp_id": [f"E{i:03d}" for i in range(1, 21)],
        "department": ["Engineering"] * 8 + ["Sales"] * 6 + ["Marketing"] * 4 + ["HR"] * 2,
        "salary": [100000 + i * 5000 for i in range(20)],
        "hire_date": pd.date_range("2021-01-01", periods=20, freq="60D")
    })
    schema = SchemaDetector.detect_schema(df_hr)
    assert "HR" in schema["domain"]
    
    kpis = MetricEngine.calculate_metrics(df_hr, schema)
    assert kpis["total_revenue"] == sum([100000 + i * 5000 for i in range(20)])
    assert kpis["unique_categories"] == 4  # 4 departments
    
    card_ids = [c["id"] for c in kpis.get("kpi_cards", [])]
    assert "headcount" in card_ids
    assert "avg_salary" in card_ids
    assert "departments" in card_ids


def test_marketing_campaign_kpi_model():
    df_mkt = pd.DataFrame({
        "campaign": ["Summer Promo", "Fall Launch", "Retargeting", "Brand Awareness"],
        "channel": ["Google Ads", "Meta Ads", "LinkedIn", "YouTube"],
        "ad_spend": [15000.0, 22000.0, 12000.0, 8000.0],
        "conversions": [450, 680, 210, 140]
    })
    schema = SchemaDetector.detect_schema(df_mkt)
    assert "Marketing" in schema["domain"]
    
    kpis = MetricEngine.calculate_metrics(df_mkt, schema)
    card_ids = [c["id"] for c in kpis.get("kpi_cards", [])]
    assert "total_spend" in card_ids
    assert "campaigns" in card_ids
    assert "channels" in card_ids


def test_inventory_supply_chain_kpi_model():
    df_inv = pd.DataFrame({
        "sku": [f"SKU-{i:04d}" for i in range(1, 16)],
        "warehouse": ["WH-East"] * 5 + ["WH-West"] * 5 + ["WH-Central"] * 5,
        "quantity_on_hand": [50, 120, 0, 45, 300, 15, 80, 200, 10, 5, 400, 25, 60, 90, 110],
        "inventory_value": [2500.0, 6000.0, 0.0, 2250.0, 15000.0, 750.0, 4000.0, 10000.0, 500.0, 250.0, 20000.0, 1250.0, 3000.0, 4500.0, 5500.0]
    })
    schema = SchemaDetector.detect_schema(df_inv)
    assert "Inventory" in schema["domain"]
    
    kpis = MetricEngine.calculate_metrics(df_inv, schema)
    card_ids = [c["id"] for c in kpis.get("kpi_cards", [])]
    assert "inventory_units" in card_ids
    assert "inventory_value" in card_ids


def test_financial_banking_kpi_model():
    df_fin = pd.DataFrame({
        "account": ["Operating", "Payroll", "Treasury", "Capital"],
        "income": [500000.0, 300000.0, 150000.0, 800000.0],
        "expense": [350000.0, 280000.0, 50000.0, 400000.0]
    })
    schema = SchemaDetector.detect_schema(df_fin)
    assert "Financial" in schema["domain"]


# -----------------------------------------------------------------------------
# 4. DATASET FINGERPRINTING & CACHE ISOLATION
# -----------------------------------------------------------------------------

def test_deterministic_fingerprint_repeatability():
    df1 = pd.DataFrame({"colA": [1, 2, 3], "colB": ["x", "y", "z"]})
    df2 = pd.DataFrame({"colA": [1, 2, 3], "colB": ["x", "y", "z"]})
    df3 = pd.DataFrame({"colA": [1, 2, 4], "colB": ["x", "y", "z"]})

    fp1 = UniversalAnalytics.compute_fingerprint(df1, "data.csv")
    fp2 = UniversalAnalytics.compute_fingerprint(df2, "data.csv")
    fp3 = UniversalAnalytics.compute_fingerprint(df3, "data.csv")

    assert fp1 == fp2
    assert fp1 != fp3


def test_dataset_switching_complete_isolation():
    """Proves Dataset A -> Dataset B -> Dataset A never leaks metrics across contexts."""
    df_a = pd.DataFrame({"dept": ["HR", "IT"], "salary": [60000.0, 90000.0]})
    df_b = pd.DataFrame({"channel": ["Google", "Meta"], "spend": [5000.0, 8000.0]})

    ctx_a = UniversalAnalytics.build_context(df_a, "dataset_a.csv")
    assert ctx_a.generated_kpis["total_revenue"] == 150000.0
    assert "HR" in ctx_a.categorical_columns or "dept" in ctx_a.categorical_columns

    ctx_b = UniversalAnalytics.build_context(df_b, "dataset_b.csv")
    assert ctx_b.generated_kpis["total_revenue"] == 13000.0
    assert "channel" in ctx_b.categorical_columns

    # Verify context A is completely untouched by context B
    assert ctx_a.generated_kpis["total_revenue"] == 150000.0
    assert "spend" not in ctx_a.numeric_columns


# -----------------------------------------------------------------------------
# 5. HIGH-CARDINALITY & CHART PROTECTION
# -----------------------------------------------------------------------------

def test_high_cardinality_donut_chart_protection():
    df_huge = pd.DataFrame({
        "customer_id": [f"CUST_{i:05d}" for i in range(1000)],
        "amount": [100.0 + i for i in range(1000)]
    })
    fig = ChartEngine.create_dimension_donut_chart(df_huge, "customer_id", "amount", top_n=5)
    assert fig is not None
    labels = list(fig.data[0].labels)
    assert len(labels) == 6  # Top 5 + "Other"
    assert labels[-1] == "Other"


def test_chart_engine_graceful_none_on_invalid_column():
    df = pd.DataFrame({"A": [1, 2, 3]})
    fig = ChartEngine.create_dimension_donut_chart(df, "NonExistentCol", "A")
    assert fig is None


# -----------------------------------------------------------------------------
# 6. UNIVERSAL NLP ASK YOUR DATA
# -----------------------------------------------------------------------------

def test_nlp_ask_your_data_across_domains():
    # 1. HR Query
    df_hr = pd.DataFrame({
        "department": ["Engineering", "Product", "Sales"],
        "salary": [120000.0, 110000.0, 95000.0]
    })
    ctx_hr = UniversalAnalytics.build_context(df_hr, "hr.csv")
    ans_hr = AskYourDataEngine.answer_question(
        df_hr, "What is the average salary?", ctx_hr.schema, ctx_hr.generated_kpis
    )
    assert "average" in ans_hr["answer"].lower()
    assert "salary" in ans_hr["answer"].lower()

    # 2. Marketing Query
    df_mkt = pd.DataFrame({
        "channel": ["Search", "Social", "Display"],
        "spend": [30000.0, 20000.0, 10000.0]
    })
    ctx_mkt = UniversalAnalytics.build_context(df_mkt, "mkt.csv")
    ans_mkt = AskYourDataEngine.answer_question(
        df_mkt, "What is the total spend?", ctx_mkt.schema, ctx_mkt.generated_kpis
    )
    assert "60,000" in ans_mkt["answer"]

    # 3. Missing Column Query
    ans_no_date = AskYourDataEngine.answer_question(
        df_mkt, "Show sales by month", ctx_mkt.schema, ctx_mkt.generated_kpis
    )
    assert "datetime column" in ans_no_date["answer"] or "can't answer" in ans_no_date["answer"]
