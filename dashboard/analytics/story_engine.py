"""
AUREVIX — Autonomous Data Story & Business Narrative Engine
Generates coherent, executive-ready narrative storylines adapting in real time to dataset slicers.
"""

from typing import Dict, Any, List
import pandas as pd


class DataStoryEngine:
    """Constructs structured business narratives from active analytical results."""

    @classmethod
    def generate_story(cls, res: Dict[str, Any], df: pd.DataFrame, active_filters: Dict[str, Any]) -> List[Dict[str, str]]:
        story_chapters = []
        if df.empty:
            return story_chapters

        kpis = res.get("kpis", {})
        schema = res.get("schema", {})
        prof = res.get("profile", {})
        domain = schema.get("domain", "Enterprise")

        m_col = kpis.get("primary_metric_col", "Metric")
        tot_val = kpis.get("total_revenue", 0.0)
        growth = kpis.get("growth_pct")

        filter_desc = ""
        if active_filters:
            parts = [f"{k} = {v}" for k, v in active_filters.items() if v]
            if parts:
                filter_desc = f" (Filtered to: {', '.join(parts)})"

        # 1. Macro Chapter: Performance
        growth_str = f" reflecting a period growth rate of <b>{'+' if growth >= 0 else ''}{growth:.1f}%</b>" if growth is not None else ""
        story_chapters.append({
            "title": "1. Overall Performance Trajectory",
            "narrative": f"The active {domain} dataset recorded aggregate <b>${tot_val:,.2f}</b> in `{m_col}` across {len(df):,} analyzed records{filter_desc}{growth_str}.",
            "takeaway": f"Average ticket density stands at ${kpis.get('average_transaction_value', 0.0):,.2f} per transaction.",
            "icon": "📈"
        })

        # 2. Segment Contribution Chapter
        top_cat = kpis.get("top_category_name")
        top_cat_val = kpis.get("top_category_val", 0.0)
        if top_cat and tot_val > 0:
            share = (top_cat_val / tot_val) * 100.0
            story_chapters.append({
                "title": "2. Primary Growth Driver & Concentration",
                "narrative": f"The leading segment <b>{top_cat}</b> generated <b>${top_cat_val:,.2f}</b>, capturing <b>{share:.1f}%</b> of total monetary volume across all categories.",
                "takeaway": "Concentration is strong; maintaining supply SLA for this key driver is essential.",
                "icon": "🏆"
            })

        # 3. Regional / Territory Chapter
        top_reg = kpis.get("top_region_name")
        top_reg_val = kpis.get("top_region_val", 0.0)
        if top_reg and tot_val > 0:
            reg_share = (top_reg_val / tot_val) * 100.0
            story_chapters.append({
                "title": "3. Geographic Distribution",
                "narrative": f"Territory <b>{top_reg}</b> represents the dominant operational hub, contributing <b>${top_reg_val:,.2f}</b> ({reg_share:.1f}% of geographic volume).",
                "takeaway": "Expansion into secondary hubs can unlock incremental scale.",
                "icon": "🗺️"
            })

        # 4. Data Quality & Risk Chapter
        q_score = prof.get("quality_score", 100.0)
        missing_cnt = prof.get("missing_cells", 0)
        anomalies = res.get("anomalies", [])
        anom_text = f"Detected {len(anomalies)} statistical trend anomalies." if anomalies else "Zero statistical anomalies observed."
        story_chapters.append({
            "title": "4. Quality Assurance & Risk Evaluation",
            "narrative": f"Data Quality scored at <b>{q_score:.1f}%</b> with {missing_cnt:,} null values across {prof.get('col_count', 0)} fields. {anom_text}",
            "takeaway": "Analytics operate with high statistical integrity.",
            "icon": "🛡️"
        })

        # 5. Strategic Recommendations
        story_chapters.append({
            "title": "5. Strategic Recommendations",
            "narrative": f"Focus resources on high-converting segment `{top_cat or 'core'}` while monitoring territory distribution and outlier transactions.",
            "takeaway": "Execute proactive rebalancing to maximize net contribution.",
            "icon": "💡"
        })

        return story_chapters
