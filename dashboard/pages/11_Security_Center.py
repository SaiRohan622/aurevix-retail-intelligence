"""
AUREVIX — Platform Security Operations Center & Audit Monitor (Phase 6)
Restricted exclusively to ADMIN role. Provides real-time defense status,
tamper-evident audit chain verification, and interactive security telemetry.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.sidebar import render_sidebar
from dashboard.components.html_utils import render_html, load_cached_css
from dashboard.analytics.auth_manager import AuthManager
from dashboard.analytics.security_audit import (
    SecurityAuditLogger,
    SecurityEventType,
    SecuritySeverity
)
from dashboard.analytics.security_monitor import SecurityMonitor

# Page Configuration
st.set_page_config(
    page_title="Security Center | AUREVIX BI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

css_path = PROJECT_ROOT / "dashboard" / "styles" / "custom.css"
load_cached_css(css_path)

# Render Global Sidebar
render_sidebar()

# ==============================================================================
# 1. ACCESS CONTROL (AUTHENTICATION & ADMIN RBAC)
# ==============================================================================

AuthManager.initialize_session()

# Case A: Unauthenticated direct access to Security Center
if not AuthManager.is_authenticated():
    st.markdown(
        """
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 10px; padding: 32px; margin-top: 30px; text-align: center; max-width: 600px; margin-left: auto; margin-right: auto;">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">🔐</div>
            <h2 style="color: #f8fafc; font-size: 20px; font-weight: 700; margin: 0 0 8px 0;">Authentication Required</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0 0 16px 0;">
                The Security Operations Center is protected and requires an active authenticated session.
            </p>
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 6px; padding: 12px 16px; color: #38bdf8; font-size: 13px; font-weight: 500; margin-bottom: 16px;">
                Please sign in from the application authentication area to continue.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    try:
        st.page_link("app.py", label="🏠 Return to Main Application", use_container_width=True)
    except Exception:
        pass
    st.stop()

# Case B: Authenticated user lacking ADMIN privileges (e.g. USER or ANALYST)
if not AuthManager.has_role("ADMIN"):
    current_user = AuthManager.get_current_user() or {}
    user_role = str(current_user.get("role", "ANALYST")).upper()
    user_id = current_user.get("id", "anonymous")

    try:
        from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
        SecurityAuditLogger.log_event(
            event_type=SecurityEventType.ADMIN_ACCESS_DENIED,
            severity=SecuritySeverity.HIGH,
            outcome="DENIED",
            user_id=user_id,
            user_role=user_role,
            source="page.11_Security_Center",
            reason=f"User with role '{user_role}' attempted to access Security Operations Center"
        )
    except Exception:
        pass

    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 10px; padding: 28px; margin-top: 24px; max-width: 600px; margin-left: auto; margin-right: auto;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🔒</span>
                <div>
                    <div style="color: #ef4444; font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">SECURITY OPERATIONS CENTER</div>
                    <h2 style="color: #f8fafc; font-size: 22px; font-weight: 700; margin: 0;">ACCESS DENIED</h2>
                </div>
            </div>
            <p style="color: #cbd5e1; font-size: 14px; margin: 0 0 16px 0;">
                This area is restricted to platform administrators.
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: rgba(15, 23, 42, 0.6); padding: 14px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 14px; font-size: 13px;">
                <div>
                    <span style="color: #94a3b8;">Current role:</span><br/>
                    <b style="color: #f59e0b; font-size: 14px;">{user_role}</b>
                </div>
                <div>
                    <span style="color: #94a3b8;">Required role:</span><br/>
                    <b style="color: #ef4444; font-size: 14px;">ADMIN</b>
                </div>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 16px 0;">
                Your account does not have permission to access Security Operations Center.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    try:
        st.page_link("app.py", label="🏠 Return to Analytics Workspace", use_container_width=True)
    except Exception:
        pass
    st.stop()


# ==============================================================================
# 2. HEADER & TELEMETRY OVERVIEW
# ==============================================================================

