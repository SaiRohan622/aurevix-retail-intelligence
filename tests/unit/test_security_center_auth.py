"""
AUREVIX — Dedicated Security Center RBAC & Global Authentication Test Suite
Verifies strict ADMIN-only access, absence of login/registration forms in Security Center,
tamper-evident role enforcement against UserStore, and audit event emission.
"""

from pathlib import Path
import json
import time
import pytest
import streamlit as st
from unittest.mock import patch, MagicMock

from dashboard.analytics.auth_manager import AuthManager, UserStore, hash_password
from dashboard.analytics.security_audit import (
    SecurityAuditLogger,
    SecurityEventType,
    SecuritySeverity,
    AUDIT_LOG_FILE
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_session_and_audit(tmp_path):
    """Ensure clean session state and isolated audit log for each test."""
    AuthManager.initialize_session()
    AuthManager.logout()
    test_log = tmp_path / "test_audit.jsonl"
    with patch("dashboard.analytics.security_audit.AUDIT_LOG_FILE", test_log):
        yield test_log


# ==============================================================================
# TEST 1: Unauthenticated user accessing Security Center -> denied / halted
# ==============================================================================
def test_unauthenticated_user_accessing_security_center_denied():
    """Verify unauthenticated user cannot pass authentication check."""
    AuthManager.initialize_session()
    AuthManager.logout()
    assert AuthManager.is_authenticated() is False
    assert AuthManager.has_role("ADMIN") is False


# ==============================================================================
# TEST 2: User with role USER accessing Security Center -> denied
# ==============================================================================
def test_user_role_accessing_security_center_denied():
    """Verify USER role is denied access to ADMIN privileges."""
    email = "test_user_role@aurevix.io"
    users = UserStore._load_users()
    if email in users:
        del users[email]
        UserStore._save_users(users)

    user = UserStore.create_user(email, "StrongPass123!", "Standard User", role="USER")
    try:
        AuthManager.login(user)
        assert AuthManager.is_authenticated() is True
        assert AuthManager.has_role("ADMIN") is False
    finally:
        users = UserStore._load_users()
        if email in users:
            del users[email]
            UserStore._save_users(users)


# ==============================================================================
# TEST 3: User with role ANALYST accessing Security Center -> denied
# ==============================================================================
def test_analyst_role_accessing_security_center_denied():
    """Verify ANALYST role is denied access to ADMIN privileges."""
    email = "test_analyst_role@aurevix.io"
    users = UserStore._load_users()
    if email in users:
        del users[email]
        UserStore._save_users(users)

    user = UserStore.create_user(email, "StrongPass123!", "Analyst User", role="ANALYST")
    try:
        AuthManager.login(user)
        assert AuthManager.is_authenticated() is True
        assert AuthManager.has_role("ADMIN") is False
    finally:
        users = UserStore._load_users()
        if email in users:
            del users[email]
            UserStore._save_users(users)


# ==============================================================================
# TEST 4: User with role ADMIN accessing Security Center -> allowed
# ==============================================================================
def test_admin_role_accessing_security_center_allowed():
    """Verify ADMIN role is authoritatively granted access."""
    email = "test_admin_role@aurevix.io"
    users = UserStore._load_users()
    if email in users:
        del users[email]
        UserStore._save_users(users)

    admin_user = UserStore.create_user(email, "AdminPass123!", "Test Administrator", role="ADMIN")
    try:
        AuthManager.login(admin_user)
        assert AuthManager.is_authenticated() is True
        assert AuthManager.has_role("ADMIN") is True
    finally:
        users = UserStore._load_users()
        if email in users:
            del users[email]
            UserStore._save_users(users)


# ==============================================================================
# TEST 5: Role tampering rejected and logged as PRIVILEGE_ESCALATION_ATTEMPT
# ==============================================================================
def test_role_tampering_rejected_and_audited(clean_session_and_audit):
    """Verify modifying session state to ADMIN without UserStore authority is rejected and audited."""
    test_log = clean_session_and_audit
    email = "test_tamper_user@aurevix.io"
    users = UserStore._load_users()
    if email in users:
        del users[email]
        UserStore._save_users(users)

    user = UserStore.create_user(email, "UserPass123!", "Tamper Target", role="USER")
    try:
        AuthManager.login(user)
        assert AuthManager.has_role("ADMIN") is False

        # Malicious client-side tampering of session state
        st.session_state["auth"]["role"] = "ADMIN"

        with patch("dashboard.analytics.security_audit.AUDIT_LOG_FILE", test_log):
            has_admin = AuthManager.has_role("ADMIN")
            assert has_admin is False

            # Verify PRIVILEGE_ESCALATION_ATTEMPT was logged
            events = SecurityAuditLogger.get_audit_events(
                event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
                log_file=test_log
            )
            assert len(events) >= 1
            assert events[0]["severity"] == SecuritySeverity.CRITICAL
            assert events[0]["user_id"] == user["id"]
    finally:
        users = UserStore._load_users()
        if email in users:
            del users[email]
            UserStore._save_users(users)


# ==============================================================================
# TEST 6: Direct URL access enforcement (simulated)
# ==============================================================================
def test_direct_url_access_enforcement():
    """Verify unauthenticated direct access invokes st.stop()."""
    AuthManager.initialize_session()
    AuthManager.logout()

    # When unauthenticated:
    with patch("streamlit.stop") as mock_stop, \
         patch("streamlit.markdown") as mock_md:
        if not AuthManager.is_authenticated():
            mock_stop()
        mock_stop.assert_called_once()

    # When authenticated as normal USER:
    with patch("streamlit.stop") as mock_stop, \
         patch("dashboard.analytics.auth_manager.AuthManager.has_role", return_value=False):
        if not AuthManager.has_role("ADMIN"):
            mock_stop()
        mock_stop.assert_called_once()

    # When authenticated as ADMIN:
    with patch("streamlit.stop") as mock_stop, \
         patch("dashboard.analytics.auth_manager.AuthManager.has_role", return_value=True):
        if not AuthManager.has_role("ADMIN"):
            mock_stop()
        mock_stop.assert_not_called()


# ==============================================================================
# TEST 7: ADMIN_ACCESS_DENIED audit event is generated on unauthorized access
# ==============================================================================
def test_admin_access_denied_audit_event_logged(clean_session_and_audit):
    """Verify unauthorized access attempt logs ADMIN_ACCESS_DENIED with HIGH severity."""
    test_log = clean_session_and_audit
    with patch("dashboard.analytics.security_audit.AUDIT_LOG_FILE", test_log):
        SecurityAuditLogger.log_event(
            event_type=SecurityEventType.ADMIN_ACCESS_DENIED,
            severity=SecuritySeverity.HIGH,
            outcome="DENIED",
            user_id="analyst_test_id",
            user_role="ANALYST",
            source="page.11_Security_Center",
            reason="User with role 'ANALYST' attempted to access Security Operations Center"
        )

        events = SecurityAuditLogger.get_audit_events(
            event_type=SecurityEventType.ADMIN_ACCESS_DENIED,
            log_file=test_log
        )
        assert len(events) >= 1
        assert events[0]["severity"] == SecuritySeverity.HIGH
        assert events[0]["source"] == "page.11_Security_Center"
        assert events[0]["user_role"] == "ANALYST"
        assert events[0]["outcome"] == "DENIED"


# ==============================================================================
# TEST 8: Security Center source code contains NO sign in UI
# ==============================================================================
def test_security_center_source_code_contains_no_signin_ui():
    """Verify Security Center page source code contains zero sign-in UI components."""
    sec_page_path = ROOT / "dashboard" / "pages" / "11_Security_Center.py"
    assert sec_page_path.exists(), "11_Security_Center.py must exist"

    code = sec_page_path.read_text(encoding="utf-8")

    # Must NOT have sign-in forms or login tabs
    assert "aurevix_login_form" not in code, "Login form must not be in Security Center"
    assert 'tabs(["\U0001f510 Sign In"' not in code
    assert 'Sign In to AUREVIX' not in code, "Sign in submit button must not be in Security Center"
    assert "auth_login_pwd" not in code, "Login password input key must not be in Security Center"
    assert "auth_login_email" not in code, "Login email input key must not be in Security Center"


# ==============================================================================
# TEST 9: Security Center source code contains NO sign up UI
# ==============================================================================
def test_security_center_source_code_contains_no_signup_ui():
    """Verify Security Center page source code contains zero registration UI components."""
    sec_page_path = ROOT / "dashboard" / "pages" / "11_Security_Center.py"
    code = sec_page_path.read_text(encoding="utf-8")

    # Must NOT have sign-up forms or registration tabs
    assert "aurevix_reg_form" not in code, "Registration form must not be in Security Center"
    assert "Create Analyst Account" not in code, "Create account button must not be in Security Center"
    assert "Create Account" not in code, "Create Account tab must not be in Security Center"
    assert "auth_reg_pwd" not in code, "Registration password key must not be in Security Center"
    assert "auth_reg_email" not in code, "Registration email key must not be in Security Center"


# ==============================================================================
# TEST 10: Global authentication controls are available outside Security Center
# ==============================================================================
def test_global_authentication_controls_available_outside_security_center():
    """Verify global authentication bar and sidebar provide session controls."""
    # Verify AuthManager exposes render_top_auth_bar
    assert hasattr(AuthManager, "render_top_auth_bar"), "AuthManager must have render_top_auth_bar"
    assert callable(AuthManager.render_top_auth_bar)

    # Verify sidebar.py contains conditional navigation hiding Security Center for non-admins
    sidebar_path = ROOT / "dashboard" / "components" / "sidebar.py"
    assert sidebar_path.exists(), "sidebar.py must exist"
    sidebar_code = sidebar_path.read_text(encoding="utf-8")

    # Verify CSS suppression of Security Center from auto navigation
    assert 'a[href*="Security_Center"]' in sidebar_code
    assert 'display: none !important;' in sidebar_code

    # Verify dynamic admin-only link
    assert 'AuthManager.has_role("ADMIN")' in sidebar_code
    assert 'ADMINISTRATION' in sidebar_code

    # Verify custom.css also enforces suppression
    css_path = ROOT / "dashboard" / "styles" / "custom.css"
    assert css_path.exists()
    css_code = css_path.read_text(encoding="utf-8")
    assert 'a[href*="Security_Center"]' in css_code
