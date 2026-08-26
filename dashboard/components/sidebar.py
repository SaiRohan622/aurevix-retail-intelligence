"""
AUREVIX — Sidebar & Global Navigation
"""

import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 10px 0 20px 0; border-bottom: 1px solid #374151;">
                <div style="font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; color: #f3f4f6;">
                    AUREVIX
                </div>
                <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 2px;">
                    From raw events to intelligent decisions.
                </div>
                <div style="margin-top: 12px;">
                    <span class="live-pulse"><span class="live-dot"></span> PLATFORM ONLINE</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("PLATFORM CONTROLS")
        if st.button("🔄 Refresh Telemetry", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("INFRASTRUCTURE MATRIX")
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: #9ca3af; line-height: 1.6;">
                • <b>Engine:</b> PySpark 4.2.0<br>
                • <b>Stream:</b> Apache Kafka<br>
                • <b>Warehouse:</b> PostgreSQL 16<br>
                • <b>dbt:</b> dbt-postgres 1.11.0<br>
                • <b>Airflow:</b> Orchestrated DAGs<br>
                • <b>Tests:</b> 33/33 Passed
            </div>
            """,
            unsafe_allow_html=True
        )
