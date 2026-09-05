"""
AUREVIX — Page 10: Universal Business Data Analytics Workspace & Next-Generation BI Center
True lazy-loading architecture with central analysis cache, dynamic schema intelligence,
multi-dimensional drill-down, AI Analyst assistant, target forecasting, and audit trail governance.
"""
import io
import sys
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

t_shell_start = time.perf_counter()

from src.common.logger import get_logger
from dashboard.components.sidebar import render_sidebar
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.comparison_engine import ComparisonEngine
from dashboard.analytics.target_engine import TargetEngine
from dashboard.analytics.forecast_engine import ForecastEngine
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.drilldown_engine import DrillDownEngine
from dashboard.analytics.kpi_explainer import KPIExplainer
from dashboard.analytics.chart_engine import ChartEngine
from dashboard.analytics.audit_trail import AuditTrail
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.components.filter_bar import render_global_filter_bar

logger = get_logger("aurevix.data_workspace")

st.set_page_config(
    page_title="Universal Business Analytics — AUREVIX",
    page_icon="📂",
    layout="wide"
)

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

AnalyticsManager.initialize()
render_sidebar()


def get_active_workspace_df() -> pd.DataFrame:
    """Single authoritative source of truth for active DataFrame."""
    return AnalyticsManager.get_active_df()


def has_active_dataset() -> bool:
    """Returns True iff a valid user-uploaded dataset is active in session state."""
    return AnalyticsManager.has_active_dataset()


