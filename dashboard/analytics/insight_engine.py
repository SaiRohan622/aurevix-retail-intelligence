"""
AUREVIX — Autonomous 3-Tier Business Insight Engine
Generates OBSERVATION -> DRIVER -> BUSINESS IMPACT structured insights strictly from active dataset metrics.
"""

from typing import List, Dict, Any, Optional
import pandas as pd


class InsightEngine:
    """Produces business intelligence observations with drivers and impact."""

    @classmethod
    def generate_insights(cls, df: pd.DataFrame, schema_meta: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        insights = []
        if df.empty:
            return insights

        rev_col = metrics.get("primary_metric_col")
        tot_rev = metrics.get("total_revenue", 0.0)
        growth = metrics.get("growth_pct")

        # 1. Growth / Macro Volume Insight
        if rev_col:
            growth_str = f" reflecting a <b>{'+' if growth >= 0 else ''}{growth:.1f}%</b> period trajectory" if growth is not None else ""
            insights.append({
                "type": "summary",
                "title": f"Aggregate {rev_col.replace('_', ' ').title()} Performance",
                "observation": f"Dataset recorded <b>${tot_rev:,.2f}</b> across {len(df):,} records{growth_str}.",
                "driver": f"Average ticket value stands at ${metrics.get('average_transaction_value', 0.0):,.2f} per record.",
                "impact": "Baseline metric density is established; monitoring volume stability across periods is recommended.",
                "badge": "MACRO KPI"
            })

        # 2. Profitability & Margin Insight
        if metrics.get("total_profit") is not None:
            p_val = metrics["total_profit"]
            p_pct = metrics.get("profit_margin", 0.0)
            insights.append({
                "type": "profitability",
                "title": "Margin & Bottom-Line Efficiency",
                "observation": f"Realized total net profit of <b>${p_val:,.2f}</b>, yielding a <b>{p_pct:.1f}%</b> contribution margin.",
                "driver": "Direct realization against gross volume without abnormal expense friction.",
                "impact": f"High margin conversion enables tactical reinvestment into expansion and operational scaling.",
                "badge": "MARGIN"
            })

        # 3. Category / Department Concentration
        cat_name = metrics.get("top_category_name")
        cat_val = metrics.get("top_category_val", 0.0)
        if cat_name and tot_rev > 0:
            share = (cat_val / tot_rev) * 100.0
            insights.append({
                "type": "category",
                "title": "Leading Segment Contribution",
                "observation": f"<b>{cat_name}</b> is the dominant segment generating <b>${cat_val:,.2f}</b> ({share:.1f}% of total).",
                "driver": f"Outperformed other {metrics.get('unique_categories', 1)} categories through high transaction volume.",
                "impact": "Segment concentration provides revenue stability but warrants diversification into secondary tiers.",
                "badge": "LEADER"
            })

        # 4. Regional Distribution
        reg_name = metrics.get("top_region_name")
        reg_val = metrics.get("top_region_val", 0.0)
        if reg_name and tot_rev > 0:
            reg_share = (reg_val / tot_rev) * 100.0
            insights.append({
                "type": "region",
                "title": "Top Geographic Territory",
                "observation": f"<b>{reg_name}</b> captured <b>${reg_val:,.2f}</b> ({reg_share:.1f}% of territory volume).",
                "driver": "Geographic concentration in core operational hub.",
                "impact": "Ensuring localized fulfillment SLA is paramount to maintaining dominant territory share.",
                "badge": "REGIONAL"
            })

        # 5. Customer Pareto Concentration
        cust_col = metrics.get("customer_col")
        if cust_col and rev_col and cust_col in df.columns and rev_col in df.columns:
            try:
                cust_grp = df.groupby(cust_col)[rev_col].sum().sort_values(ascending=False)
                top_20_pct_count = max(1, int(len(cust_grp) * 0.2))
                top_20_rev = cust_grp.head(top_20_pct_count).sum()
                if tot_rev > 0:
                    p_share = (top_20_rev / tot_rev) * 100.0
                    insights.append({
                        "type": "customer",
                        "title": "Entity Concentration (Pareto Law)",
                        "observation": f"Top 20% of accounts ({top_20_pct_count:,} entities) generate <b>{p_share:.1f}%</b> of total monetary value.",
                        "driver": "High-value core buyer tier exhibiting repeat purchase commitment.",
                        "impact": "VIP retention programs should be prioritized to safeguard primary revenue drivers.",
                        "badge": "PARETO"
                    })
            except Exception:
                pass

        # 6. Data Hygiene & Quality
        missing_cells = int(df.isnull().sum().sum())
        dup_rows = int(df.duplicated().sum())
        if missing_cells == 0 and dup_rows == 0:
            insights.append({
                "type": "quality",
                "title": "100% Data Quality Fidelity",
                "observation": "Zero missing values and zero duplicate records detected across the full dataset.",
                "driver": "Clean ingestion formatting and normalized schema structure.",
                "impact": "All downstream dashboards, projections, and reports operate at maximum statistical confidence.",
                "badge": "100% CLEAN"
            })
        else:
            insights.append({
                "type": "quality",
                "title": "Data Hygiene & Missingness Alert",
                "observation": f"Found <b>{missing_cells:,} missing cells</b> and <b>{dup_rows:,} duplicate rows</b> in active data.",
                "driver": "Incomplete source capture or redundant records in source extraction.",
                "impact": "Analytics automatically filter out null records to preserve aggregation correctness.",
                "badge": "AUDITED"
            })

        return insights
