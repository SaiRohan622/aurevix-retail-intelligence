import streamlit as st
import pandas as pd
from dashboard.analytics.data_cache import AnalyticsManager
from dashboard.components.html_utils import render_html


def render_global_filter_bar():
    """Renders interactive slicers matching the active dataset dimensions."""
    if not AnalyticsManager.is_user_mode():
        return

    res = AnalyticsManager.get_analysis_results()
    schema = res.get("schema", {})
    # FIX: was reading st.session_state.get("active_dataframe") — key never existed.
    # Correct: use AnalyticsManager.get_raw_df() which reads workspace["raw_df"].
    df_raw = AnalyticsManager.get_raw_df()
    if df_raw is None or df_raw.empty:
        return

    cat_cols = schema.get("categorical_columns", [])
    date_cols = schema.get("date_columns", [])

    if not cat_cols and not date_cols:
        return

    with st.expander("🔍 Global Slicers & Dynamic Dimension Filters", expanded=False):
        with st.form("global_filter_form"):
            num_cols = min(4, max(1, len(cat_cols[:3]) + (1 if date_cols else 0)))
            f_cols = st.columns(num_cols)
            selected_filters = {}
            col_idx = 0

            if date_cols:
                d_col = date_cols[0]
                with f_cols[col_idx % num_cols]:
                    try:
                        dt_series = pd.to_datetime(df_raw[d_col], errors="coerce")
                        min_d = dt_series.min()
                        max_d = dt_series.max()
                        if pd.notnull(min_d) and pd.notnull(max_d) and min_d.date() != max_d.date():
                            d_range = st.date_input(
                                f"Date Range ({d_col}):",
                                [min_d.date(), max_d.date()],
                                key="flt_date"
                            )
                            if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
                                selected_filters[d_col] = (d_range[0], d_range[1])
                    except Exception:
                        pass
                col_idx += 1

            for c_col in cat_cols[:3]:
                with f_cols[col_idx % num_cols]:
                    opts = sorted(list(df_raw[c_col].dropna().unique().astype(str)))
                    selected = st.multiselect(f"{c_col}:", options=opts, default=[],
                                              key=f"flt_{c_col}")
                    if selected:
                        selected_filters[c_col] = selected
                col_idx += 1

            btn_col1, btn_col2, btn_spacer = st.columns([1.2, 1.2, 4])
            with btn_col1:
                submitted = st.form_submit_button("⚡ Apply Filters", use_container_width=True)
            with btn_col2:
                reset = st.form_submit_button("🔄 Reset Filters", use_container_width=True)

            if submitted:
                AnalyticsManager.apply_filters(selected_filters)
                st.rerun()
            elif reset:
                AnalyticsManager.apply_filters({})
                st.rerun()