def render_no_data_state(message: str = "No dataset loaded."):
    st.markdown(
        f"""
        <div style="padding:40px;text-align:center;background:rgba(15,23,42,0.5);
                    border:1px dashed #334155;border-radius:12px;margin:20px 0;">
            <div style="font-size:2.5rem;margin-bottom:12px;">📂</div>
            <div style="font-size:1.1rem;font-weight:700;color:#f8fafc;margin-bottom:8px;">{message}</div>
            <div style="color:#64748b;font-size:0.85rem;">
                Upload a CSV, Excel, Parquet, or JSON dataset to activate Next-Gen Business Intelligence.<br>
                The Olist demo dataset is available only via the explicit demo button below.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================================
# SECTION RENDER FUNCTIONS (TRUE LAZY LOADING)
# =====================================================================

def render_ingest_quality_center(active_df, res, schema, prof, kpis, user_active):
    """Section 1: Ingest, Schema Intelligence & 4-Pillar Quality Center with Explanations & Drilldown"""
    if user_active and not active_df.empty:
        ws_state = AnalyticsManager.get_workspace_state()
        orig_df = AnalyticsManager.get_original_raw_df()
        init_prof = st.session_state.get("workspace", {}).get("initial_profile") or prof
        recipe = st.session_state.get("workspace", {}).get("cleaning_recipe") or []

        init_q = float(init_prof.get("quality_score", prof.get("quality_score", 100.0)))
        curr_q = float(prof.get("quality_score", 100.0))
        delta_q = curr_q - init_q

        init_rows = len(orig_df) if isinstance(orig_df, pd.DataFrame) and not orig_df.empty else len(active_df)
        curr_rows = len(active_df)
        rows_removed = max(0, init_rows - curr_rows)

        issues = prof.get("issues_summary", {})
        init_issues = init_prof.get("issues_summary", {}).get("total_issues", issues.get("total_issues", 0))
        curr_issues = issues.get("total_issues", 0)

        q_rating = prof.get("rating", "GOOD")
        q_color = prof.get("rating_color", "#10b981")
        domain = schema.get("domain", "Enterprise Analytics")
        domain_conf = schema.get("domain_confidence", 85)
        sample_badge = f"<span style='color:#f59e0b; font-size:0.75rem; margin-left:8px;'>[Sampled {prof.get('sample_size', 0):,} rows]</span>" if prof.get("is_sampled") else ""

        state_label = f"Cleaned (v{ws_state.get('dataset_version', 1)})" if recipe else "Initial Upload (Pristine)"
        render_html(
            f"""
            <div style="background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(30,41,59,0.9));
                        border: 1px solid {q_color}40; border-radius: 12px; padding: 24px; margin-bottom: 20px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 0.8rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em;">
                            Data Quality Center &amp; Schema Intelligence
                        </div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #f8fafc; margin-top: 4px;">
                            {curr_q:.1f}% <span style="font-size: 1.1rem; padding: 4px 12px; border-radius: 9999px;
                                                       background: {q_color}25; color: {q_color}; border: 1px solid {q_color};">
                                {q_rating}
                            </span>
                            {sample_badge}
                        </div>
                        <div style="color: #64748b; font-size: 0.85rem; margin-top: 6px;">
                            Dataset: <b style="color: #cbd5e1;">{res.get('dataset_name','')}</b> &nbsp;|&nbsp;
                            Detected Domain: <b style="color: #38bdf8;">{domain}</b> ({domain_conf}% Confidence) &nbsp;|&nbsp;
                            State: <b style="color: #10b981;">{state_label}</b>
                        </div>
                    </div>
                    <div style="display: flex; gap: 16px; text-align: center; flex-wrap: wrap;">
                        <div style="background: rgba(15,23,42,0.6); padding: 10px 16px; border-radius: 8px; border: 1px solid #334155;">
                            <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">{curr_rows:,}</div>
                            <div style="font-size: 0.72rem; color: #94a3b8;">Working Rows</div>
                        </div>
                        <div style="background: rgba(15,23,42,0.6); padding: 10px 16px; border-radius: 8px; border: 1px solid #334155;">
                            <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">{len(active_df.columns):,}</div>
                            <div style="font-size: 0.72rem; color: #94a3b8;">Columns Classified</div>
                        </div>
                        <div style="background: rgba(15,23,42,0.6); padding: 10px 16px; border-radius: 8px; border: 1px solid #334155;">
                            <div style="font-size: 1.2rem; font-weight: 700; color: {'#ef4444' if curr_issues > 0 else '#10b981'};">
                                {curr_issues:,}
                            </div>
                            <div style="font-size: 0.72rem; color: #94a3b8;">Remaining Issues</div>
                        </div>
                    </div>
                </div>
            </div>
            """
        )

        # -------------------------------------------------------------
        # 2. BEFORE -> AFTER DATA QUALITY COMPARISON
        # -------------------------------------------------------------
        st.markdown("##### ⚖️ Initial vs Current Data Quality State")
        st_c1, st_c2, st_c3, st_c4, st_c5 = st.columns(5)
        st_c1.metric(
            "Initial Quality",
            f"{init_q:.1f}%",
            help="Quality score on pristine uploaded dataset"
        )
        st_c2.metric(
            "Current Quality",
            f"{curr_q:.1f}%",
            delta=f"{delta_q:+.1f} pts" if len(recipe) > 0 else "0.0 pts (Pristine)",
            help="Quality score on current working dataset"
        )
        st_c3.metric(
            "Rows Retained",
            f"{curr_rows:,}",
            delta=f"-{rows_removed:,} removed" if rows_removed > 0 else "100% Retained",
            delta_color="off" if rows_removed == 0 else "normal",
            help="Working dataset row count"
        )
        st_c4.metric(
            "Remaining Issues",
            f"{curr_issues:,}",
            delta=f"{curr_issues - init_issues:+d}" if len(recipe) > 0 else f"{curr_issues:,} detected",
            delta_color="inverse" if len(recipe) > 0 else "off",
            help="Count of detected quality problems remaining"
        )
        st_c5.metric(
            "Cleaning Steps",
            f"{len(recipe)}",
            help="Total non-destructive cleaning transformations applied"
        )

        if len(recipe) > 0:
            with st.expander("📊 Detailed Before → After Quality Metrics Breakdown", expanded=True):
                init_nulls = int(init_prof.get("missing_cells", 0))
                curr_nulls = int(prof.get("missing_cells", 0))
                init_dups = int(init_prof.get("duplicate_rows", 0))
                curr_dups = int(prof.get("duplicate_rows", 0))
                init_inv = int(init_prof.get("issues_summary", {}).get("invalid_dates", 0))
                curr_inv = int(issues.get("invalid_dates", 0))
                init_out = int(init_prof.get("issues_summary", {}).get("outliers_count", 0))
                curr_out = int(issues.get("outliers_count", 0))

                comp_data = [
                    {"Metric": "Overall Quality Score", "Initial State (Before)": f"{init_q:.1f}%", "Current Working (After)": f"{curr_q:.1f}%", "Change / Delta": f"{delta_q:+.1f} pts", "Status": "✅ Improved" if delta_q > 0 else "⏸️ Unchanged"},
                    {"Metric": "Missing Value Cells", "Initial State (Before)": f"{init_nulls:,}", "Current Working (After)": f"{curr_nulls:,}", "Change / Delta": f"{curr_nulls - init_nulls:+d}", "Status": "✅ Resolved" if curr_nulls < init_nulls else ("⚠️ Remaining" if curr_nulls > 0 else "✅ None")},
                    {"Metric": "Duplicate Records", "Initial State (Before)": f"{init_dups:,}", "Current Working (After)": f"{curr_dups:,}", "Change / Delta": f"{curr_dups - init_dups:+d}", "Status": "✅ Removed" if curr_dups < init_dups else ("⚠️ Remaining" if curr_dups > 0 else "✅ None")},
                    {"Metric": "Invalid Date Formats", "Initial State (Before)": f"{init_inv:,}", "Current Working (After)": f"{curr_inv:,}", "Change / Delta": f"{curr_inv - init_inv:+d}", "Status": "✅ Fixed" if curr_inv < init_inv else ("⚠️ Remaining" if curr_inv > 0 else "✅ None")},
                    {"Metric": "Statistical IQR Outliers", "Initial State (Before)": f"{init_out:,}", "Current Working (After)": f"{curr_out:,}", "Change / Delta": f"{curr_out - init_out:+d}", "Status": "✅ Treated" if curr_out < init_out else ("ℹ️ Present" if curr_out > 0 else "✅ None")},
                    {"Metric": "Dataset Total Rows", "Initial State (Before)": f"{init_rows:,}", "Current Working (After)": f"{curr_rows:,}", "Change / Delta": f"{curr_rows - init_rows:+d}", "Status": "ℹ️ Filtered" if rows_removed > 0 else "✅ Intact"}
                ]
                st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # 3. 4 PILLARS OF DATA QUALITY
        # -------------------------------------------------------------
        st.markdown("##### 🛡️ 4 Pillars of Data Quality")
        p_c1, p_c2, p_c3, p_c4 = st.columns(4)
        with p_c1:
            comp_val = float(prof.get("completeness_score", 100.0))
            comp_icon = "✅" if comp_val >= 95 else ("⚠️" if comp_val >= 80 else "❌")
            p_c1.metric(f"{comp_icon} Completeness", f"{comp_val:.1f}%",
                        delta=f"-{prof.get('missing_cells', 0):,} null cells" if prof.get('missing_cells', 0) > 0 else "100% complete")
            st.progress(comp_val / 100.0)
        with p_c2:
            val_val = float(prof.get("validity_score", 100.0))
            val_icon = "✅" if val_val >= 95 else ("⚠️" if val_val >= 80 else "❌")
            p_c2.metric(f"{val_icon} Validity", f"{val_val:.1f}%",
                        delta=f"{issues.get('invalid_dates', 0)} invalid dates" if issues.get('invalid_dates', 0) > 0 else "Valid formats")
            st.progress(val_val / 100.0)
        with p_c3:
            cons_val = float(prof.get("consistency_score", 100.0))
            cons_icon = "✅" if cons_val >= 95 else ("⚠️" if cons_val >= 80 else "❌")
            p_c3.metric(f"{cons_icon} Consistency", f"{cons_val:.1f}%",
                        delta=f"{issues.get('outliers_count', 0)} outliers" if issues.get('outliers_count', 0) > 0 else "Consistent")
            st.progress(cons_val / 100.0)
        with p_c4:
            uniq_val = float(prof.get("uniqueness_score", 100.0))
            uniq_icon = "✅" if uniq_val >= 95 else ("⚠️" if uniq_val >= 80 else "❌")
            p_c4.metric(f"{uniq_icon} Uniqueness", f"{uniq_val:.1f}%",
                        delta=f"-{prof.get('duplicate_rows', 0):,} duplicates" if prof.get('duplicate_rows', 0) > 0 else "Zero duplicates")
            st.progress(uniq_val / 100.0)

        # -------------------------------------------------------------
        # 4. EXPLAIN EVERY DATA QUALITY ISSUE & DRILLDOWN
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("##### 🔬 Data Quality Diagnostics & Issue Explanations")
        st.caption("Comprehensive analysis of all detected data anomalies, why they matter, and recommended remediation:")

        col_profs = prof.get("column_profiles", {})
        outliers_dict = prof.get("outliers", {})
        invalid_dates_dict = prof.get("invalid_dates", {})
        constant_cols = prof.get("constant_columns", [])
        missing_cells_cnt = prof.get("missing_cells", 0)
        dup_rows_cnt = prof.get("duplicate_rows", 0)

        # Group identified issues
        issue_items = []
        if missing_cells_cnt > 0:
            null_cols = [c for c, p in col_profs.items() if p.get("null_count", 0) > 0]
            issue_items.append({
                "type": "Missing Values",
                "icon": "💧",
                "count": missing_cells_cnt,
                "location": f"{len(null_cols)} column(s): {', '.join(null_cols[:4])}{'...' if len(null_cols) > 4 else ''}",
                "explanation": "Null or unpopulated cells exist in the dataset. Missing data reduces statistical power, skews mean formulations, and causes unexpected errors in predictive models.",
                "action": "Apply Median/Mean (numeric) or Mode/Constant (categorical) imputation in Clean & Transform.",
                "filter_key": "missing"
            })

        if dup_rows_cnt > 0:
            issue_items.append({
                "type": "Duplicate Records",
                "icon": "🔁",
                "count": dup_rows_cnt,
                "location": "Full-row matching records",
                "explanation": "Exact identical rows detected. Duplicates artificially inflate revenue figures, distort order counts, and introduce bias into cohort analysis.",
                "action": "Use Deduplication in Clean & Transform to retain the first occurrence and remove redundant copies.",
                "filter_key": "duplicate"
            })

        if outliers_dict:
            out_cols = list(outliers_dict.keys())
            total_out = sum(info.get("count", 0) for info in outliers_dict.values())
            issue_items.append({
                "type": "Statistical IQR Outliers",
                "icon": "📈",
                "count": total_out,
                "location": f"Numeric columns: {', '.join(out_cols[:4])}",
                "explanation": "Values lie outside the 1.5x Interquartile Range [Q1 - 1.5*IQR, Q3 + 1.5*IQR]. Extreme values heavily pull mean metrics and distort trend regressions.",
                "action": "Clip/Winsorize extreme outliers or filter unrepresentative anomalies in Clean & Transform.",
                "filter_key": "outliers"
            })

        if invalid_dates_dict:
            inv_cols = list(invalid_dates_dict.keys())
            total_inv = sum(info.get("count", 0) for info in invalid_dates_dict.values())
            issue_items.append({
                "type": "Invalid Date Formats",
                "icon": "📅",
                "count": total_inv,
                "location": f"Date columns: {', '.join(inv_cols)}",
                "explanation": "Date strings could not be parsed into valid timestamps. Unparseable dates break time-series aggregation, monthly trends, and period comparisons.",
                "action": "Coerce date formats to ISO-8601 or standard datetime in Clean & Transform.",
                "filter_key": "invalid_dates"
            })

        if constant_cols:
            issue_items.append({
                "type": "Constant / Zero-Variance Columns",
                "icon": "⏹️",
                "count": len(constant_cols),
                "location": f"Columns: {', '.join(constant_cols)}",
                "explanation": "Columns contain only 1 unique value across all records. Zero-variance features carry no predictive or analytical utility and consume memory.",
                "action": "Drop redundant constant columns in Clean & Transform to simplify dataset schema.",
                "filter_key": "constant"
            })

        if issue_items:
            for item in issue_items:
                render_html(f"""
                <div style="background: rgba(15,23,42,0.7); border: 1px solid #334155; border-left: 4px solid #f59e0b;
                            border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div style="font-weight: 700; color: #f8fafc; font-size: 1rem;">
                            {item['icon']} {item['type']} — <span style="color: #f59e0b;">{item['count']:,} affected</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8;">
                            <b>Location:</b> <code style="color: #38bdf8;">{item['location']}</code>
                        </div>
                    </div>
                    <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 8px;">
                        <b>Why It Matters:</b> {item['explanation']}
                    </div>
                    <div style="color: #10b981; font-size: 0.83rem; margin-top: 6px;">
                        <b>💡 Recommended Action:</b> {item['action']}
                    </div>
                </div>
                """)

            # ---------------------------------------------------------
            # 5. PROBLEMATIC RECORD DRILLDOWN STUDIO
            # ---------------------------------------------------------
            with st.expander("🔍 Problematic Record Drilldown Studio (View Affected Rows)", expanded=False):
                st.markdown("###### Inspect Specific Problematic Records Before Cleaning")
                drill_mode = st.selectbox(
                    "Select Issue to Inspect:",
                    ["All Problematic Records (Nulls & Duplicates)"] + [f"{item['icon']} {item['type']}" for item in issue_items],
                    key="dq_drill_selector"
                )

                filtered_drill_df = pd.DataFrame()
                if "Missing Values" in drill_mode:
                    filtered_drill_df = active_df[active_df.isnull().any(axis=1)]
                elif "Duplicate" in drill_mode:
                    filtered_drill_df = active_df[active_df.duplicated(keep=False)]
                elif "Outliers" in drill_mode:
                    if outliers_dict:
                        target_out_col = st.selectbox("Select Numeric Column to Inspect Outliers:", list(outliers_dict.keys()), key="out_drill_col")
                        s_num = pd.to_numeric(active_df[target_out_col], errors="coerce")
                        bounds = outliers_dict.get(target_out_col, {})
                        low = bounds.get("lower_bound", -np.inf)
                        high = bounds.get("upper_bound", np.inf)
                        filtered_drill_df = active_df[(s_num < low) | (s_num > high)]
                elif "Invalid Date" in drill_mode:
                    if invalid_dates_dict:
                        target_date_col = list(invalid_dates_dict.keys())[0]
                        s_dt = pd.to_datetime(active_df[target_date_col], errors="coerce")
                        filtered_drill_df = active_df[active_df[target_date_col].notnull() & s_dt.isnull()]
                elif "Constant" in drill_mode:
                    if constant_cols:
                        filtered_drill_df = active_df[constant_cols]
                else:
                    null_mask = active_df.isnull().any(axis=1)
                    dup_mask = active_df.duplicated(keep=False)
                    filtered_drill_df = active_df[null_mask | dup_mask]

                if not filtered_drill_df.empty:
                    st.info(f"Showing **{len(filtered_drill_df):,} affected records** out of {len(active_df):,} total rows:")
                    st.dataframe(filtered_drill_df.head(200), use_container_width=True)
                else:
                    st.success("✅ No records found matching the selected issue criteria.")
        else:
            st.success("🎉 Perfect Data Quality! Zero missing values, zero duplicates, and zero formatting anomalies detected.")

        # -------------------------------------------------------------
        # 6. FINAL "DATASET READY FOR ANALYSIS" OR "NEEDS ATTENTION" STATE
        # -------------------------------------------------------------
        st.markdown("---")
        if curr_issues == 0 or curr_q >= 95.0:
            render_html(f"""
            <div style="background: linear-gradient(135deg, rgba(6,78,59,0.5), rgba(15,23,42,0.9));
                        border: 1px solid #10b981; border-radius: 12px; padding: 22px; margin-bottom: 20px;
                        box-shadow: 0 4px 20px rgba(16,185,129,0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.4rem;">✅</span>
                            <span style="font-size: 1.25rem; font-weight: 800; color: #f8fafc; letter-spacing: 0.05em;">
                                DATASET READY FOR ANALYSIS
                            </span>
                        </div>
                        <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 6px;">
                            Quality Score: <b style="color: #10b981;">{curr_q:.1f}%</b> &nbsp;|&nbsp;
                            Records: <b style="color: #f8fafc;">{curr_rows:,}</b> &nbsp;|&nbsp;
                            Columns: <b style="color: #f8fafc;">{len(active_df.columns)}</b> &nbsp;|&nbsp;
                            Remaining Issues: <b style="color: #10b981;">{curr_issues}</b> &nbsp;|&nbsp;
                            Cleaning Steps: <b style="color: #38bdf8;">{len(recipe)}</b>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <span style="background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">✓ Validated</span>
                        <span style="background: rgba(56,189,248,0.2); color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">✓ Profiled</span>
                        <span style="background: rgba(168,85,247,0.2); color: #a855f7; border: 1px solid #a855f7; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">✓ Cleaned</span>
                        <span style="background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid #f59e0b; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">✓ Analytics Ready</span>
                    </div>
                </div>
            </div>
            """)
        else:
            render_html(f"""
            <div style="background: linear-gradient(135deg, rgba(120,53,15,0.4), rgba(15,23,42,0.9));
                        border: 1px solid #f59e0b; border-radius: 12px; padding: 22px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.4rem;">⚠️</span>
                            <span style="font-size: 1.25rem; font-weight: 800; color: #f8fafc; letter-spacing: 0.05em;">
                                DATASET NEEDS ATTENTION ({curr_issues:,} Issues Remaining)
                            </span>
                        </div>
                        <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 6px;">
                            Quality Score is currently <b>{curr_q:.1f}%</b>. We recommend resolving missing values and duplicates in the Clean & Transform Studio for optimal statistical fidelity.
                        </div>
                    </div>
                </div>
            </div>
            """)

        # Quick Navigation Action Buttons
        st.markdown("##### 🚀 Quick Workspace Navigation")
        nav_c1, nav_c2, nav_c3, nav_c4 = st.columns(4)
        with nav_c1:
            if st.button("🔎 Explore Data", use_container_width=True, key="quick_nav_explore"):
                AnalyticsManager.set_active_section("🔎 Data Explorer")
                st.session_state["active_workspace_section_radio"] = "🔎 Data Explorer"
                st.rerun()
        with nav_c2:
            if st.button("🧹 Clean & Transform", use_container_width=True, key="quick_nav_clean"):
                AnalyticsManager.set_active_section("🧹 Clean & Transform")
                st.session_state["active_workspace_section_radio"] = "🧹 Clean & Transform"
                st.rerun()
        with nav_c3:
            if st.button("🤖 Ask Your Data", use_container_width=True, key="quick_nav_ask"):
                AnalyticsManager.set_active_section("🤖 Ask Your Data")
                st.session_state["active_workspace_section_radio"] = "🤖 Ask Your Data"
                st.rerun()
        with nav_c4:
            if st.button("📄 Export Clean Dataset", use_container_width=True, key="quick_nav_export"):
                AnalyticsManager.set_active_section("📄 Export Center")
                st.session_state["active_workspace_section_radio"] = "📄 Export Center"
                st.rerun()

        # -------------------------------------------------------------
        # 7. DYNAMIC BUSINESS KPIS & CHARTS
        # -------------------------------------------------------------
        kpi_cards = kpis.get("kpi_cards", [])
        if kpi_cards:
            st.markdown("---")
            st.markdown("##### 💼 Dynamic Business Key Performance Indicators")
            k_cols = st.columns(min(4, len(kpi_cards)))
            for idx, card in enumerate(kpi_cards[:4]):
                with k_cols[idx]:
                    st.metric(
                        label=f"{card.get('icon', '📊')} {card['label']}",
                        value=card["value"],
                        delta=card.get("delta"),
                        help=card.get("explanation")
                    )

        # Recommended Visualizations Section
        st.markdown("---")
        st.markdown("##### 📈 Recommended Visualizations")
        recs = ChartEngine.recommend_visualizations(active_df, schema, kpis)
        if recs:
            r_c1, r_c2 = st.columns(2)
            for idx, r in enumerate(recs[:4]):
                target_col = r_c1 if idx % 2 == 0 else r_c2
                with target_col:
                    st.markdown(f"###### {r['title']}")
                    st.caption(r['reason'])
                    st.plotly_chart(r['figure'], use_container_width=True)

        # Autonomous Business Insights
        insights = res.get("insights", [])
        if insights:
            st.markdown("---")
            st.markdown("##### 💡 Autonomous Business Insights")
            for ins in insights:
                st.markdown(f"""
                <div style="background: rgba(15,23,42,0.6); border-left: 4px solid #38bdf8;
                            border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 0.95rem;">{ins.get('title')}</div>
                    <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 4px;">{ins.get('observation')}</div>
                    <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">
                        <b>Driver:</b> {ins.get('driver')} &nbsp;|&nbsp; <b>Impact:</b> {ins.get('impact')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        render_no_data_state("Upload a dataset above to view the Data Quality Center & semantic profile.")


def render_clean_transform(active_df, res, schema, prof, recipe, init_prof, user_active):
    """Section 2: Interactive Data Cleaning Studio with Result Feedback & Non-Destructive Recipes"""
    if user_active and not active_df.empty:
        st.markdown("##### 🧹 Interactive Data Cleaning & Preparation Studio")
        st.caption("Perform user-controlled, non-destructive data cleaning with instant quality score feedback. Original uploaded data is always preserved.")

        init_q = float(init_prof.get("quality_score", prof.get("quality_score", 100.0)))
        curr_q = float(prof.get("quality_score", 100.0))
        delta_q = curr_q - init_q

        # Top Control & Metrics Banner
        q_banner_col1, q_banner_col2, q_banner_col3, q_banner_col4 = st.columns([1.5, 1.5, 1.5, 2.5])
        q_banner_col1.metric("Initial Quality Score", f"{init_q:.1f}%")
        q_banner_col2.metric("Current Quality Score", f"{curr_q:.1f}%",
                             delta=f"{'+' if delta_q >= 0 else ''}{delta_q:.1f} pts" if len(recipe) > 0 else None)
        q_banner_col3.metric("Applied Steps", f"{len(recipe)}")

        with q_banner_col4:
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("↩️ Undo Last Step", disabled=(len(recipe) == 0), use_container_width=True):
                    undone = AnalyticsManager.undo_last_cleaning_step()
                    if undone:
                        st.success(f"Undid step: {undone.get('title', 'Operation')}")
                    st.rerun()
            with btn_c2:
                if st.button("🔄 Reset All", disabled=(len(recipe) == 0), use_container_width=True):
                    AnalyticsManager.reset_cleaning()
                    st.info("Reset dataset to original uploaded data.")
                    st.rerun()

        # Compact Cleaning Result Feedback Banner (if a step was recently applied)
        if recipe:
            latest_step = recipe[-1]
            render_html(f"""
            <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
                        border-radius: 8px; padding: 12px 16px; margin: 12px 0 16px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div style="color: #10b981; font-weight: 700; font-size: 0.9rem;">
                        ✓ Latest Cleaning Applied: {latest_step.get('title', 'Cleaning Step')}
                    </div>
                    <div style="color: #94a3b8; font-size: 0.8rem;">
                        Applied at: {latest_step.get('timestamp', 'Recently')}
                    </div>
                </div>
                <div style="color: #cbd5e1; font-size: 0.83rem; margin-top: 4px;">
                    Current Quality: <b style="color: #10b981;">{curr_q:.1f}%</b> ({delta_q:+.1f} pts from initial {init_q:.1f}%) &nbsp;|&nbsp;
                    Working Rows: <b>{len(active_df):,}</b>
                </div>
            </div>
            """)

        st.markdown("---")

        # Smart Auto-Clean Recommendations
        smart_recs = DataCleaningEngine.generate_smart_cleaning_recommendations(active_df, prof, schema)
        if smart_recs:
            st.markdown("##### ⚡ Smart Auto-Clean Recommendations")
            st.caption("One-click high-impact fixes identified by the AUREVIX profiling engine:")
            for rec in smart_recs:
                r_col1, r_col2 = st.columns([4, 1])
                with r_col1:
                    st.markdown(f"**{rec['title']}** — <span style='color: #94a3b8; font-size: 0.85rem;'>{rec['description']} ({rec['impact']} Impact)</span>", unsafe_allow_html=True)
                with r_col2:
                    if st.button(f"⚡ Apply##{rec['id']}", key=f"btn_{rec['id']}", use_container_width=True):
                        step_dict = {
                            "action": rec["action"],
                            "params": rec["params"],
                            "title": rec["title"]
                        }
                        AnalyticsManager.apply_cleaning_step(step_dict)
                        st.success(f"Applied: {rec['title']}")
                        st.rerun()
            st.markdown("---")

        clean_tab_miss, clean_tab_dup, clean_tab_out, clean_tab_text, clean_tab_type, clean_tab_cols = st.tabs([
            "💧 Missing Values",
            "🔁 Deduplication",
            "📈 Outlier Handling",
            "✂️ Text & Whitespace",
            "🔢 Types & Sentinels",
            "🗑️ Drop Columns"
        ])

        with clean_tab_miss:
            st.markdown("###### 💧 Missing Value Treatment")
            m_cols_with_null = [c for c in active_df.columns if active_df[c].isnull().any()]
            if m_cols_with_null:
                mc1, mc2, mc3 = st.columns([1.5, 1.5, 1.0])
                with mc1:
                    sel_null_col = st.selectbox("Select Column with Missing Values:", m_cols_with_null)
                    null_cnt = int(active_df[sel_null_col].isnull().sum())
                    st.caption(f"Found **{null_cnt:,} null values** in `{sel_null_col}` ({null_cnt/len(active_df)*100:.1f}%)")
                with mc2:
                    strat_options = ["Median (Numeric)", "Mean (Numeric)", "Mode (Most Frequent)", "Zero (0)", "Custom Constant", "Forward Fill", "Backward Fill", "Drop Missing Rows"]
                    sel_strat = st.selectbox("Imputation Strategy:", strat_options)
                    custom_const_val = None
                    if sel_strat == "Custom Constant":
                        custom_const_val = st.text_input("Enter Constant Value:", value="Unknown")
                with mc3:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("✅ Apply Imputation", use_container_width=True):
                        if sel_strat == "Drop Missing Rows":
                            step = {
                                "action": "drop_missing",
                                "params": {"columns": [sel_null_col]},
                                "title": f"Drop null rows in '{sel_null_col}'"
                            }
                        else:
                            strat_code_map = {
                                "Median (Numeric)": "median",
                                "Mean (Numeric)": "mean",
                                "Mode (Most Frequent)": "mode",
                                "Zero (0)": "zero",
                                "Custom Constant": "constant",
                                "Forward Fill": "ffill",
                                "Backward Fill": "bfill"
                            }
                            step = {
                                "action": "impute_missing",
                                "params": {
                                    "column": sel_null_col,
                                    "strategy": strat_code_map.get(sel_strat, "median"),
                                    "constant_value": custom_const_val
                                },
                                "title": f"Impute missing in '{sel_null_col}' via {sel_strat}"
                            }
                        AnalyticsManager.apply_cleaning_step(step)
                        st.success(f"Applied missing value fix to `{sel_null_col}`!")
                        st.rerun()
            else:
                st.info("✅ No missing values detected in the active dataset!")

        with clean_tab_dup:
            st.markdown("###### 🔁 Duplicate Row Removal")
            dup_cnt = int(active_df.duplicated().sum())
            st.write(f"Detected **{dup_cnt:,} exact duplicate rows** in dataset.")
            dc1, dc2, dc3 = st.columns([2, 1.5, 1.5])
            with dc1:
                dedup_cols = st.multiselect("Deduplicate on subset of columns (leave empty for all columns):", options=list(active_df.columns), default=[])
            with dc2:
                keep_strat = st.selectbox("Keep occurrence:", ["First (first)", "Last (last)"])
            with dc3:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("✅ Remove Duplicates", use_container_width=True):
                    keep_val = "first" if "first" in keep_strat.lower() else "last"
                    step = {
                        "action": "remove_duplicates",
                        "params": {"subset": dedup_cols if dedup_cols else None, "keep": keep_val},
                        "title": f"Remove duplicates (keep {keep_val})"
                    }
                    AnalyticsManager.apply_cleaning_step(step)
                    st.success("Duplicates removed successfully!")
                    st.rerun()

        with clean_tab_out:
            st.markdown("###### 📈 Statistical Outlier Treatment")
            num_cols = schema.get("numeric_columns", [])
            if num_cols:
                oc1, oc2, oc3, oc4 = st.columns(4)
                with oc1:
                    sel_num_col = st.selectbox("Numeric Column:", num_cols)
                with oc2:
                    out_method = st.selectbox("Detection Method:", ["IQR (1.5x IQR)", "IQR (3.0x Extreme)", "Z-Score (3.0 std)"])
                with oc3:
                    out_action = st.selectbox("Action:", ["Clip / Winsorize (Safe)", "Drop Outlier Rows"])
                with oc4:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("✅ Handle Outliers", use_container_width=True):
                        factor = 3.0 if "3.0" in out_method else 1.5
                        method_code = "zscore" if "z-score" in out_method.lower() else "iqr"
                        action_code = "drop" if "drop" in out_action.lower() else "clip"
                        step = {
                            "action": "handle_outliers",
                            "params": {
                                "column": sel_num_col,
                                "method": method_code,
                                "action": action_code,
                                "factor": factor
                            },
                            "title": f"{action_code.title()} outliers in '{sel_num_col}' ({method_code.upper()})"
                        }
                        AnalyticsManager.apply_cleaning_step(step)
                        st.success(f"Treated outliers in `{sel_num_col}`!")
                        st.rerun()
            else:
                st.info("No numeric columns available for outlier detection.")

        with clean_tab_text:
            st.markdown("###### ✂️ Text Trimming & Casing")
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                if st.button("✂️ Strip All Leading/Trailing Whitespace", use_container_width=True):
                    step = {
                        "action": "strip_whitespace",
                        "params": {},
                        "title": "Strip whitespace across all text columns"
                    }
                    AnalyticsManager.apply_cleaning_step(step)
                    st.success("Trimmed text columns!")
                    st.rerun()
            with tc2:
                text_cols = [c for c in active_df.columns if active_df[c].dtype == object or pd.api.types.is_string_dtype(active_df[c])]
                if text_cols:
                    case_col = st.selectbox("Select Text Column:", text_cols, key="case_col_sel")
                    case_type = st.selectbox("Target Case:", ["Title Case", "UPPERCASE", "lowercase", "Capitalize"])
                    if st.button("✅ Change Case", use_container_width=True):
                        case_map = {"Title Case": "title", "UPPERCASE": "upper", "lowercase": "lower", "Capitalize": "capitalize"}
                        step = {
                            "action": "change_case",
                            "params": {"column": case_col, "case_type": case_map.get(case_type, "title")},
                            "title": f"Convert '{case_col}' to {case_type}"
                        }
                        AnalyticsManager.apply_cleaning_step(step)
                        st.success(f"Converted `{case_col}` to {case_type}!")
                        st.rerun()

        with clean_tab_type:
            st.markdown("###### 🔢 Data Type Coercion & Sentinel Value Replacement")
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("**Replace Sentinel Placeholders** (e.g. `'N/A'`, `'null'`, `'-'`, `'?'`)")
                if st.button("✅ Convert Sentinels to NaNs", use_container_width=True):
                    step = {
                        "action": "replace_sentinels",
                        "params": {},
                        "title": "Replace placeholder sentinels with NaN"
                    }
                    AnalyticsManager.apply_cleaning_step(step)
                    st.success("Replaced sentinel placeholders!")
                    st.rerun()
            with sc2:
                st.markdown("**Coerce Column Type**")
                coerce_col = st.selectbox("Target Column:", list(active_df.columns), key="coerce_col_sel")
                target_dtype = st.selectbox("Target Data Type:", ["numeric (Float)", "integer (Nullable Int)", "datetime (Date/Time)", "string (Text)", "boolean (True/False)"])
                if st.button("✅ Coerce Data Type", use_container_width=True):
                    type_key_map = {
                        "numeric (Float)": "numeric",
                        "integer (Nullable Int)": "integer",
                        "datetime (Date/Time)": "datetime",
                        "string (Text)": "string",
                        "boolean (True/False)": "boolean"
                    }
                    step = {
                        "action": "coerce_data_type",
                        "params": {"column": coerce_col, "target_type": type_key_map.get(target_dtype, "numeric")},
                        "title": f"Coerce '{coerce_col}' to {target_dtype}"
                    }
                    AnalyticsManager.apply_cleaning_step(step)
                    st.success(f"Coerced `{coerce_col}` to {target_dtype}!")
                    st.rerun()

        with clean_tab_cols:
            st.markdown("###### 🗑️ Drop Unwanted or Redundant Columns")
            cols_to_drop = st.multiselect("Select columns to remove from dataset:", options=list(active_df.columns))
            if cols_to_drop and st.button("🗑️ Drop Selected Columns", use_container_width=True):
                step = {
                    "action": "drop_columns",
                    "params": {"columns": cols_to_drop},
                    "title": f"Drop {len(cols_to_drop)} column(s): {', '.join(cols_to_drop)}"
                }
                AnalyticsManager.apply_cleaning_step(step)
                st.success(f"Dropped columns: {', '.join(cols_to_drop)}")
                st.rerun()

        if recipe:
            st.markdown("---")
            st.markdown("##### 📜 Cleaning Recipe Audit Trail")
            st.caption("Reproducible step history applied to the working dataset:")
            recipe_rows = []
            for s in recipe:
                recipe_rows.append({
                    "Step": f"#{s.get('step_num', 1)}",
                    "Operation": s.get("title", s.get("action")),
                    "Action Type": s.get("action"),
                    "Applied At": s.get("timestamp"),
                    "Details": str(s.get("stats", {}))
                })
            st.dataframe(pd.DataFrame(recipe_rows), use_container_width=True, hide_index=True)
    else:
        render_no_data_state("Upload a dataset above to enable the interactive cleaning studio.")


def render_data_explorer(active_df, res, schema, user_active):
    """Section 3: Fast Interactive Record Explorer & Multi-Level Drill-Down"""
    if user_active and not active_df.empty:
        render_global_filter_bar()
        st.markdown("##### 🔍 Interactive Record Explorer & Multi-Level Drill-Down")
        
        # Supported Hierarchies for Drill-Down
        hierarchies = DrillDownEngine.get_supported_hierarchies(active_df, schema)
        if hierarchies:
            with st.expander("🔬 Interactive Dimensional Drill-Down Studio", expanded=False):
                h_names = list(hierarchies.keys())
                sel_h = st.selectbox("Select Hierarchy Path:", h_names)
                levels = hierarchies[sel_h]
                st.caption(f"Supported Hierarchy Levels: **{' → '.join(levels)}**")

                if sel_h == "Time Hierarchy":
                    d_col = schema.get("roles", {}).get("date")
                    m_col = res.get("kpis", {}).get("primary_metric_col") or schema.get("numeric_columns", [None])[0]
                    sel_level = st.selectbox("Drill Level:", ["Year", "Quarter", "Month", "Day"], index=2)
                    drill_res = DrillDownEngine.drill_into_time(active_df, d_col, m_col, level=sel_level)
                    st.dataframe(drill_res["data"], use_container_width=True, hide_index=True)
                else:
                    if len(levels) >= 2:
                        p_col = levels[0]
                        c_col = levels[1]
                        m_col = res.get("kpis", {}).get("primary_metric_col") or schema.get("numeric_columns", [None])[0]
                        p_vals = sorted(list(active_df[p_col].dropna().unique().astype(str)))
                        sel_p_val = st.selectbox(f"Select Parent Value ({p_col}):", p_vals[:30])
                        drill_res = DrillDownEngine.drill_into_dimension(active_df, p_col, c_col, sel_p_val, m_col)
                        st.dataframe(drill_res["data"], use_container_width=True, hide_index=True)

        st.markdown("---")

        # Interactive Table Filtering & Column Selection
        c_search, c_rows, c_sort = st.columns([2, 1, 1])
        with c_search:
            search_query = st.text_input("🔎 Search dataset across all string columns:", placeholder="Type to filter rows...")
        with c_rows:
            preview_limit = st.selectbox("Display Limit:", [50, 100, 250, 500, 1000], index=1)
        with c_sort:
            sort_col = st.selectbox("Sort by Column:", ["None"] + list(active_df.columns))

        display_df = active_df.copy()
        if search_query:
            str_cols = display_df.select_dtypes(include=["object", "string"]).columns
            if len(str_cols) > 0:
                mask = pd.Series(False, index=display_df.index)
                for sc in str_cols:
                    mask = mask | display_df[sc].astype(str).str.contains(search_query, case=False, na=False)
                display_df = display_df[mask]

        if sort_col != "None":
            sort_order = st.radio("Order:", ["Ascending", "Descending"], horizontal=True)
            display_df = display_df.sort_values(sort_col, ascending=(sort_order == "Ascending"))

        st.caption(f"Displaying **{min(len(display_df), preview_limit):,}** of **{len(display_df):,}** matching rows ({len(active_df):,} total working dataset rows):")
        st.dataframe(display_df.head(preview_limit), use_container_width=True)
    else:
        render_no_data_state("Upload a dataset above to explore raw and filtered records.")


def render_compare(active_df, kpis, user_active):
    """Section 4: Enterprise Dual-Dataset & Multi-Dimensional Comparison Workspace"""
    st.markdown("##### ⚖️ Enterprise Comparison Workspace")
    st.caption("Perform cross-dataset comparative intelligence across schemas, metrics, trends, record-level changes, and data quality.")

    comp_main_tab1, comp_main_tab2 = st.tabs([
        "📑 Dual-Dataset Head-to-Head Comparison",
        "🏷️ In-Dataset Dimensional & Period Comparison"
    ])

    with comp_main_tab1:
        comp_state = AnalyticsManager.get_comparison_state()
        df_a = comp_state.get("dataset_a")
        df_b = comp_state.get("dataset_b")
        name_a = comp_state.get("dataset_a_name") or "Dataset A"
        name_b = comp_state.get("dataset_b_name") or "Dataset B"
        fhash_a = comp_state.get("dataset_a_fingerprint")
        fhash_b = comp_state.get("dataset_b_fingerprint")

        # -------------------------------------------------------------
        # Dual-Dataset Ingestion & Management
        # -------------------------------------------------------------
        c_up1, c_up2 = st.columns(2)
        with c_up1:
            st.markdown(f"###### 📁 Dataset A (Baseline): <b style='color:#38bdf8;'>{name_a}</b>", unsafe_allow_html=True)
            if user_active and not active_df.empty:
                if st.button("📥 Use Current Active Dataset as Dataset A", use_container_width=True, key="use_active_as_a"):
                    active_name = AnalyticsManager.get_workspace_state().get("dataset_name") or "Active_Working_Dataset"
                    active_id = AnalyticsManager.get_workspace_state().get("dataset_id") or "active_hash"
                    AnalyticsManager.set_comparison_dataset_a(active_df, active_name, active_id)
                    st.success(f"Set Dataset A to '{active_name}' ({len(active_df):,} rows)")
                    st.rerun()

            uploaded_a = st.file_uploader(
                "Or Upload Dataset A (CSV, XLSX, Parquet, JSON):",
                type=["csv", "xlsx", "xls", "json", "parquet"],
                key="comp_file_uploader_a"
            )
            if uploaded_a is not None:
                try:
                    df_loaded_a, hash_a = UniversalDataLoader.load_file(uploaded_a)
                    if fhash_a != hash_a:
                        AnalyticsManager.set_comparison_dataset_a(df_loaded_a, uploaded_a.name, hash_a)
                        st.success(f"Loaded Dataset A: '{uploaded_a.name}' ({len(df_loaded_a):,} rows)")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Error loading Dataset A: {str(exc)}")

            if df_a is not None and not df_a.empty:
                prof_a = DataProfiler.profile(df_a)
                q_score_a = float(prof_a.get("quality_score", 100.0)) if isinstance(prof_a, dict) and prof_a.get("quality_score") is not None else 100.0
                st.caption(f"✓ **{name_a}** | `{len(df_a):,} rows` | `{len(df_a.columns)} cols` | Quality: **{q_score_a:.1f}%**")
                with st.expander(f"👁️ Preview {name_a} (Top 5 rows)", expanded=False):
                    st.dataframe(df_a.head(5), use_container_width=True)

        with c_up2:
            st.markdown(f"###### 📁 Dataset B (Target / Comparison): <b style='color:#10b981;'>{name_b}</b>", unsafe_allow_html=True)
            uploaded_b = st.file_uploader(
                "Upload Dataset B (CSV, XLSX, Parquet, JSON):",
                type=["csv", "xlsx", "xls", "json", "parquet"],
                key="comp_file_uploader_b"
            )
            if uploaded_b is not None:
                try:
                    df_loaded_b, hash_b = UniversalDataLoader.load_file(uploaded_b)
                    if fhash_b != hash_b:
                        AnalyticsManager.set_comparison_dataset_b(df_loaded_b, uploaded_b.name, hash_b)
                        st.success(f"Loaded Dataset B: '{uploaded_b.name}' ({len(df_loaded_b):,} rows)")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Error loading Dataset B: {str(exc)}")

            if df_b is not None and not df_b.empty:
                prof_b = DataProfiler.profile(df_b)
                q_score_b = float(prof_b.get("quality_score", 100.0)) if isinstance(prof_b, dict) and prof_b.get("quality_score") is not None else 100.0
                st.caption(f"✓ **{name_b}** | `{len(df_b):,} rows` | `{len(df_b.columns)} cols` | Quality: **{q_score_b:.1f}%**")
                with st.expander(f"👁️ Preview {name_b} (Top 5 rows)", expanded=False):
                    st.dataframe(df_b.head(5), use_container_width=True)

        # Quick Actions & Sample Pair Loaders
        s_btn_c1, s_btn_c2, s_btn_c3 = st.columns(3)
        with s_btn_c1:
            if st.button("🛒 Load Retail Comparison Sample Pair", use_container_width=True):
                p_a = PROJECT_ROOT / "data" / "samples" / "retail_sales.csv"
                df_sa, ha = UniversalDataLoader.load_file(p_a, "retail_sales_2025.csv")
                df_sb = df_sa.sample(frac=0.85, random_state=42).copy()
                if "sales" in df_sb.columns:
                    df_sb["sales"] = df_sb["sales"] * 1.15
                AnalyticsManager.set_comparison_dataset_a(df_sa, "Retail_Sales_2025.csv", ha)
                AnalyticsManager.set_comparison_dataset_b(df_sb, "Retail_Sales_2026.csv", "sample_hash_b")
                st.rerun()
        with s_btn_c2:
            if st.button("💼 Load Workforce Comparison Sample Pair", use_container_width=True):
                p_a = PROJECT_ROOT / "data" / "samples" / "employee_data.xlsx"
                df_ea, ha = UniversalDataLoader.load_file(p_a, "employee_data_2024.xlsx")
                df_eb = df_ea.sample(frac=0.9, random_state=24).copy()
                if "salary" in df_eb.columns:
                    df_eb["salary"] = df_eb["salary"] * 1.08
                AnalyticsManager.set_comparison_dataset_a(df_ea, "Workforce_2024.xlsx", ha)
                AnalyticsManager.set_comparison_dataset_b(df_eb, "Workforce_2025.xlsx", "sample_hash_eb")
                st.rerun()
        with s_btn_c3:
            if (df_a is not None or df_b is not None) and st.button("🗑️ Clear Comparison Workspace", use_container_width=True):
                AnalyticsManager.clear_comparison_state()
                st.rerun()

        st.markdown("---")

        # -------------------------------------------------------------
        # Comparison Workspace Processing
        # -------------------------------------------------------------
        if df_a is not None and not df_a.empty and df_b is not None and not df_b.empty:
            # 1. Automatic Schema Matching & Manual Override
            schema_match_res = ComparisonEngine.match_schemas(df_a, df_b)
            saved_mapping = comp_state.get("schema_mapping", {})
            effective_mapping = saved_mapping if saved_mapping else schema_match_res["matched"]

            with st.expander(f"🧩 Schema Matching Studio (Match Rate: {schema_match_res.get('match_rate_pct', 0.0):.1f}%)", expanded=False):
                st.caption("Automatically aligned columns based on exact names, normalized strings, semantic synonyms, and data types:")
                match_table = []
                for d in schema_match_res.get("match_details", []):
                    match_table.append({
                        "Dataset A Column": d["col_a"],
                        "Dataset B Column": d["col_b"],
                        "Method": d["method"],
                        "Confidence": f"{d['confidence']}%",
                        "Type A": d["type_a"],
                        "Type B": d["type_b"]
                    })
                if match_table:
                    st.dataframe(pd.DataFrame(match_table), use_container_width=True, hide_index=True)

                if schema_match_res.get("unmatched_a") or schema_match_res.get("unmatched_b"):
                    u_col1, u_col2 = st.columns(2)
                    with u_col1:
                        st.caption(f"Unmatched in A: `{', '.join(schema_match_res.get('unmatched_a', [])) or 'None'}`")
                    with u_col2:
                        st.caption(f"Unmatched in B: `{', '.join(schema_match_res.get('unmatched_b', [])) or 'None'}`")

            # 2. Compute Full Dataset Comparison
            comp_res = ComparisonEngine.compare_datasets(df_a, df_b, name_a, name_b, effective_mapping)
            AnalyticsManager.set_comparison_results(comp_res)

            # ---------------------------------------------------------
            # Comparison Sub-Tabs
            # ---------------------------------------------------------
            c_tab_kpi, c_tab_dq, c_tab_rec, c_tab_cat, c_tab_trend, c_tab_ins, c_tab_ask = st.tabs([
                "📊 Executive KPI Deltas",
                "🛡️ Quality Head-to-Head",
                "🔍 Record-Level Diff",
                "🏷️ Categorical Shifts",
                "📈 Trend Overlay",
                "💡 Comparison Insights",
                "🤖 Ask Your Data (Comparison)"
            ])

            with c_tab_kpi:
                st.markdown("###### 📊 Executive Volume & Measure Deltas")
                k1, k2, k3, k4 = st.columns(4)
                row_pct = comp_res.get("row_pct_change", 0.0)
                row_diff = comp_res.get("row_difference", 0)
                k1.metric(f"Rows ({name_a} → {name_b})", f"{len(df_b):,}", delta=f"{row_pct:+.1f}% ({row_diff:+d} rows)")
                k2.metric(f"Columns", f"{len(df_b.columns)}", delta=f"{comp_res.get('column_difference', 0):+d} cols")
                k3.metric("Matched Columns", f"{len(effective_mapping)}", help="Equivalent columns mapped between schemas")
                k4.metric("Memory Footprint", f"{comp_res['dataset_b']['memory_mb']:.2f} MB", delta=f"{comp_res['dataset_b']['memory_mb'] - comp_res['dataset_a']['memory_mb']:+.2f} MB")

                num_metrics = comp_res.get("numeric_metrics", {})
                if num_metrics:
                    st.markdown("###### 🔢 Numeric Measure Comparison Matrix")
                    num_table = []
                    for k, v in num_metrics.items():
                        num_table.append({
                            "Metric (A)": v["col_a"],
                            "Mapped To (B)": v["col_b"],
                            f"Sum ({name_a})": f"{v['sum_a']:,.2f}",
                            f"Sum ({name_b})": f"{v['sum_b']:,.2f}",
                            "Sum Delta ($)": f"{v['sum_diff']:+,.2f}",
                            "Sum Delta (%)": f"{v['sum_pct']:+.1f}%",
                            f"Mean ({name_a})": f"{v['mean_a']:,.2f}",
                            f"Mean ({name_b})": f"{v['mean_b']:,.2f}",
                            "Mean Delta (%)": f"{v['mean_pct']:+.1f}%"
                        })
                    st.dataframe(pd.DataFrame(num_table), use_container_width=True, hide_index=True)
                else:
                    st.info("No common numeric measures mapped between datasets.")

            with c_tab_dq:
                st.markdown("###### 🛡️ Data Quality & Hygiene Head-to-Head")
                qc = comp_res.get("quality_comparison", {})
                dq1, dq2, dq3, dq4 = st.columns(4)
                dq1.metric(
                    "Overall Quality Score",
                    f"{qc.get('score_b', 100.0):.1f}%",
                    delta=f"{qc.get('score_delta', 0.0):+.1f} pts ({name_a}: {qc.get('score_a', 100.0):.1f}%)"
                )
                dq2.metric(
                    "Completeness",
                    f"{qc.get('completeness_b', 100.0):.1f}%",
                    delta=f"{qc.get('completeness_delta', 0.0):+.1f} pts"
                )
                dq3.metric(
                    "Missing Cells",
                    f"{qc.get('missing_cells_b', 0):,}",
                    delta=f"{qc.get('missing_delta', 0):+d} cells",
                    delta_color="inverse"
                )
                dq4.metric(
                    "Duplicate Rows",
                    f"{qc.get('duplicate_rows_b', 0):,}",
                    delta=f"{qc.get('duplicate_delta', 0):+d} rows",
                    delta_color="inverse"
                )

                dq_comp_data = [
                    {"Metric": "Overall Quality Score", name_a: f"{qc.get('score_a', 100.0):.1f}%", name_b: f"{qc.get('score_b', 100.0):.1f}%", "Difference": f"{qc.get('score_delta', 0.0):+.1f} pts"},
                    {"Metric": "Completeness Pillar", name_a: f"{qc.get('completeness_a', 100.0):.1f}%", name_b: f"{qc.get('completeness_b', 100.0):.1f}%", "Difference": f"{qc.get('completeness_delta', 0.0):+.1f} pts"},
                    {"Metric": "Validity Pillar", name_a: f"{qc.get('validity_a', 100.0):.1f}%", name_b: f"{qc.get('validity_b', 100.0):.1f}%", "Difference": f"{qc.get('validity_delta', 0.0):+.1f} pts"},
                    {"Metric": "Consistency Pillar", name_a: f"{qc.get('consistency_a', 100.0):.1f}%", name_b: f"{qc.get('consistency_b', 100.0):.1f}%", "Difference": f"{qc.get('consistency_delta', 0.0):+.1f} pts"},
                    {"Metric": "Uniqueness Pillar", name_a: f"{qc.get('uniqueness_a', 100.0):.1f}%", name_b: f"{qc.get('uniqueness_b', 100.0):.1f}%", "Difference": f"{qc.get('uniqueness_delta', 0.0):+.1f} pts"},
                    {"Metric": "Total Missing Cells", name_a: f"{qc.get('missing_cells_a', 0):,}", name_b: f"{qc.get('missing_cells_b', 0):,}", "Difference": f"{qc.get('missing_delta', 0):+d}"},
                    {"Metric": "Total Duplicate Rows", name_a: f"{qc.get('duplicate_rows_a', 0):,}", name_b: f"{qc.get('duplicate_rows_b', 0):,}", "Difference": f"{qc.get('duplicate_delta', 0):+d}"},
                    {"Metric": "Statistical Outliers", name_a: f"{qc.get('outliers_a', 0):,}", name_b: f"{qc.get('outliers_b', 0):,}", "Difference": f"{qc.get('outliers_delta', 0):+d}"}
                ]
                st.dataframe(pd.DataFrame(dq_comp_data), use_container_width=True, hide_index=True)

            with c_tab_rec:
                st.markdown("###### 🔍 Record-Level Cohort Diffing (COMMON / NEW / REMOVED)")
                # Key candidates
                key_candidates_a = [c for c in df_a.columns if "id" in c.lower() or "code" in c.lower() or "key" in c.lower() or "name" in c.lower()] or list(df_a.columns)
                key_candidates_b = [c for c in df_b.columns if "id" in c.lower() or "code" in c.lower() or "key" in c.lower() or "name" in c.lower()] or list(df_b.columns)

                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    sel_key_a = st.selectbox("Select Key Column in Dataset A:", key_candidates_a, key="rec_key_a")
                with r_col2:
                    default_b_idx = key_candidates_b.index(effective_mapping.get(sel_key_a)) if effective_mapping.get(sel_key_a) in key_candidates_b else 0
                    sel_key_b = st.selectbox("Select Key Column in Dataset B:", key_candidates_b, index=default_b_idx, key="rec_key_b")

                rec_res = ComparisonEngine.compare_records(df_a, df_b, sel_key_a, sel_key_b)
                if rec_res.get("available"):
                    rc1, rc2, rc3 = st.columns(3)
                    rc1.metric("Common Records", f"{rec_res['common_count']:,}", delta=f"{rec_res['common_pct']:.1f}% cohort overlap")
                    rc2.metric("New Records (in B only)", f"{rec_res['new_count']:,}")
                    rc3.metric("Removed Records (in A only)", f"{rec_res['removed_count']:,}")

                    rec_sub_tab1, rec_sub_tab2, rec_sub_tab3 = st.tabs(["✨ New Records (in B)", "🗑️ Removed Records (in A)", "🤝 Common Records"])
                    with rec_sub_tab1:
                        st.dataframe(rec_res["df_new"], use_container_width=True)
                    with rec_sub_tab2:
                        st.dataframe(rec_res["df_removed"], use_container_width=True)
                    with rec_sub_tab3:
                        st.dataframe(rec_res["df_common"], use_container_width=True)

            with c_tab_cat:
                st.markdown("###### 🏷️ Categorical Segment Growth & Distribution Shifts")
                cat_cols_a = [c for c in df_a.columns if df_a[c].dtype == object or pd.api.types.is_string_dtype(df_a[c])]
                cat_cols_b = [c for c in df_b.columns if df_b[c].dtype == object or pd.api.types.is_string_dtype(df_b[c])]
                num_cols_a = [c for c in df_a.columns if pd.api.types.is_numeric_dtype(df_a[c])]
                num_cols_b = [c for c in df_b.columns if pd.api.types.is_numeric_dtype(df_b[c])]

                if cat_cols_a and cat_cols_b:
                    cc1, cc2, cc3 = st.columns([1.5, 1.5, 1.0])
                    with cc1:
                        sel_cat_a = st.selectbox("Category Dimension (A):", cat_cols_a, key="comp_cat_a")
                    with cc2:
                        default_cat_b = effective_mapping.get(sel_cat_a) if effective_mapping.get(sel_cat_a) in cat_cols_b else cat_cols_b[0]
                        sel_cat_b = st.selectbox("Category Dimension (B):", cat_cols_b, index=cat_cols_b.index(default_cat_b), key="comp_cat_b")
                    with cc3:
                        sel_metric = st.selectbox("Aggregate By:", ["Record Count"] + num_cols_a, key="comp_cat_metric")

                    metric_a = sel_metric if sel_metric != "Record Count" else None
                    metric_b = effective_mapping.get(sel_metric) if metric_a and effective_mapping.get(sel_metric) in num_cols_b else metric_a

                    cat_comp_res = ComparisonEngine.compare_categories(df_a, df_b, sel_cat_a, sel_cat_b, metric_a, metric_b)
                    if cat_comp_res.get("available"):
                        st.plotly_chart(cat_comp_res["figure"], use_container_width=True)
                        st.dataframe(cat_comp_res["data"], use_container_width=True, hide_index=True)

            with c_tab_trend:
                st.markdown("###### 📈 Historical Temporal Trend Overlay")
                date_cols_a = [c for c in df_a.columns if "date" in c.lower() or "time" in c.lower() or pd.api.types.is_datetime64_any_dtype(df_a[c])]
                date_cols_b = [c for c in df_b.columns if "date" in c.lower() or "time" in c.lower() or pd.api.types.is_datetime64_any_dtype(df_b[c])]
                num_cols_a = [c for c in df_a.columns if pd.api.types.is_numeric_dtype(df_a[c])]
                num_cols_b = [c for c in df_b.columns if pd.api.types.is_numeric_dtype(df_b[c])]

                if date_cols_a and date_cols_b and num_cols_a and num_cols_b:
                    tc1, tc2, tc3, tc4 = st.columns(4)
                    with tc1:
                        sel_date_a = st.selectbox("Date Column (A):", date_cols_a, key="comp_date_a")
                    with tc2:
                        default_db = effective_mapping.get(sel_date_a) if effective_mapping.get(sel_date_a) in date_cols_b else date_cols_b[0]
                        sel_date_b = st.selectbox("Date Column (B):", date_cols_b, index=date_cols_b.index(default_db), key="comp_date_b")
                    with tc3:
                        sel_trend_m_a = st.selectbox("Measure (A):", num_cols_a, key="comp_trend_m_a")
                    with tc4:
                        sel_gran = st.selectbox("Granularity:", ["Month", "Quarter", "Week", "Day", "Year"], index=0, key="comp_gran")

                    trend_m_b = effective_mapping.get(sel_trend_m_a) if effective_mapping.get(sel_trend_m_a) in num_cols_b else num_cols_b[0]
                    trend_res = ComparisonEngine.compare_trends(df_a, df_b, sel_date_a, sel_date_b, sel_trend_m_a, trend_m_b, sel_gran)
                    if trend_res.get("available"):
                        st.plotly_chart(trend_res["figure"], use_container_width=True)
                else:
                    st.info("Time trend overlay requires valid date and numeric columns in both datasets.")

            with c_tab_ins:
                st.markdown("###### 💡 Autonomous Comparative Business Insights")
                for ins in comp_res.get("insights", []):
                    st.markdown(f"""
                    <div style="background: rgba(15,23,42,0.7); border-left: 4px solid #38bdf8;
                                border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                        <div style="font-weight: 700; color: #f8fafc; font-size: 1rem;">{ins.get('title')}</div>
                        <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 4px;">{ins.get('observation')}</div>
                        <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">
                            <b>Driver:</b> {ins.get('driver')} &nbsp;|&nbsp; <b>Impact:</b> {ins.get('impact')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with c_tab_ask:
                st.markdown("###### 🤖 Ask Your Data — Dual-Dataset Comparison Mode")
                st.caption("Ask natural-language questions comparing Dataset A and Dataset B:")
                q_comp_input = st.text_input(
                    "Enter comparison query:",
                    placeholder="e.g. 'Which dataset has higher revenue?', 'Which dataset has better data quality?', 'What changed between these datasets?'",
                    key="comp_ask_input"
                )

                q_preset1, q_preset2, q_preset3 = st.columns(3)
                with q_preset1:
                    if st.button("📊 Compare Metric Volumes", use_container_width=True):
                        q_comp_input = "Which dataset has higher revenue?"
                with q_preset2:
                    if st.button("🛡️ Compare Data Quality", use_container_width=True):
                        q_comp_input = "Which dataset has better data quality?"
                with q_preset3:
                    if st.button("🔍 Summarize Changes", use_container_width=True):
                        q_comp_input = "What changed between these datasets?"

                if q_comp_input:
                    ans = ComparisonEngine.answer_comparison_query(q_comp_input, df_a, df_b, name_a, name_b, comp_res)
                    st.markdown(f"""
                    <div style="background: rgba(15,23,42,0.8); border-left: 4px solid #10b981;
                                border-radius: 8px; padding: 16px 20px; margin: 16px 0;">
                        <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Comparative Answer</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: #f8fafc; margin-top: 6px;">{ans.get('answer')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if ans.get("data") is not None and isinstance(ans["data"], pd.DataFrame) and not ans["data"].empty:
                        st.dataframe(ans["data"], use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Upload or select both **Dataset A** and **Dataset B** above to activate dual-dataset comparative analytics.")

    # -----------------------------------------------------------------
    # Tab 2: Single Dataset Internal Comparison
    # -----------------------------------------------------------------
    with comp_main_tab2:
        if user_active and not active_df.empty:
            st.markdown("###### Compare Dimensional Entities or Time Windows in Active Dataset")
            single_comp_tab1, single_comp_tab2 = st.tabs(["🏷️ Dimension vs Dimension", "📅 Time Period vs Period"])

            with single_comp_tab1:
                cat_cols = [c for c in active_df.columns if active_df[c].dtype == object or pd.api.types.is_string_dtype(active_df[c])]
                num_cols = [c for c in active_df.columns if pd.api.types.is_numeric_dtype(active_df[c])]
                if cat_cols and num_cols:
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    with cc1:
                        dim_col = st.selectbox("Select Dimension:", cat_cols, key="comp_dim_col")
                        uniq_vals = sorted(list(active_df[dim_col].dropna().unique().astype(str)))
                    with cc2:
                        item_a = st.selectbox("Entity A:", uniq_vals, index=0, key="comp_item_a")
                    with cc3:
                        item_b = st.selectbox("Entity B:", uniq_vals, index=min(1, len(uniq_vals)-1), key="comp_item_b")
                    with cc4:
                        metric_col = st.selectbox("Measure Metric:", num_cols, key="comp_num_col")

                    if st.button("⚖️ Run Dimensional Comparison", use_container_width=True):
                        comp_res = ComparisonEngine.compare_dimensions(active_df, dim_col, item_a, item_b, metric_col)
                        if comp_res.get("available"):
                            st.markdown(f"### {comp_res['summary']}")
                            r1, r2, r3, r4 = st.columns(4)
                            r1.metric(f"Entity A ({item_a})", f"${comp_res['val_a']:,.2f}", delta=f"{comp_res['count_a']:,} records")
                            r2.metric(f"Entity B ({item_b})", f"${comp_res['val_b']:,.2f}", delta=f"{comp_res['count_b']:,} records")
                            r3.metric("Absolute Difference", f"${abs(comp_res['diff_abs']):,.2f}")
                            r4.metric("Percentage Delta", f"{comp_res['diff_pct']:+.1f}%")
                        else:
                            st.warning(comp_res.get("reason", "Comparison unavailable."))
                else:
                    st.info("Requires at least one categorical and one numeric column.")

            with single_comp_tab2:
                date_col = kpis.get("date_col")
                metric_col = kpis.get("primary_metric_col")
                if date_col and metric_col and date_col in active_df.columns and metric_col in active_df.columns:
                    p_res = ComparisonEngine.compare_periods(active_df, date_col, metric_col)
                    if p_res.get("available"):
                        st.markdown(f"### {p_res['summary']}")
                        p1, p2, p3 = st.columns(3)
                        p1.metric(p_res["p1_label"], f"${p_res['p1_val']:,.2f}")
                        p2.metric(p_res["p2_label"], f"${p_res['p2_val']:,.2f}", delta=f"{p_res['diff_pct']:+.1f}%")
                        p3.metric("Net Period Growth", f"${p_res['diff_abs']:+,.2f}")
                    else:
                        st.info(p_res.get("reason", "Period comparison unavailable."))
                else:
                    st.info("Time period comparison requires a valid date column and numeric measure.")
        else:
            render_no_data_state("Upload a dataset above to run single-dataset dimensional and temporal comparisons.")


def render_targets_goals(active_df, kpis, user_active):
    """Section 5: Target Attainment, Forecasting & Scenario Modeling"""
    if user_active and not active_df.empty:
        st.markdown("##### 🎯 Strategic Targets & What-If Scenario Modeling")
        primary_metric = kpis.get("primary_metric_col", "total_revenue")
        current_rev = float(kpis.get("total_revenue", 0.0))

        t_col1, t_col2 = st.columns([1, 1.5])
        with t_col1:
            st.markdown("###### Target Attainment Tracker")
            target_val = st.number_input(
                "Set Target Goal ($):",
                value=float(AnalyticsManager.get_targets().get(primary_metric, current_rev * 1.15)),
                step=1000.0
            )
            if st.button("💾 Save Target Goal", use_container_width=True):
                AnalyticsManager.set_target(primary_metric, target_val)
                st.success("Target saved!")

            # Evaluate Target
            t_eval = TargetEngine.evaluate_target(current_rev, target_val, "Gross Target")
            st.metric("Current Attainment", f"{t_eval['attainment_pct']:.1f}%",
                      delta=f"${t_eval['gap']:+,.2f} gap" if t_eval['gap'] > 0 else "Target Exceeded! 🎯")
            st.progress(min(1.0, t_eval['attainment_pct'] / 100.0))

        with t_col2:
            st.markdown("###### What-If Strategic Scenario Modeler")
            vol_growth = st.slider("Projected Volume Growth (%):", -50, 100, 10)
            price_change = st.slider("Price / Unit Value Shift (%):", -30, 50, 5)
            cost_shift = st.slider("Logistics / Operating Cost Shift (%):", -30, 50, 0)

            scen_rev = current_rev * (1 + vol_growth / 100.0) * (1 + price_change / 100.0)
            scen_delta = scen_rev - current_rev

            s1, s2 = st.columns(2)
            s1.metric("Projected Scenario Outcome", f"${scen_rev:,.2f}", delta=f"{scen_delta:+,.2f} ({scen_delta/max(1, current_rev)*100:+.1f}%)")
            s2.metric("Scenario vs Target", f"${scen_rev - target_val:+,.2f}", delta="Surplus" if scen_rev >= target_val else "Deficit")
    else:
        render_no_data_state("Upload a dataset above to set targets and run scenario modeling.")


def render_ask_your_data(active_df, schema, kpis, user_active):
    """Section 6: AI Business Analyst Query Assistant"""
    if user_active and not active_df.empty:
        st.markdown("##### 🤖 Ask Your Data — Autonomous AI Business Analyst")
        st.caption("Ask natural-language business questions about the active dataset to receive verified answers, explanations, and dynamic charts:")

        q_input = st.text_input(
            "Enter your analytical question:",
            placeholder="e.g., 'What is my total sales?', 'Which department earns the most?', 'Show monthly trend'"
        )

        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
        with preset_col1:
            if st.button("📊 Total Performance", use_container_width=True):
                q_input = "What is the total revenue?"
        with preset_col2:
            if st.button("🏆 Top Categories", use_container_width=True):
                q_input = "Which category performs best?"
        with preset_col3:
            if st.button("📈 Time Trend", use_container_width=True):
                q_input = "Show sales trend over time"
        with preset_col4:
            if st.button("⚠️ Data Anomalies", use_container_width=True):
                q_input = "Are there any outliers in the dataset?"

        if q_input:
            ans = AskYourDataEngine.answer_question(active_df, q_input, schema, kpis)
            st.markdown(f"""
            <div style="background: rgba(15,23,42,0.8); border-left: 4px solid #38bdf8;
                        border-radius: 8px; padding: 16px 20px; margin: 16px 0;">
                <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">
                    Analytical Answer
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-top: 6px;">
                    {ans.get('answer')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if ans.get("data") is not None and isinstance(ans["data"], pd.DataFrame) and not ans["data"].empty:
                st.dataframe(ans["data"], use_container_width=True)

            if ans.get("figure") is not None:
                st.plotly_chart(ans["figure"], use_container_width=True)
    else:
        render_no_data_state("Upload a dataset above to query data with the AI Business Analyst.")


def render_saved_workspaces(active_df, res, user_active):
    """Section 7: Saved Workspaces & State Snapshots"""
    if user_active and not active_df.empty:
        st.markdown("##### 💾 Saved Workspaces & Analytical Snapshots")
        st.caption("Snapshot your cleaned datasets, active filters, strategic goals, and cleaning recipes for persistent retrieval:")

        ws_c1, ws_c2 = st.columns([2, 1])
        with ws_c1:
            ws_name = st.text_input("Workspace Snapshot Name:", value=f"Workspace_{res.get('dataset_name', 'Data')[:15]}")
        with ws_c2:
            default_tag = res.get('schema', {}).get('domain', 'Analytics')
            st.text_input("Domain / Category Tag:", value=default_tag, disabled=True)

        ws_desc = st.text_area("Description / Notes:", value="Analytical checkpoint created in AUREVIX BI Workspace.")
        
        if st.button("💾 Save Current Workspace State", use_container_width=True):
            try:
                snap_res = WorkspaceManager.save_workspace(
                    name=ws_name,
                    dataset_id=res.get("dataset_id") or "user_active_dataset",
                    dataset_name=res.get("dataset_name") or "Active Dataset",
                    filters=AnalyticsManager.get_workspace_state().get("active_filters", {}),
                    targets=AnalyticsManager.get_targets(),
                    dashboard_layout=AnalyticsManager.get_dashboard_layout(),
                    cleaning_recipe=AnalyticsManager.get_workspace_state().get("cleaning_recipe", []),
                    notes=ws_desc
                )
                st.success(f"✅ Workspace '{ws_name}' saved successfully (Snapshot ID: `{snap_res.get('snapshot_id', 'N/A')}`)!")
            except Exception as exc:
                st.error(f"⚠️ Failed to save workspace: {str(exc)}")

        # List Existing Snapshots
        st.markdown("---")
        st.markdown("###### 📂 Available Saved Workspaces")
        saved_list = WorkspaceManager.list_saved_workspaces()
        if saved_list:
            for ws_item in saved_list:
                w_id = ws_item.get("workspace_id", "ws")
                w_name = ws_item.get("name", "Saved Workspace")
                w_ds = ws_item.get("dataset_name", "Dataset")
                w_date = ws_item.get("updated_at") or ws_item.get("created_at", "N/A")
                w_notes = ws_item.get("notes", "")
                w_targets_cnt = len(ws_item.get("targets", {}))
                w_recipe_cnt = len(ws_item.get("cleaning_recipe", []))

                with st.expander(f"📁 {w_name} — `{w_ds}` ({w_date})", expanded=False):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Dataset", str(w_ds)[:20])
                    m2.metric("Saved Targets", str(w_targets_cnt))
                    m3.metric("Cleaning Steps", str(w_recipe_cnt))
                    m4.metric("Snapshot ID", str(w_id)[:15])

                    if w_notes:
                        st.caption(f"**Notes:** {w_notes}")

                    b_c1, b_c2 = st.columns([1, 1])
                    with b_c1:
                        if st.button(f"🔄 Restore Workspace", key=f"btn_restore_{w_id}", use_container_width=True):
                            restored = WorkspaceManager.restore_workspace(w_id)
                            if restored:
                                st.success(f"Workspace '{w_name}' state restored successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to restore workspace snapshot.")
                    with b_c2:
                        if st.button(f"🗑️ Delete Snapshot", key=f"btn_del_{w_id}", use_container_width=True):
                            WorkspaceManager.delete_workspace(w_id)
                            st.success(f"Snapshot '{w_name}' deleted.")
                            st.rerun()
        else:
            st.info("No saved workspaces found. Save your current analytical state above.")
    else:
        render_no_data_state("Upload a dataset above to manage saved workspace snapshots.")


def render_export_center(active_df, res, user_active):
    """Section 8: Executive Governance & Multi-Format Export Center"""
    if user_active and not active_df.empty:
        st.markdown("##### 📄 Executive Governance & Multi-Format Export Center")
        st.caption("Export working datasets, data quality audit reports, KPI summaries, executive briefings, and comparative reports:")

        from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType

        def _log_export_event(fmt: str):
            try:
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.DATA_EXPORT,
                    source="dashboard.workspace.export",
                    dataset_id=res.get("dataset_id"),
                    metadata={"export_format": fmt, "dataset_name": res.get("dataset_name", "dataset")}
                )
            except Exception:
                pass

        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            st.markdown("###### 📊 Cleaned Dataset & BI Workbook")
            from dashboard.analytics.security_utils import sanitize_for_spreadsheet_export
            safe_export_df = sanitize_for_spreadsheet_export(active_df)
            csv_data = safe_export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Cleaned CSV",
                data=csv_data,
                file_name=f"aurevix_cleaned_{res.get('dataset_name', 'dataset')}.csv",
                mime="text/csv",
                on_click=_log_export_event,
                args=("csv",),
                use_container_width=True
            )
            # Enterprise 10-sheet BI Excel Report
            excel_bytes = ExecutiveReportGenerator.generate_excel_report(res, active_df)
            st.download_button(
                label="⬇️ Download Executive BI Report (.xlsx)",
                data=excel_bytes,
                file_name=f"aurevix_bi_report_{res.get('dataset_name', 'dataset')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                on_click=_log_export_event,
                args=("xlsx",),
                use_container_width=True
            )
            # Parquet export
            parquet_buf = io.BytesIO()
            active_df.to_parquet(parquet_buf, index=False)
            st.download_button(
                label="⬇️ Download Cleaned Parquet",
                data=parquet_buf.getvalue(),
                file_name=f"aurevix_cleaned_{res.get('dataset_name', 'dataset')}.parquet",
                mime="application/octet-stream",
                on_click=_log_export_event,
                args=("parquet",),
                use_container_width=True
            )
            json_data = active_df.to_json(orient="records", date_format="iso").encode("utf-8")
            st.download_button(
                label="⬇️ Download Cleaned JSON",
                data=json_data,
                file_name=f"aurevix_cleaned_{res.get('dataset_name', 'dataset')}.json",
                mime="application/json",
                on_click=_log_export_event,
                args=("json",),
                use_container_width=True
            )

        with ex_col2:
            st.markdown("###### 🛡️ Quality Audit Report")
            audit_report = ExecutiveReportGenerator.generate_quality_report(res)
            st.download_button(
                label="⬇️ Download Quality Audit (Markdown)",
                data=audit_report,
                file_name="aurevix_data_quality_audit.md",
                mime="text/markdown",
                on_click=_log_export_event,
                args=("quality_markdown",),
                use_container_width=True
            )

        with ex_col3:
            st.markdown("###### 🏛️ Executive Strategy Briefing")
            # PDF Executive Briefing
            pdf_bytes = ExecutiveReportGenerator.generate_pdf_report(res, active_df)
            st.download_button(
                label="⬇️ Download Executive Brief (PDF)",
                data=pdf_bytes,
                file_name=f"aurevix_executive_brief_{res.get('dataset_name', 'dataset')}.pdf",
                mime="application/pdf",
                on_click=_log_export_event,
                args=("executive_pdf",),
                use_container_width=True
            )
            exec_brief = ExecutiveReportGenerator.generate_executive_briefing(res, active_df)
            st.download_button(
                label="⬇️ Download Executive Brief (Markdown)",
                data=exec_brief,
                file_name="aurevix_executive_strategy_brief.md",
                mime="text/markdown",
                on_click=_log_export_event,
                args=("executive_markdown",),
                use_container_width=True
            )

        # Dual-Dataset Comparison Report Export (if comparison datasets active)
        if AnalyticsManager.has_comparison_datasets():
            st.markdown("---")
            st.markdown("##### ⚖️ Dual-Dataset Comparative Intelligence Export")
            comp_res = AnalyticsManager.get_comparison_state().get("comparison_results", {})
            if comp_res:
                cx1, cx2 = st.columns(2)
                with cx1:
                    comp_pdf_bytes = ExecutiveReportGenerator.generate_comparison_pdf(comp_res)
                    st.download_button(
                        label="⬇️ Download Comparison Audit (PDF)",
                        data=comp_pdf_bytes,
                        file_name="aurevix_dual_dataset_comparison_audit.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with cx2:
                    comp_report = ExecutiveReportGenerator.generate_comparison_report(comp_res)
                    st.download_button(
                        label="⬇️ Download Comparison Audit (Markdown)",
                        data=comp_report,
                        file_name="aurevix_dual_dataset_comparison_audit.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
    else:
        render_no_data_state("Upload a dataset above to export data and executive intelligence reports.")


# =====================================================================
# MAIN WORKSPACE INGESTION & GLOBAL CONTROL BAR
# =====================================================================

user_active = AnalyticsManager.is_user_mode()
res = AnalyticsManager.get_analysis_results()
active_df = AnalyticsManager.get_active_df()
schema = res.get("schema", {})
prof = res.get("profile", {})
kpis = res.get("kpis", {})
recipe = st.session_state.get("workspace", {}).get("cleaning_recipe", [])
init_prof = st.session_state.get("workspace", {}).get("initial_profile", prof)
ws_state = AnalyticsManager.get_workspace_state()

mode_text = f"USER DATA ({res.get('dataset_name', 'Custom')[:15]})" if user_active else "DEMO MODE (PRODUCTION TARGETS)"
render_html(
    f"""
    <div class="top-header-bar">
        <div class="top-header-left">
            <div class="header-icon-badge">📂</div>
            <div>
                <div class="header-title-text">Universal Business Data Analytics Workspace</div>
                <div class="header-title-sub">Ingest arbitrary CSV, Excel, Parquet, or JSON datasets with schema detection, automated cleaning &amp; interactive BI</div>
            </div>
        </div>
        <div class="top-header-right">
            <span class="status-pill-green"><span class="status-dot-pulse"></span> {mode_text}</span>
        </div>
    </div>
    """
)

# File Ingestion Center
u_col1, u_col2, u_col3 = st.columns([2.5, 1, 1])
with u_col1:
    uploaded_file = st.file_uploader(
        "Upload any business dataset (CSV, XLSX, JSON, Parquet):",
        type=["csv", "xlsx", "xls", "json", "parquet"],
        key="workspace_file_uploader",
        help="Upload arbitrary business data for instant profiling, quality scoring, cleaning & KPI generation"
    )
with u_col2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if user_active and st.button("🗑️ Clear Dataset", use_container_width=True, help="Clears current dataset from active workspace"):
        AnalyticsManager.clear_active_dataset()
        st.rerun()
with u_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if user_active and st.button("🧹 Purge Cache", use_container_width=True, help="Purges all persisted user dataset files from disk"):
        AnalyticsManager.purge_persistent_storage()
        st.success("Persisted workspace storage purged.")
        st.rerun()

if uploaded_file is not None:
    try:
        df_loaded, f_hash = UniversalDataLoader.load_file(uploaded_file)
        if isinstance(df_loaded, pd.DataFrame) and not df_loaded.empty:
            curr_id = ws_state.get("dataset_id")
            if curr_id != f_hash:
                AnalyticsManager.activate_user_dataset(df_loaded, uploaded_file.name, f_hash, data_source="user_upload")
                st.success(f"Loaded '{uploaded_file.name}' ({len(df_loaded):,} rows, {len(df_loaded.columns)} columns)")
                st.rerun()
    except Exception as exc:
        st.error(f"⚠️ Unable to load '{getattr(uploaded_file, 'name', 'file')}': {str(exc)}")

# Sample Dataset Quick-Loaders
st.markdown("###### Or load a curated enterprise sample dataset:")
s_col1, s_col2, s_col3, s_col4 = st.columns(4)
with s_col1:
    if st.button("🛒 Retail Sales (CSV)", use_container_width=True):
        p = PROJECT_ROOT / "data" / "samples" / "retail_sales.csv"
        df, fhash = UniversalDataLoader.load_and_fingerprint(str(p), "retail_sales.csv")
        AnalyticsManager.activate_user_dataset(df, "retail_sales.csv", fhash, data_source="sample_dataset")
        st.rerun()
with s_col2:
    if st.button("💼 HR Workforce (XLSX)", use_container_width=True):
        p = PROJECT_ROOT / "data" / "samples" / "employee_data.xlsx"
        df, fhash = UniversalDataLoader.load_and_fingerprint(str(p), "employee_data.xlsx")
        AnalyticsManager.activate_user_dataset(df, "employee_data.xlsx", fhash, data_source="sample_dataset")
        st.rerun()
with s_col3:
    if st.button("📢 Marketing (CSV)", use_container_width=True):
        p = PROJECT_ROOT / "data" / "samples" / "marketing_campaign.csv"
        df, fhash = UniversalDataLoader.load_and_fingerprint(str(p), "marketing_campaign.csv")
        AnalyticsManager.activate_user_dataset(df, "marketing_campaign.csv", fhash, data_source="sample_dataset")
        st.rerun()
with s_col4:
    if st.button("🗃️ Load AUREVIX Demo Dataset", use_container_width=True):
        AnalyticsManager.revert_to_demo()
        st.info("Reverted to Olist demo mode. Upload a dataset to return to analyst mode.")
        st.rerun()

st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

# =====================================================================
# TRUE LAZY SECTION SELECTOR & RENDERING
# =====================================================================
SECTIONS = [
    "📥 Ingest & Quality Center",
    "🧹 Clean & Transform",
    "🔎 Data Explorer",
    "⚖️ Compare",
    "🎯 Targets & Goals",
    "🤖 Ask Your Data",
    "💾 Saved Workspaces",
    "📄 Export Center"
]


# System Component Health Status Indicator Area
data_ready = user_active and not active_df.empty
analytics_ready = bool(res.get("kpis")) and not active_df.empty if user_active else False
dq_ready = bool(res.get("profile")) and not active_df.empty if user_active else False
comp_ready = AnalyticsManager.has_comparison_datasets()
export_ready = data_ready

st.markdown(
    f"""
    <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; font-size: 0.75rem; font-weight: 600; padding: 6px 12px; background: rgba(15,23,42,0.5); border-radius: 6px; border: 1px solid rgba(148,163,184,0.1);">
        <span style="color: {'#10b981' if data_ready else '#94a3b8'};">{'●' if data_ready else '○'} DATA {'READY' if data_ready else 'IDLE'}</span>
        <span style="color: {'#10b981' if analytics_ready else '#94a3b8'};">{'●' if analytics_ready else '○'} ANALYTICS {'READY' if analytics_ready else 'IDLE'}</span>
        <span style="color: {'#10b981' if dq_ready else '#94a3b8'};">{'●' if dq_ready else '○'} DATA QUALITY {'READY' if dq_ready else 'IDLE'}</span>
        <span style="color: {'#10b981' if comp_ready else '#94a3b8'};">{'●' if comp_ready else '○'} COMPARISON {'READY' if comp_ready else 'IDLE'}</span>
        <span style="color: {'#10b981' if export_ready else '#94a3b8'};">{'●' if export_ready else '○'} EXPORT {'READY' if export_ready else 'IDLE'}</span>
    </div>
    """,
    unsafe_allow_html=True
)

current_active_section = AnalyticsManager.get_active_section()
default_index = SECTIONS.index(current_active_section) if current_active_section in SECTIONS else 0

selected_section = st.radio(
    "Workspace Navigation",
    options=SECTIONS,
    index=default_index,
    horizontal=True,
    label_visibility="collapsed",
    key="active_workspace_section_radio"
)

AnalyticsManager.set_active_section(selected_section)

# Execute ONLY the selected section render function
t_sec_start = time.perf_counter()

if selected_section == "📥 Ingest & Quality Center":
    render_ingest_quality_center(active_df, res, schema, prof, kpis, user_active)
elif selected_section == "🧹 Clean & Transform":
    render_clean_transform(active_df, res, schema, prof, recipe, init_prof, user_active)
elif selected_section == "🔎 Data Explorer":
    render_data_explorer(active_df, res, schema, user_active)
elif selected_section == "⚖️ Compare":
    render_compare(active_df, kpis, user_active)
elif selected_section == "🎯 Targets & Goals":
    render_targets_goals(active_df, kpis, user_active)
elif selected_section == "🤖 Ask Your Data":
    render_ask_your_data(active_df, schema, kpis, user_active)
elif selected_section == "💾 Saved Workspaces":
    render_saved_workspaces(active_df, res, user_active)
elif selected_section == "📄 Export Center":
    render_export_center(active_df, res, user_active)

sec_duration = time.perf_counter() - t_sec_start
shell_duration = time.perf_counter() - t_shell_start

sec_name_clean = selected_section.encode("ascii", "ignore").decode("ascii").strip()
logger.info(f"[PERF] Data Workspace shell: {shell_duration:.4f}s")
logger.info(f"[PERF] Section '{sec_name_clean}': {sec_duration:.4f}s")

# ---------------------------------------------------------------------
# Developer Diagnostics & Governance Audit Trail
# ---------------------------------------------------------------------
with st.expander("🔧 Developer Diagnostics, Governance & Audit Trail", expanded=False):
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Workspace Exists", "TRUE" if ws_state["workspace_exists"] else "FALSE")
    d2.metric("User Mode", "TRUE" if ws_state["user_mode"] else "FALSE")
    d3.metric("Dataset Name", ws_state.get("dataset_name") or "None")
    d4.metric("Dataset ID", ws_state.get("dataset_id") or "N/A")

    dd1, dd2, dd3, dd4 = st.columns(4)
    dd1.metric("Data Source", ws_state.get("data_source") or "None")
    dd2.metric("Dataset Version", f"v{ws_state.get('dataset_version', 1)}")
    dd3.metric("Working Rows", f"{ws_state['raw_rows']:,}")
    dd4.metric("Working Columns", f"{ws_state['raw_cols']:,}")

    ddd1, ddd2, ddd3, ddd4 = st.columns(4)
    ddd1.metric("Cache Status", ws_state.get("cache_status", "MISS"))
    ddd2.metric("Analysis Status", ws_state.get("analysis_status", "idle").upper())
    ddd3.metric("Cache Hits Count", f"{ws_state.get('cache_hits', 0):,}")
    ddd4.metric("Cleaning Recipe Steps", f"{ws_state['cleaning_steps_count']}")

    # Performance Latency Metrics
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("⚡ Dataset Load", f"{ws_state.get('load_time_ms', 0.0):.1f} ms")
    t2.metric("🛡️ Fast Profile", f"{ws_state.get('fast_profile_time_ms', 0.0):.1f} ms")
    t3.metric("🔬 Deep Analysis", f"{ws_state.get('deep_analysis_time_ms', 0.0):.1f} ms")
    t4.metric("⏱️ Section Execution", f"{sec_duration * 1000:.1f} ms")
    t5.metric("🚀 Shell Latency", f"{shell_duration * 1000:.1f} ms")

    # Audit Trail Governance Table
    st.markdown("---")
    st.markdown("###### 📜 Chronological Governance Audit Trail")
    logs = AuditTrail.get_logs(limit=15)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else:
        st.caption("No audit events recorded yet.")
