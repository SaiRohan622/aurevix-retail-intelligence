"""
AUREVIX — Automated Analyst Recommendations & "Top Findings" Engine
Produces domain-specific analytical next-steps and autonomous highlights ("What should I look at?").
"""

from typing import Dict, Any, List
import pandas as pd


class RecommendationEngine:
    """Generates domain-aware suggestions and top findings for analysts."""

    @classmethod
    def get_top_findings(cls, res: Dict[str, Any], df: pd.DataFrame) -> List[Dict[str, str]]:
        findings = []
        if df.empty:
            return findings

        kpis = res.get("kpis", {})
        schema = res.get("schema", {})
        prof = res.get("profile", {})
        anomalies = res.get("anomalies", [])

        # Finding 1: Volume
        rev_col = kpis.get("primary_metric_col", "Volume")
        tot_rev = kpis.get("total_revenue", 0.0)
        growth = kpis.get("growth_pct")
        findings.append({
            "badge": "PERFORMANCE",
            "title": f"Aggregate {rev_col} Volume",
            "description": f"Generated ${tot_rev:,.2f} across {len(df):,} records" + (f" with a <b>{'+' if growth >= 0 else ''}{growth:.1f}%</b> period growth trajectory." if growth is not None else ".")
        })

        # Finding 2: Concentration
        top_cat = kpis.get("top_category_name")
        top_cat_val = kpis.get("top_category_val", 0.0)
        if top_cat and tot_rev > 0:
            share = (top_cat_val / tot_rev) * 100.0
            findings.append({
                "badge": "LEADER",
                "title": f"Dominant Segment: {top_cat}",
                "description": f"Accounts for <b>{share:.1f}%</b> (${top_cat_val:,.2f}) of total recorded volume."
            })

        # Finding 3: Anomalies
        if anomalies:
            top_an = anomalies[0]
            findings.append({
                "badge": "ANOMALY",
                "title": f"Detected Spike: {top_an.get('title', 'Anomaly')}",
                "description": top_an.get("description", "Statistical outlier observed.")
            })

        # Finding 4: Data Quality
        q_score = prof.get("quality_score", 100.0)
        findings.append({
            "badge": "DATA QUALITY",
            "title": f"Platform DQ Rating: {q_score:.1f}%",
            "description": f"Audited {prof.get('missing_cells', 0):,} missing cells and {prof.get('duplicate_rows', 0):,} duplicates."
        })

        return findings

    @classmethod
    def get_analyst_recommendations(cls, domain: str, schema: Dict[str, Any]) -> List[str]:
        d_lower = domain.lower()
        if "hr" in d_lower or "workforce" in d_lower:
            return [
                "📊 Analyze compensation distribution across departments",
                "🔍 Compare salary medians by location and job role",
                "📈 Track hiring velocity and tenure over joining dates",
                "⚠️ Inspect compensation outliers (>3.0× IQR) for equity audits",
                "📄 Export Executive Workforce Demographic Summary"
            ]
        elif "marketing" in d_lower:
            return [
                "📊 Evaluate Cost-per-Click (CPC) and conversion rates by channel",
                "🎯 Compare campaign ROI (Spend vs Conversions)",
                "📈 Analyze monthly spend trajectory against conversion spikes",
                "⚠️ Identify low-converting campaigns with abnormal ad spend",
                "📄 Generate Campaign Performance Executive Report"
            ]
        elif "retail" in d_lower or "commerce" in d_lower:
            return [
                "📊 Perform Pareto analysis (Top 20% products generating 80% revenue)",
                "🚚 Review freight and logistics cost ratios across states",
                "📈 Forecast next-quarter gross revenue using time-series trend",
                "⚠️ Investigate unusual high-volume transaction spikes",
                "📄 Export Monthly Commercial Performance Report"
            ]
        else:
            return [
                "📊 Analyze primary metric distribution across detected categories",
                "🔍 Drill into leading dimensions to inspect sub-item contributions",
                "📈 Track time-series progression over available date fields",
                "🛡️ Inspect missing-value density in Data Quality Center",
                "📄 Download Executive Business Intelligence Summary"
            ]
