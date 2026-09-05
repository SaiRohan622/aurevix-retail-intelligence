"""
AUREVIX — Next-Generation AI Business Analyst & Deterministic Natural Language Analytical Query Engine
Interprets questions, performs safe verified DataFrame computations, computes evidence-based explanations,
recommends Plotly visualizations, and supports conversational workspace follow-ups across any business domain.
"""
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.kpi_explainer import KPIExplainer


class AskYourDataEngine:
    """Interprets business questions, executes exact analytical operations, and generates rich visual takeaways."""

    @classmethod
    def answer_question(
        cls,
        *args,
        conversation_context: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        # Handle flexible argument passing (df, query, schema, metrics) or (query, df, schema, metrics)
        df = None
        query = ""
        schema_meta = {}
        metrics = {}

        if "df" in kwargs:
            df = kwargs["df"]
        if "query" in kwargs:
            query = kwargs["query"]
        if "schema_meta" in kwargs:
            schema_meta = kwargs["schema_meta"]
        if "metrics" in kwargs:
            metrics = kwargs["metrics"]

        # Parse positional args if present
        pos_args = list(args)
        for a in pos_args:
            if isinstance(a, pd.DataFrame) and df is None:
                df = a
            elif isinstance(a, str) and not query:
                query = a
            elif isinstance(a, dict):
                if not schema_meta:
                    schema_meta = a
                elif not metrics:
                    metrics = a

        from dashboard.analytics.security_utils import validate_nlp_query
        is_safe, blocked_msg = validate_nlp_query(query)
        if not is_safe:
            return {
                "answer": blocked_msg,
                "figure": None,
                "table": None,
                "follow_ups": ["What is total revenue?", "Show monthly trend", "What are my top categories?"]
            }

        if df is None or df.empty:
            return {
                "answer": "No active dataset loaded to analyze. Please upload a dataset or activate the workspace.",
                "figure": None,
                "table": None,
                "follow_ups": []
            }

        q_lower = query.lower().strip()
        roles = schema_meta.get("roles", {})
        num_cols = schema_meta.get("numeric_columns", [])
        curr_cols = schema_meta.get("currency_columns", [])
        cat_cols = schema_meta.get("categorical_columns", [])
        date_cols = schema_meta.get("date_columns", [])
        domain = schema_meta.get("domain", "Enterprise Operations / General Tabular")

        rev_col = metrics.get("primary_metric_col") or (curr_cols[0] if curr_cols else (num_cols[0] if num_cols else None))
        cat_col = metrics.get("category_col") or (cat_cols[0] if cat_cols else None)
        date_col = metrics.get("date_col") or (date_cols[0] if date_cols else None)
        cust_col = metrics.get("customer_col")
        reg_col = metrics.get("region_col") or ((schema_meta.get("geographic_columns") or [None])[0])
        tot_rev = metrics.get("total_revenue", 0.0)

        # 1. Why did sales fall / Why did metric change?
        if any(w in q_lower for w in ["why", "driver", "cause", "explain"]):
            if rev_col and rev_col in df.columns:
                why_res = KPIExplainer.explain_why_variance(df, rev_col, date_col, cat_col, reg_col)
                if why_res.get("available"):
                    driver_lines = "\n".join([f"• **{d['driver']}**: {d['impact']}" for d in why_res["drivers"]])
                    return {
                        "answer": f"### Analytical Driver Decomposition for `{rev_col}`\n\n{driver_lines}",
                        "figure": ChartEngine.create_dimension_bar_chart(df, cat_col, rev_col, top_n=6) if cat_col and cat_col in df.columns else None,
                        "table": None,
                        "follow_ups": ["Show regional breakdown", "Find unusual transactions", "What are the biggest risks?"]
                    }

        # 2. Find unusual transactions / Anomalies
        if any(w in q_lower for w in ["anomaly", "anomalies", "unusual", "outlier", "outliers", "spike", "drop", "weird", "irregular"]):
            anomalies = AnomalyEngine.detect_anomalies(df, schema_meta, metrics)
            if anomalies:
                lines = "\n".join([f"• **{a['title']}** ({a.get('severity', 'MED')}): {a['description']}" for a in anomalies[:4]])
                return {
                    "answer": f"### Detected Anomalies & Outliers\n\n{lines}",
                    "figure": ChartEngine.create_time_series_chart(df, date_col, rev_col) if date_col and rev_col and date_col in df.columns and rev_col in df.columns else None,
                    "table": pd.DataFrame(anomalies)[["type", "title", "metric", "severity"]].head(5),
                    "follow_ups": ["Why did sales fall?", "Show my top categories", "What are the strongest growth opportunities?"]
                }
            else:
                return {
                    "answer": "No severe statistical anomalies or extreme spikes were detected across the current dataset parameters.",
                    "figure": None,
                    "table": None,
                    "follow_ups": ["Show monthly sales trend", "What are my total metrics?"]
                }

        # 3. What should management know / Executive Summary
        if any(w in q_lower for w in ["management", "executive", "summary", "overview", "briefing"]):
            growth = metrics.get("growth_pct")
            growth_str = f" (**{'+' if growth >= 0 else ''}{growth:.1f}%** period trajectory)" if growth is not None else ""
            prefix = "$" if curr_cols else ""
            summary = (
                f"### Executive Management Briefing ({domain})\n\n"
                f"• **Aggregate Performance**: Total `{rev_col}` of **{prefix}{tot_rev:,.2f}** recorded across **{len(df):,} records**{growth_str}.\n"
                f"• **Segment Dominance**: Primary segment `{metrics.get('top_category_name', 'N/A')}` contributed **{prefix}{metrics.get('top_category_val', 0.0):,.2f}**.\n"
                f"• **Average Record / Order Value**: Standing at **{prefix}{metrics.get('average_transaction_value', 0.0):,.2f}**.\n"
                f"• **Active Scope**: Operating across **{metrics.get('unique_categories', 1)} segments** and **{metrics.get('unique_regions', 1)} geographic territories**."
            )
            return {
                "answer": summary,
                "figure": ChartEngine.create_dimension_bar_chart(df, cat_col, rev_col, top_n=5) if cat_col and cat_col in df.columns and rev_col in df.columns else None,
                "table": None,
                "follow_ups": ["What are the strongest growth opportunities?", "What region should I focus on?", "Show my top categories"]
            }

        # 4. Growth opportunities / Recommendations
        if any(w in q_lower for w in ["opportunity", "opportunities", "growth", "recommend", "focus", "strategy"]):
            rec_lines = []
            prefix = "$" if curr_cols else ""
            if cat_col and rev_col and cat_col in df.columns and rev_col in df.columns:
                grp = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
                if len(grp) >= 2:
                    top_name = grp.index[0]
                    rec_lines.append(f"• **Double-down on `{top_name}`**: Captures **{prefix}{grp.iloc[0]:,.2f}** ({grp.iloc[0]/grp.sum()*100:.1f}% share).")
                if len(grp) >= 3:
                    rising_name = grp.index[1]
                    rec_lines.append(f"• **Expand secondary pillar `{rising_name}`**: Accelerating this segment reduces reliance on the single leader.")
            if reg_col and rev_col and reg_col in df.columns and rev_col in df.columns:
                r_grp = df.groupby(reg_col)[rev_col].sum().sort_values(ascending=False)
                if len(r_grp) >= 2:
                    rec_lines.append(f"• **Scale regional operations in `{r_grp.index[0]}`**: Leading territory generating **{prefix}{r_grp.iloc[0]:,.2f}**.")

            return {
                "answer": f"### Growth Opportunities & Strategic Recommendations\n\n" + "\n".join(rec_lines),
                "figure": ChartEngine.create_dimension_donut_chart(df, cat_col, rev_col) if cat_col and cat_col in df.columns and rev_col in df.columns else None,
                "table": None,
                "follow_ups": ["What should management know?", "Which category is performing best?"]
            }

        # 5. Highest revenue / Top category / Best segment / Department / Salary
        if any(w in q_lower for w in ["category", "segment", "department", "highest revenue", "top category", "best category", "highest profit", "top department", "most sales", "best performing", "performing best", "highest salary"]):
            if cat_col and rev_col and cat_col in df.columns and rev_col in df.columns:
                grp = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
                top_name = grp.index[0]
                top_val = grp.iloc[0]
                pct = (top_val / grp.sum()) * 100.0 if grp.sum() > 0 else 0.0
                fig = ChartEngine.create_dimension_bar_chart(df, cat_col, rev_col, top_n=8)
                prefix = "$" if (curr_cols or "salary" in rev_col.lower() or "price" in rev_col.lower()) else ""
                return {
                    "answer": f"The leading segment in `{cat_col}` is **{top_name}** generating **{prefix}{top_val:,.2f}** (**{pct:.1f}%** of total `{rev_col}` across all {len(grp)} segments).",
                    "figure": fig,
                    "table": grp.reset_index().head(5),
                    "follow_ups": ["Why is it first?", "What region should I focus on?", "Show monthly trend"]
                }
            elif cat_col and cat_col in df.columns:
                counts = df[cat_col].value_counts()
                top_name = counts.index[0]
                top_val = counts.iloc[0]
                return {
                    "answer": f"The most frequent segment in `{cat_col}` is **{top_name}** with **{top_val:,} occurrences** ({top_val/len(df)*100:.1f}% of records).",
                    "figure": ChartEngine.create_dimension_bar_chart(df, cat_col, None, top_n=8),
                    "table": counts.reset_index().head(5),
                    "follow_ups": ["What are total records?", "What should management know?"]
                }

        # 6. Average salary / Average revenue / Mean value
        if any(w in q_lower for w in ["average salary", "avg salary", "average revenue", "average spend", "average transaction", "mean value", "avg", "average"]):
            if rev_col and rev_col in df.columns:
                avg_val = float(df[rev_col].mean())
                prefix = "$" if (curr_cols or "salary" in rev_col.lower() or "price" in rev_col.lower()) else ""
                return {
                    "answer": f"The average `{rev_col}` across the active dataset is **{prefix}{avg_val:,.2f}** (Median: **{prefix}{float(df[rev_col].median()):,.2f}**, Range: {prefix}{float(df[rev_col].min()):,.2f} – {prefix}{float(df[rev_col].max()):,.2f}).",
                    "figure": None,
                    "table": None,
                    "follow_ups": ["Which category is performing best?", "Show monthly trend"]
                }
            else:
                return {
                    "answer": "I can't answer this from the available columns. This query requires a numeric measure column, but none was detected in the active dataset.",
                    "figure": None,
                    "table": None,
                    "follow_ups": []
                }

        # 7. Time series trend / monthly / timeline (must precede single-word metric match)
        if any(w in q_lower for w in ["monthly", "trend", "sales over time", "timeline", "revenue trend", "daily", "by month", "by date", "time series", "over time"]):
            if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
                fig = ChartEngine.create_time_series_chart(df, date_col, rev_col, granularity="Monthly")
                return {
                    "answer": f"Time-series progression for **{rev_col}** across `{date_col}`.",
                    "figure": fig,
                    "table": None,
                    "follow_ups": ["Why did metric change?", "What are the biggest anomalies?"]
                }
            else:
                return {
                    "answer": "I can't answer this from the available columns. This time-series analysis requires a recognizable datetime column and a numeric measure, but none was detected in the active dataset.",
                    "figure": None,
                    "table": None,
                    "follow_ups": ["What columns exist?", "What should management know?"]
                }

        # 8. Total Sales / Revenue / Salary / Spend / Overall metric
        if any(w in q_lower for w in ["total sales", "total revenue", "total salary", "total payroll", "total spend", "total amount", "overall sales", "how much revenue", "how much sales", "sales", "revenue", "payroll", "spend"]):
            if rev_col and rev_col in df.columns:
                prefix = "$" if (curr_cols or "salary" in rev_col.lower() or "price" in rev_col.lower() or "spend" in rev_col.lower()) else ""
                return {
                    "answer": f"Total **{rev_col.replace('_', ' ').title()}** across the active dataset is **{prefix}{tot_rev:,.2f}** across **{len(df):,} records** (Average: **{prefix}{metrics.get('average_transaction_value', 0.0):,.2f}** per record).",
                    "figure": ChartEngine.create_time_series_chart(df, date_col, rev_col) if date_col and date_col in df.columns else None,
                    "table": None,
                    "follow_ups": ["Which category is performing best?", "Show monthly trend", "Show top entities"]
                }
            else:
                return {
                    "answer": f"The active dataset contains **{len(df):,} total records** across **{len(df.columns)} columns**.",
                    "figure": None,
                    "table": df.head(5),
                    "follow_ups": ["What columns exist?", "Which category has the most records?"]
                }
            if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
                fig = ChartEngine.create_time_series_chart(df, date_col, rev_col, granularity="Monthly")
                return {
                    "answer": f"Time-series progression for **{rev_col}** across `{date_col}`.",
                    "figure": fig,
                    "table": None,
                    "follow_ups": ["Why did metric change?", "What are the biggest anomalies?"]
                }
            else:
                return {
                    "answer": "I can't answer this from the available columns. This time-series analysis requires a recognizable datetime column and a numeric measure, but none was detected in the active dataset.",
                    "figure": None,
                    "table": None,
                    "follow_ups": ["What columns exist?", "What should management know?"]
                }

        # 9. Regional / Geographic performance
        if any(w in q_lower for w in ["region", "state", "city", "location", "territory", "country", "best region", "top region"]):
            if reg_col and rev_col and reg_col in df.columns and rev_col in df.columns:
                grp = df.groupby(reg_col)[rev_col].sum().sort_values(ascending=False)
                fig = ChartEngine.create_dimension_bar_chart(df, reg_col, rev_col, top_n=10)
                prefix = "$" if curr_cols else ""
                return {
                    "answer": f"The top territory is **{grp.index[0]}** generating **{prefix}{grp.iloc[0]:,.2f}** ({grp.iloc[0]/grp.sum()*100:.1f}% share of `{rev_col}`).",
                    "figure": fig,
                    "table": grp.reset_index().head(8),
                    "follow_ups": ["Which category is performing best?", "Show monthly trend"]
                }
            elif reg_col and reg_col in df.columns:
                counts = df[reg_col].value_counts()
                return {
                    "answer": f"The top geographic territory in `{reg_col}` is **{counts.index[0]}** with **{counts.iloc[0]:,} records**.",
                    "figure": ChartEngine.create_dimension_bar_chart(df, reg_col, None, top_n=10),
                    "table": counts.reset_index().head(8),
                    "follow_ups": ["What are total records?"]
                }
            else:
                return {
                    "answer": "I can't answer this from the available columns. No geographic or territory dimension was detected in this dataset.",
                    "figure": None,
                    "table": None,
                    "follow_ups": ["Which category is performing best?", "What should management know?"]
                }

        # 10. Default fallback
        prefix = "$" if curr_cols else ""
        return {
            "answer": f"Active dataset ({domain}) has **{len(df):,} total records** with aggregate **{prefix}{tot_rev:,.2f}** in `{rev_col}`.",
            "figure": None,
            "table": df.head(5),
            "follow_ups": ["What are my total metrics?", "Which category is performing best?", "What should management know?"]
        }


AskYourDataEngine.ask_question = AskYourDataEngine.answer_question
