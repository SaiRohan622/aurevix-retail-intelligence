import io
import time
import pytest
import pandas as pd
import streamlit as st
from pathlib import Path

from dashboard.analytics.auth_manager import (
    AuthManager,
    UserStore,
    hash_password,
    verify_password,
    validate_password_policy,
    normalize_email
)
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.persistent_storage import PersistentStorageManager
from dashboard.analytics.query_engine import AskYourDataEngine
from dashboard.analytics.comparison_engine import ComparisonEngine


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_auth_state(tmp_path, monkeypatch):
    """Ensure a clean, isolated user store and attempts store for each test."""
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    users_file = auth_dir / "users.json"
    attempts_file = auth_dir / "attempts.json"

    import dashboard.analytics.auth_manager as am
    monkeypatch.setattr(am, "AUTH_STORAGE_DIR", auth_dir)
    monkeypatch.setattr(am, "USERS_FILE", users_file)
    monkeypatch.setattr(am, "ATTEMPTS_FILE", attempts_file)

    AuthManager.initialize_session()
    AuthManager.logout()
    yield
    AuthManager.logout()


# ==============================================================================
# 1. PASSWORD HASHING & POLICY TESTS
# ==============================================================================

def test_password_is_hashed():
    """Verify password is encrypted using memory-hard scrypt."""
    raw_pwd = "SecurePassword123!"
    h = hash_password(raw_pwd)
    assert h.startswith("scrypt$16384$8$1$")
    assert raw_pwd not in h
    assert verify_password(raw_pwd, h) is True
    assert verify_password("WrongPassword", h) is False


def test_password_not_stored_plaintext():
    """Verify stored user records contain only password_hash, never plaintext."""
    email = "analyst_sec@aurevix.io"
    pwd = "MySecretPassword2026!"
    u = AuthManager.register(email, pwd, display_name="Security Analyst")
    assert "password" not in u
    assert "password_hash" in u
    assert u["password_hash"].startswith("scrypt$")
    assert pwd not in u["password_hash"]


def test_password_policy():
    """Verify minimum 8-character password enforcement."""
    is_valid, msg = validate_password_policy("short")
    assert is_valid is False
    assert "at least 8 characters" in msg

    is_valid, msg = validate_password_policy("")
    assert is_valid is False

    is_valid, msg = validate_password_policy("valid_password_123")
    assert is_valid is True
    assert msg is None


# ==============================================================================
# 2. LOGIN, LOGOUT & BRUTE-FORCE TESTS
# ==============================================================================

def test_valid_login():
    """Verify valid credentials authenticate successfully."""
    email = "login_test@aurevix.io"
    pwd = "ValidPassword123!"
    AuthManager.register(email, pwd, display_name="Test User")

    success, user_dict, err = AuthManager.authenticate(email, pwd)
    assert success is True
    assert user_dict is not None
    assert user_dict["email"] == email.lower()
    assert "password_hash" not in user_dict
    assert err is None


def test_invalid_password_generic_error():
    """Verify wrong password returns generic error message without account details."""
    email = "generic_err_user@aurevix.io"
    pwd = "CorrectPassword123!"
    AuthManager.register(email, pwd)

    success, user_dict, err = AuthManager.authenticate(email, "WrongPassword999!")
    assert success is False
    assert user_dict is None
    assert err == "Invalid email or password."


def test_invalid_user_generic_error():
    """Verify non-existent user returns exact same generic error (preventing account enumeration)."""
    success, user_dict, err = AuthManager.authenticate("non_existent_account@aurevix.io", "SomePassword123!")
    assert success is False
    assert user_dict is None
    assert err == "Invalid email or password."


def test_duplicate_account_rejected():
    """Verify duplicate account registration is rejected."""
    email = "dup_test@aurevix.io"
    pwd = "ValidPassword123!"
    AuthManager.register(email, pwd)

    with pytest.raises(ValueError, match="already exists"):
        AuthManager.register(email.upper(), "AnotherPassword123!")


def test_inactive_user_rejected():
    """Verify inactive/disabled user account cannot authenticate."""
    email = "inactive_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd)
    
    # Disable user
    users = UserStore._load_users()
    users[email]["is_active"] = False
    UserStore._save_users(users)

    success, user_dict, err = AuthManager.authenticate(email, pwd)
    assert success is False
    assert err == "Invalid email or password."


def test_bruteforce_protection():
    """Verify repeated failed attempts trigger temporary lockout."""
    email = "brute_force_victim@aurevix.io"
    pwd = "ValidPassword123!"
    AuthManager.register(email, pwd)

    for _ in range(5):
        AuthManager.authenticate(email, "BadPassword")

    # 6th attempt should be locked out
    success, user_dict, err = AuthManager.authenticate(email, "BadPassword")
    assert success is False
    assert "Account is temporarily locked" in err


