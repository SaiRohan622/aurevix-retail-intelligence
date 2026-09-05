"""
AUREVIX — Chart Engine & Visualization Robustness Test Suite
Tests ChartEngine.create_dimension_donut_chart across normal, edge-case, and malformed datasets.
"""
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from dashboard.analytics.chart_engine import ChartEngine
from dashboard.components.charts import create_dimension_donut_chart as comp_create_donut


def test_donut_chart_valid_categorical_and_numeric():
    df = pd.DataFrame({
        "Category": ["Electronics", "Apparel", "Home", "Beauty", "Sports"],
        "Revenue": [5000.0, 3000.0, 2000.0, 1500.0, 800.0]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Revenue", top_n=5)
    assert fig is not None
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert list(fig.data[0].labels) == ["Electronics", "Apparel", "Home", "Beauty", "Sports"]


def test_donut_chart_top_n_and_other_aggregation():
    df = pd.DataFrame({
        "Category": [f"Cat_{i}" for i in range(10)],
        "Revenue": [1000 - i * 50 for i in range(10)]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Revenue", top_n=4)
    assert fig is not None
    labels = list(fig.data[0].labels)
    assert len(labels) == 5  # Top 4 + "Other"
    assert labels[-1] == "Other"
    assert fig.data[0].values[-1] == sum([1000 - i * 50 for i in range(4, 10)])


def test_donut_chart_missing_and_null_categories():
    df = pd.DataFrame({
        "Category": ["Laptops", None, np.nan, "Phones", ""],
        "Sales": [1000.0, 200.0, 300.0, 800.0, 150.0]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Sales", top_n=5)
    assert fig is not None
    labels = list(fig.data[0].labels)
    assert "Unspecified" in labels
    assert "Laptops" in labels
    assert "Phones" in labels


def test_donut_chart_currency_and_comma_strings():
    df = pd.DataFrame({
        "Department": ["Engineering", "Sales", "Support", "Marketing"],
        "Budget": ["$1,250,000.00", "$850,000", " $450,000 ", "€300,000"]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Department", "Budget", top_n=4)
    assert fig is not None
    assert len(fig.data[0].labels) == 4
    assert fig.data[0].values[0] == 1250000.0


def test_donut_chart_empty_dataframe():
    df_empty = pd.DataFrame()
    fig = ChartEngine.create_dimension_donut_chart(df_empty, "Category", "Revenue")
    assert fig is None


def test_donut_chart_none_input():
    fig = ChartEngine.create_dimension_donut_chart(None, "Category", "Revenue")
    assert fig is None


def test_donut_chart_missing_category_column():
    df = pd.DataFrame({"Wrong_Col": [1, 2, 3], "Revenue": [10, 20, 30]})
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Revenue")
    assert fig is None


def test_donut_chart_missing_metric_column_defaults_to_count():
    df = pd.DataFrame({
        "Category": ["Electronics", "Electronics", "Apparel", "Apparel", "Apparel"]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", metric_column=None)
    assert fig is not None
    labels = list(fig.data[0].labels)
    assert labels == ["Apparel", "Electronics"]
    assert list(fig.data[0].values) == [3.0, 2.0]


def test_donut_chart_single_category():
    df = pd.DataFrame({
        "Category": ["Monolithic", "Monolithic", "Monolithic"],
        "Revenue": [100.0, 200.0, 300.0]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Revenue")
    assert fig is not None
    assert list(fig.data[0].labels) == ["Monolithic"]
    assert fig.data[0].values[0] == 600.0


def test_donut_chart_negative_and_zero_values():
    df = pd.DataFrame({
        "Category": ["Profit_A", "Profit_B", "Loss_C", "Zero_D"],
        "Net": [500.0, 300.0, -200.0, 0.0]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Net")
    assert fig is not None
    labels = list(fig.data[0].labels)
    # Negative and Zero slices are excluded from donut proportionality
    assert "Loss_C" not in labels
    assert "Zero_D" not in labels
    assert labels == ["Profit_A", "Profit_B"]


def test_donut_chart_all_negative_returns_none():
    df = pd.DataFrame({
        "Category": ["Loss_1", "Loss_2"],
        "Net": [-100.0, -50.0]
    })
    fig = ChartEngine.create_dimension_donut_chart(df, "Category", "Net")
    assert fig is None


def test_donut_chart_hr_dataset():
    df_hr = pd.DataFrame({
        "Department": ["Engineering", "Product", "Sales", "HR"],
        "Salary": [120000, 110000, 95000, 75000]
    })
    fig = ChartEngine.create_dimension_donut_chart(df_hr, "Department", "Salary")
    assert fig is not None
    assert "Engineering" in list(fig.data[0].labels)


def test_donut_chart_marketing_dataset():
    df_mkt = pd.DataFrame({
        "Channel": ["Google Ads", "Meta Ads", "LinkedIn", "TikTok", "Affiliates"],
        "Spend": [50000, 42000, 25000, 18000, 8000]
    })
    fig = ChartEngine.create_dimension_donut_chart(df_mkt, "Channel", "Spend", top_n=3)
    assert fig is not None
    assert len(fig.data[0].labels) == 4  # Top 3 + Other


def test_donut_chart_duplicate_column_names():
    df = pd.DataFrame([[ "A", 100, 200 ]], columns=["Cat", "Val", "Val"])
    fig = ChartEngine.create_dimension_donut_chart(df, "Cat", "Val")
    assert fig is not None


def test_donut_chart_backward_compatible_aliases():
    df = pd.DataFrame({
        "Category": ["Alpha", "Beta"],
        "Revenue": [100, 200]
    })
    f1 = ChartEngine.create_dimension_donut_chart(df, "Category", "Revenue")
    f2 = ChartEngine.create_composition_donut_chart(df, "Category", "Revenue")
    f3 = ChartEngine.create_category_donut_chart(df, "Category", "Revenue")
    f4 = ChartEngine.create_donut_chart(df, "Category", "Revenue")
    f5 = ChartEngine.dimension_donut_chart(df, "Category", "Revenue")
    f6 = ChartEngine.create_pie_chart(df, "Category", "Revenue")
    f7 = comp_create_donut(df, "Category", "Revenue")

    for f in [f1, f2, f3, f4, f5, f6, f7]:
        assert f is not None
        assert isinstance(f, go.Figure)
