"""
AUREVIX — Custom KPI Card Component
"""

import streamlit as st


def render_kpi_card(title: str, value: str, subtext: str = "", delta: str = "", is_positive: bool = True):
    delta_class = "positive" if is_positive else "neutral"
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""
    sub_html = f'<div style="font-size: 0.75rem; color: #6b7280; margin-top: 4px;">{subtext}</div>' if subtext else ""

    html = f'''
    <div class="kpi-container">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
        {sub_html}
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
