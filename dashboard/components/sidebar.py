"""
AUREVIX — Sidebar & Global Navigation
Displays Global Data Source mode switch, Domain Intelligence, and system telemetry.
"""

import streamlit as st
from dashboard.components.html_utils import render_html
from dashboard.analytics.data_cache import AnalyticsManager


def render_sidebar():
    AnalyticsManager.initialize()
    with st.sidebar:
        render_html(
            """
            <div class="sb-header-box">
                <div class="sb-logo-title">⚡ AUREVIX</div>
                <div style="font-size: 0.65rem; font-weight: 700; color: #38bdf8; letter-spacing: 0.08em; text-transform: uppercase;">ENTERPRISE BI & ANALYTICS</div>
                <div class="sb-tagline">From raw events to intelligent decisions.</div>
                <div style="margin-top: 10px;">
                    <span class="status-pill-green"><span class="status-dot-pulse"></span> PLATFORM ONLINE</span>
                </div>
            </div>
            """
        )

        render_html('<div class="nav-section-title">GLOBAL DATA SOURCE</div>')
        
        if AnalyticsManager.is_user_mode():
            res = AnalyticsManager.get_analysis_results()
            ds_name = res.get("dataset_name", "Uploaded Dataset")
            prof = res.get("profile", {})
            schema = res.get("schema", {})
            domain = schema.get("domain", "Enterprise Dataset")
            conf = schema.get("domain_confidence", 85)
            row_count = prof.get("row_count", 0)
            col_count = prof.get("col_count", 0)
            
            render_html(
                f"""
                <div style="padding: 10px 12px; border-radius: 8px; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.3); font-size: 0.725rem; margin-bottom: 10px;">
                    <div style="color: #38bdf8; font-weight: 700; display: flex; align-items: center; justify-content: space-between;">
                        <span><span class="status-dot-pulse"></span> USER DATA ACTIVE</span>
                        <span style="font-size: 0.625rem; color: #10b981; font-weight: 700;">{conf}% Match</span>
                    </div>
                    <div style="color: #ffffff; font-weight: 600; margin-top: 4px; word-break: break-all;">📁 {ds_name}</div>
                    <div style="color: #94a3b8; font-size: 0.675rem; margin-top: 2px;">🏷️ {domain}</div>
                    <div style="color: #64748b; font-size: 0.65rem; margin-top: 2px;">{row_count:,} Rows • {col_count} Columns</div>
                </div>
                """
            )
            if st.button("🔄 Clear Dataset (Return to Demo)", key="sb_clear_btn", use_container_width=True):
                AnalyticsManager.revert_to_demo()
                st.rerun()
        else:
            render_html(
                """
                <div style="padding: 10px 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.725rem; margin-bottom: 10px;">
                    <div style="color: #10b981; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                        <span class="status-dot-pulse"></span> DEMO MODE (PRODUCTION)
                    </div>
                    <div style="color: #ffffff; font-weight: 600; margin-top: 4px;">📁 Olist Brazilian E-Commerce</div>
                    <div style="color: #94a3b8; font-size: 0.675rem; margin-top: 2px;">1.55M Rows • Gold Star Schema</div>
                </div>
                """
            )

        render_html(
            """
            <style>
            [data-testid="stSidebarNav"] a[href*="Security_Center"],
            [data-testid="stSidebarNav"] a[href*="11_Security_Center"],
            [data-testid="stSidebarNav"] li:has(a[href*="Security_Center"]),
            [data-testid="stSidebarNav"] li:has(a[href*="11_Security_Center"]) {
                display: none !important;
            }
            </style>
            """
        )

        from dashboard.analytics.auth_manager import AuthManager
        if AuthManager.is_authenticated() and AuthManager.has_role("ADMIN"):
            render_html(
                """
                <div style="margin: 14px 0 6px 0; border-top: 1px solid #1e293b; padding-top: 10px;">
                    <div class="nav-section-title" style="color: #f87171; letter-spacing: 0.08em;">ADMINISTRATION</div>
                </div>
                """
            )
            try:
                st.page_link("pages/11_Security_Center.py", label="Security Center", icon="🛡️")
            except Exception:
                pass

        render_html('<div class="nav-section-title">SECURITY & SESSION</div>')
        if AuthManager.is_authenticated():
            curr_u = AuthManager.get_current_user() or {}
            u_name = curr_u.get("display_name", "Analyst")
            u_role = curr_u.get("role", "USER")
            render_html(
                f"""
                <div style="padding: 10px 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.725rem; margin-bottom: 8px;">
                    <div style="color: #10b981; font-weight: 700;">👤 {u_name}</div>
                    <div style="color: #94a3b8; font-size: 0.65rem; margin-top: 2px;">Role: <b style="color:#f8fafc;">{u_role}</b> • Session Active</div>
                </div>
                """
            )
            if st.button("🚪 Sign Out", key="sb_logout_btn", use_container_width=True):
                AuthManager.logout()
                st.rerun()
        else:
            render_html(
                """
                <div style="padding: 10px 12px; border-radius: 8px; background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); font-size: 0.725rem; margin-bottom: 8px;">
                    <div style="color: #94a3b8; font-weight: 600;">🔒 Guest Analyst Mode</div>
                </div>
                """
            )
            if st.button("🔑 Sign In / Sign Up", key="sb_login_nav_btn", use_container_width=True):
                st.session_state["top_auth_active_tab"] = "signin"
                st.rerun()

        render_html('<div class="nav-section-title">QUICK ACTIONS</div>')
        if st.button("🔄 Refresh Cache & Data", key="sb_refresh_btn", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        render_html(
            """
            <div style="margin-top: 24px; padding: 12px; border-radius: 8px; background: rgba(22, 32, 53, 0.4); border: 1px solid #192338; font-size: 0.725rem; color: #64748b;">
                <div style="font-weight: 700; color: #94a3b8; margin-bottom: 2px;">AUREVIX v2.1.0 BI</div>
                <div>Universal Schema-Aware BI Engine.</div>
                <div style="display: flex; align-items: center; gap: 6px; margin-top: 8px; color: #10b981; font-weight: 600;">
                    <span class="status-dot-pulse"></span> Low-Latency Engine Ready
                </div>
            </div>
            """
        )