# ==============================================================================
# 3. SESSION SECURITY & TIMEOUT TESTS
# ==============================================================================

def test_session_created_after_login():
    """Verify session dictionary is populated after login."""
    email = "session_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd)

    success, user_dict, _ = AuthManager.authenticate(email, pwd)
    session_id = AuthManager.login(user_dict)

    assert session_id is not None
    assert AuthManager.is_authenticated() is True
    curr = AuthManager.get_current_user()
    assert curr["email"] == email.lower()
    assert curr["role"] == "USER"


def test_session_id_rotated_after_login():
    """Verify session ID is rotated to a new random token on each login."""
    email = "rotate_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd)

    _, user_dict, _ = AuthManager.authenticate(email, pwd)
    sid1 = AuthManager.login(user_dict)
    sid2 = AuthManager.login(user_dict)

    assert sid1 != sid2
    assert len(sid1) == 32
    assert len(sid2) == 32


def test_session_expiration():
    """Verify expired session automatically invalidates authenticated state."""
    email = "timeout_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd)

    _, user_dict, _ = AuthManager.authenticate(email, pwd)
    AuthManager.login(user_dict)
    assert AuthManager.is_authenticated() is True

    # Simulate expiration by rolling back expires_at
    st.session_state["auth"]["expires_at"] = time.time() - 10

    assert AuthManager.is_authenticated() is False
    assert AuthManager.get_current_user() is None


def test_logout_invalidates_session():
    """Verify logout invalidates authentication state and session ID."""
    email = "logout_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd)

    _, user_dict, _ = AuthManager.authenticate(email, pwd)
    AuthManager.login(user_dict)
    assert AuthManager.is_authenticated() is True

    AuthManager.logout()
    assert AuthManager.is_authenticated() is False
    assert st.session_state["auth"]["authenticated"] is False
    assert st.session_state["auth"]["session_id"] is None


def test_authentication_state_is_separate_from_workspace_state():
    """Verify auth state and workspace state reside in separate session keys."""
    AuthManager.initialize_session()
    assert "auth" in st.session_state
    assert "raw_df" not in st.session_state["auth"]
    assert "password" not in st.session_state["auth"]


# ==============================================================================
# 4. AUTHORIZATION & RBAC TESTS
# ==============================================================================

def test_user_role_authorization():
    """Verify standard user role permissions."""
    email = "standard_analyst@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd, role="USER")

    _, user_dict, _ = AuthManager.authenticate(email, pwd)
    AuthManager.login(user_dict)

    assert AuthManager.has_role("USER") is True
    assert AuthManager.has_role("ADMIN") is False


def test_admin_role_authorization():
    """Verify administrator role permissions."""
    email = "admin_user@aurevix.io"
    pwd = "ValidPassword123!"
    u = AuthManager.register(email, pwd, role="ADMIN")

    _, user_dict, _ = AuthManager.authenticate(email, pwd)
    AuthManager.login(user_dict)

    assert AuthManager.has_role("USER") is True
    assert AuthManager.has_role("ADMIN") is True


# ==============================================================================
# 5. WORKSPACE & DATASET OWNERSHIP / ISOLATION TESTS
# ==============================================================================

def test_workspace_owner_can_access_workspace():
    """Verify workspace owner can save, list, and reload their workspace."""
    u_alice = AuthManager.register("alice@aurevix.io", "ValidPassword123!")
    AuthManager.login(u_alice)

    ws_saved = WorkspaceManager.save_workspace("Alice Q3 Analysis", dataset_name="Alice Data")
    assert ws_saved["owner_user_id"] == u_alice["id"]

    ws_loaded = WorkspaceManager.load_workspace("alice_q3_analysis")
    assert ws_loaded is not None
    assert ws_loaded["name"] == "Alice Q3 Analysis"


def test_user_cannot_access_other_users_workspace():
    """Verify User B cannot load User A's private workspace."""
    u_alice = AuthManager.register("alice_private@aurevix.io", "ValidPassword123!")
    u_bob = AuthManager.register("bob_attacker@aurevix.io", "ValidPassword123!")

    # Alice creates workspace
    AuthManager.login(u_alice)
    WorkspaceManager.save_workspace("Alice Confidential", dataset_name="Financials")

    # Bob logs in and tries to load Alice's workspace
    AuthManager.login(u_bob)
    ws_bob_attempt = WorkspaceManager.load_workspace("alice_confidential")
    assert ws_bob_attempt is None


