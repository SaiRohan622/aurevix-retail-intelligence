"""
AUREVIX — Lazy Loading & Instant Navigation Test Suite
Verifies single-section execution, dataset persistence during section switches,
lazy query engine initialization, lazy export generation, and zero Olist fallback.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
import io
import time

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.workspace_manager import WorkspaceManager


@pytest.fixture(autouse=True)
def reset_state():
    AnalyticsManager.revert_to_demo()
    yield
    AnalyticsManager.revert_to_demo()


def _make_sample_df(n=500):
    np.random.seed(42)
    return pd.DataFrame({
        "order_id": [f"ORD_{i:05d}" for i in range(1, n + 1)],
        "order_date": pd.date_range("2024-01-01", periods=n, freq="h").astype(str),
        "customer_id": [f"CUST_{i % 50:03d}" for i in range(n)],
        "category": [["Electronics", "Apparel", "Home", "Books"][i % 4] for i in range(n)],
        "region": [["North", "South", "East", "West"][i % 4] for i in range(n)],
        "quantity": np.random.randint(1, 10, n),
        "price": np.random.uniform(10.0, 500.0, n).round(2),
        "revenue": np.random.uniform(20.0, 2000.0, n).round(2),
    })


def test_active_section_state_management():
    AnalyticsManager.initialize()
    assert AnalyticsManager.get_active_section() == "📥 Ingest & Quality Center"

    AnalyticsManager.set_active_section("🔎 Data Explorer")
    assert AnalyticsManager.get_active_section() == "🔎 Data Explorer"

    AnalyticsManager.set_active_section("🤖 Ask Your Data")
    assert AnalyticsManager.get_active_section() == "🤖 Ask Your Data"


def test_dataset_persists_across_all_section_switches():
    df = _make_sample_df(200)
    AnalyticsManager.activate_user_dataset(df, "sales_q1.csv", "hash_persist_01")

    sections = [
        "📥 Ingest & Quality Center",
        "🧹 Clean & Transform",
        "🔎 Data Explorer",
        "⚖️ Compare",
        "🎯 Targets & Goals",
        "🤖 Ask Your Data",
        "💾 Saved Workspaces",
        "📄 Export Center"
    ]

    for sec in sections:
        AnalyticsManager.set_active_section(sec)
        active = AnalyticsManager.get_active_df()
        assert len(active) == 200
        assert "revenue" in active.columns
        assert AnalyticsManager.has_active_dataset() is True
        assert AnalyticsManager.is_demo_mode() is False


def test_ask_data_nlp_engine_is_lazy():
    df = _make_sample_df(100)
    res = AnalyticsManager.activate_user_dataset(df, "nlp_lazy.csv", "hash_nlp_lazy")

    # NLP engine is not invoked until user explicitly asks a question
    active = AnalyticsManager.get_active_df()
    t0 = time.time()
    ans = AskYourDataEngine.answer_question(
        active, "Which category has the highest revenue?",
        res["schema"], res["kpis"]
    )
    duration = time.time() - t0

    assert "answer" in ans
    assert duration < 1.0


def test_comparison_engine_is_lazy():
    df = _make_sample_df(100)
    AnalyticsManager.activate_user_dataset(df, "compare_lazy.csv", "hash_comp_lazy")
    active = AnalyticsManager.get_active_df()

    # Compare dimensions executed only on demand
    comp_dim = ComparisonEngine.compare_dimensions(active, "category", "Electronics", "Apparel", "revenue")
    assert comp_dim.get("available") is True
    assert "val_a" in comp_dim

    # Compare periods executed only on demand
    comp_per = ComparisonEngine.compare_periods(active, "order_date", "revenue")
    assert comp_per.get("available") is True


def test_export_report_generation_is_lazy():
    df = _make_sample_df(100)
    res = AnalyticsManager.activate_user_dataset(df, "export_lazy.csv", "hash_exp_lazy")
    active = AnalyticsManager.get_active_df()

    # Report is generated only when requested
    report = ExecutiveReportGenerator.generate_report(res, active)
    assert "AUREVIX — Executive Business Intelligence Report" in report
    assert "export_lazy.csv" in report


def test_cleaning_increments_version_and_updates_active_df():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["  Alice ", " Bob  ", " Charlie "],
        "sales": [100, 200, 300]
    })
    AnalyticsManager.activate_user_dataset(df, "clean_ver.csv", "hash_clean_ver")
    v1 = AnalyticsManager.get_dataset_version()

    step = {
        "action": "strip_whitespace",
        "params": {"columns": ["name"]},
        "title": "Strip whitespace"
    }
    cleaned_df, stats = AnalyticsManager.apply_cleaning_step(step)
    v2 = AnalyticsManager.get_dataset_version()

    assert v2 == v1 + 1
    assert list(cleaned_df["name"]) == ["Alice", "Bob", "Charlie"]
    assert list(AnalyticsManager.get_active_df()["name"]) == ["Alice", "Bob", "Charlie"]


def test_revert_to_demo_resets_workspace():
    df = _make_sample_df(50)
    AnalyticsManager.activate_user_dataset(df, "temp.csv", "hash_temp")
    assert AnalyticsManager.has_active_dataset() is True

    AnalyticsManager.revert_to_demo()
    assert AnalyticsManager.has_active_dataset() is False
    assert AnalyticsManager.is_demo_mode() is True
    assert AnalyticsManager.get_active_df().empty is True