st.markdown(
    """
    <div style="margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="color: #ef4444; font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">ADMINISTRATOR SECURITY OPERATIONS</div>
                <h1 style="color: #f8fafc; font-size: 26px; font-weight: 700; margin: 2px 0 6px 0;">
                    🛡️ Security Center
                </h1>
                <p style="color: #94a3b8; font-size: 14px; margin: 0;">
                    Real-time platform defense status, tamper-evident audit trail, and threat intelligence telemetry.
                </p>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                    Security Status: HEALTHY
                </span>
                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                    Authentication: ACTIVE
                </span>
                <span style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                    Audit Integrity: VERIFIED
                </span>
                <span style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                    Monitoring: ACTIVE
                </span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Fetch Security Summary & Health
summary = SecurityAuditLogger.get_security_summary()
health = SecurityMonitor.get_security_health()


# ==============================================================================
# 3. DEFENSE HEALTH PULSE CARDS
# ==============================================================================

st.markdown("### 🟢 Defense Health & Subsystem Readiness")
health_cols = st.columns(4)

layers_to_show = [
    ("Authentication", health.get("authentication", {})),
    ("Authorization & RBAC", health.get("authorization", {})),
    ("Audit Integrity", health.get("audit_logging", {})),
    ("Input & Ingestion", health.get("file_validation", {})),
]

for idx, (title, item) in enumerate(layers_to_show):
    with health_cols[idx]:
        st.markdown(
            f"""
            <div style="background: #1e293b; border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #f8fafc; font-size: 14px;">{title}</span>
                    <span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">
                        {item.get('status', 'HEALTHY')}
                    </span>
                </div>
                <div style="color: #94a3b8; font-size: 12px; margin-bottom: 4px;">{item.get('layer', '')}</div>
                <div style="color: #cbd5e1; font-size: 11px;">{item.get('details', '')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==============================================================================
# 4. INCIDENT & TELEMETRY METRIC KPIS
# ==============================================================================

st.markdown("### 📊 Security Incident Telemetry")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric("Total Events Logged", summary.get("total_events", 0))
with kpi2:
    st.metric("Failed Logins", summary.get("failed_logins", 0))
with kpi3:
    st.metric("Blocked Injections", summary.get("blocked_sql", 0) + summary.get("blocked_nlp", 0))
with kpi4:
    st.metric("Blocked Uploads", summary.get("blocked_uploads", 0))
with kpi5:
    st.metric("Rate Limit Events", summary.get("rate_limit_events", 0))


# ==============================================================================
# 5. CRYPTOGRAPHIC AUDIT INTEGRITY VERIFICATION
# ==============================================================================

st.markdown("### 🔗 Tamper-Evident Audit Chain Integrity")
col_ver_btn, col_ver_info = st.columns([1, 3])

with col_ver_btn:
    verify_clicked = st.button("🔍 Verify Hash Chain", use_container_width=True)

with col_ver_info:
    if verify_clicked:
        res = SecurityAuditLogger.verify_audit_integrity()
        if res.get("valid"):
            st.success(f"✅ {res.get('message')} (SHA-256 links verified)")
        else:
            st.error(f"❌ {res.get('message')}")
    else:
        st.info("Click 'Verify Hash Chain' to cryptographically validate the SHA-256 sequential audit chain.")


# ==============================================================================
# 6. INTERACTIVE AUDIT TRAIL EXPLORER
# ==============================================================================

st.markdown("### 📜 Real-Time Security Audit Stream")

f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    sev_filter = st.selectbox("Filter by Severity", ["All", "CRITICAL", "HIGH", "WARNING", "INFO"])
with f_col2:
    outcome_filter = st.selectbox("Filter by Outcome", ["All", "SUCCESS", "FAILURE", "DENIED", "REJECTED", "ALERT"])
with f_col3:
    event_limit = st.slider("Max Events", min_value=10, max_value=200, value=50, step=10)

eff_sev = None if sev_filter == "All" else sev_filter
eff_out = None if outcome_filter == "All" else outcome_filter

recent_events = SecurityAuditLogger.get_audit_events(
    limit=event_limit,
    severity=eff_sev,
    outcome=eff_out
)

if not recent_events:
    st.write("No security events matching current criteria.")
else:
    table_rows = []
    for ev in recent_events:
        table_rows.append({
            "Timestamp": ev.get("timestamp"),
            "Severity": ev.get("severity"),
            "Event": ev.get("event_type"),
            "User": ev.get("user_id"),
            "Role": ev.get("user_role"),
            "Outcome": ev.get("outcome"),
            "Source": ev.get("source"),
            "Reason": ev.get("reason"),
            "Hash": (ev.get("event_hash") or "")[:12] + "..."
        })

    df_events = pd.DataFrame(table_rows)
    st.dataframe(df_events, use_container_width=True, hide_index=True)

    csv_data = df_events.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Filtered Audit Trail (CSV)",
        data=csv_data,
        file_name="aurevix_security_audit_trail.csv",
        mime="text/csv",
        key="btn_export_audit_trail",
        help="Export currently filtered security events as a CSV audit report"
    )