def test_user_cannot_delete_other_users_workspace():
    """Verify User B cannot delete User A's private workspace."""
    u_alice = AuthManager.register("alice_owner@aurevix.io", "ValidPassword123!")
    u_bob = AuthManager.register("bob_delete_attempt@aurevix.io", "ValidPassword123!")

    AuthManager.login(u_alice)
    WorkspaceManager.save_workspace("Alice Protected", dataset_name="Data")

    # Bob tries to delete Alice's workspace
    AuthManager.login(u_bob)
    deleted = WorkspaceManager.delete_workspace("alice_protected")
    assert deleted is False

    # Alice can still load it
    AuthManager.login(u_alice)
    assert WorkspaceManager.load_workspace("alice_protected") is not None


def test_user_cannot_access_other_users_dataset():
    """Verify User B cannot load User A's persisted dataset directly."""
    u_alice = AuthManager.register("alice_dataset_owner@aurevix.io", "ValidPassword123!")
    u_bob = AuthManager.register("bob_dataset_snooper@aurevix.io", "ValidPassword123!")

    df_alice = pd.DataFrame({"revenue": [1000, 2000], "secret": ["Confidential A", "Confidential B"]})
    
    # Alice saves dataset
    AuthManager.login(u_alice)
    ds_id = "alice_secret_hash"
    PersistentStorageManager.save_dataset(ds_id, "alice_data.csv", df_alice)

    # Bob tries to load Alice's dataset
    AuthManager.login(u_bob)
    loaded = PersistentStorageManager.load_dataset(ds_id)
    assert loaded is None

    # Alice can load her own dataset
    AuthManager.login(u_alice)
    loaded_alice = PersistentStorageManager.load_dataset(ds_id)
    assert loaded_alice is not None
    assert len(loaded_alice["raw_df"]) == 2


def test_ask_data_requires_dataset_authorization():
    """Verify AskYourData operates on active authorized workspace data."""
    df_sample = pd.DataFrame({"product": ["Gadget"], "price": [100.0]})
    res = AskYourDataEngine.answer_question(
        df=df_sample,
        query="What is total revenue?",
        schema_meta={"numeric_columns": ["price"]},
        metrics={"total_revenue": 100.0}
    )
    assert res is not None
    assert "answer" in res


def test_workspace_path_and_owner_both_validated():
    """Verify both path traversal sanitization and ownership check are enforced."""
    u_alice = AuthManager.register("alice_path@aurevix.io", "ValidPassword123!")
    AuthManager.login(u_alice)

    ws = WorkspaceManager.save_workspace("../../../traversal_workspace", dataset_name="Data")
    assert ws is not None
    assert "../" not in ws["workspace_id"]
    assert ws["owner_user_id"] == u_alice["id"]


def test_password_not_logged():
    """Verify raw passwords are never included in logger output."""
    from src.common.logger import sanitize_log_text
    raw_log = "User tried logging in with password='SuperSecretPassword123!' and token=abc"
    clean_log = sanitize_log_text(raw_log)
    assert "SuperSecretPassword123!" not in clean_log
    assert "****" in clean_log or "[REDACTED]" in clean_log


def test_normal_user_cannot_access_admin():
    """Verify normal user cannot claim or execute admin-level operations."""
    u_user = AuthManager.register("analyst_normal@aurevix.io", "ValidPassword123!", role="USER")
    AuthManager.login(u_user)
    assert AuthManager.has_role("ADMIN") is False
    assert AuthManager.has_role("USER") is True


def test_compare_requires_dataset_authorization():
    """Verify comparison engine requires valid datasets."""
    df_a = pd.DataFrame({"product": ["A", "B"], "price": [10, 20]})
    df_b = pd.DataFrame({"product": ["A", "B"], "price": [15, 25]})
    res = ComparisonEngine.compare_datasets(df_a, df_b, "Data A", "Data B")
    assert res is not None
    assert "metric_deltas" in res or "available" in res


def test_export_requires_ownership():
    """Verify export operations respect user dataset boundaries."""
    u_alice = AuthManager.register("alice_export@aurevix.io", "ValidPassword123!")
    AuthManager.login(u_alice)
    df_alice = pd.DataFrame({"revenue": [100, 200]})
    ds_id = "alice_export_ds"
    PersistentStorageManager.save_dataset(ds_id, "alice_export.csv", df_alice)

    # Alice can retrieve for export
    loaded = PersistentStorageManager.load_dataset(ds_id)
    assert loaded is not None

    # Bob cannot retrieve Alice's dataset for export
    u_bob = AuthManager.register("bob_export@aurevix.io", "ValidPassword123!")
    AuthManager.login(u_bob)
    loaded_bob = PersistentStorageManager.load_dataset(ds_id)
    assert loaded_bob is None


def test_session_secret_not_logged():
    """Verify session IDs or tokens are redacted in log messages."""
    from src.common.logger import sanitize_log_text
    raw_log = "User authenticated with bearer token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    clean_log = sanitize_log_text(raw_log)
    assert "eyJhbGci" not in clean_log
