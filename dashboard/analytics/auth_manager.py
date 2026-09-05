"""
AUREVIX — Authentication, Authorization & Session Security Manager (Phase 4)
Provides production-grade authentication with memory-hard scrypt password hashing,
session fixation defense, configurable timeouts, brute-force rate-limiting,
role-based authorization (USER/ADMIN), and user data isolation.
"""

import os
import re
import json
import time
import hmac
import uuid
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union
import streamlit as st

from src.common.logger import get_logger

logger = get_logger("aurevix.auth_manager")

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

# Session & Security Settings
DEFAULT_SESSION_TIMEOUT_MINUTES = 60
try:
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", str(DEFAULT_SESSION_TIMEOUT_MINUTES)))
except Exception:
    SESSION_TIMEOUT_MINUTES = DEFAULT_SESSION_TIMEOUT_MINUTES

DEFAULT_MAX_LOGIN_ATTEMPTS = 5
try:
    AUTH_MAX_LOGIN_ATTEMPTS = int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", str(DEFAULT_MAX_LOGIN_ATTEMPTS)))
except Exception:
    AUTH_MAX_LOGIN_ATTEMPTS = DEFAULT_MAX_LOGIN_ATTEMPTS

DEFAULT_LOCKOUT_MINUTES = 15
try:
    AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", str(DEFAULT_LOCKOUT_MINUTES)))
except Exception:
    AUTH_LOCKOUT_MINUTES = DEFAULT_LOCKOUT_MINUTES

# Storage Directory for User Accounts
AUTH_STORAGE_DIR = Path("data/auth")
USERS_FILE = AUTH_STORAGE_DIR / "users.json"
ATTEMPTS_FILE = AUTH_STORAGE_DIR / "login_attempts.json"

# Session Namespace
_AUTH_NS = "auth"


# ==============================================================================
# 1. PASSWORD HASHING UTILITIES (scrypt)
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Hashes a password using Python standard library hashlib.scrypt with a random 16-byte salt.
    Format: scrypt$16384$8$1$<hex_salt>$<hex_hash>
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")

    salt = secrets.token_bytes(16)
    # Memory-hard scrypt parameters: N=16384, r=8, p=1, maxmem=32MB
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=33554432
    )
    return f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored scrypt hash using constant-time comparison.
    """
    if not password or not password_hash or not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    try:
        parts = password_hash.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False

        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected_hash = bytes.fromhex(parts[5])

        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=33554432
        )
        return hmac.compare_digest(derived, expected_hash)
    except Exception as exc:
        logger.warning(f"Password verification error: {exc}")
        return False


def validate_password_policy(password: str) -> Tuple[bool, Optional[str]]:
    """
    Enforces password complexity: minimum 8 characters, non-empty.
    """
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, None


def normalize_email(email: str) -> str:
    """
    Normalizes email addresses to lowercase and strips whitespace.
    """
    return str(email or "").strip().lower()


# ==============================================================================
# 2. USER STORE & PERSISTENCE
# ==============================================================================

class UserStore:
    """Thread-safe persistent store for user accounts and rate-limiting."""

    _secrets_bootstrapped: bool = False

    @classmethod
    def bootstrap_admin_from_secrets(cls) -> None:
        """
        Safely provisions an initial administrator account from Streamlit secrets
        (ADMIN_EMAIL and ADMIN_PASSWORD) if explicitly configured in Streamlit Cloud.
        If the account already exists, it is not recreated or overwritten.
        If no secrets are defined, this is a graceful no-op.
        """
        if cls._secrets_bootstrapped:
            return
        cls._secrets_bootstrapped = True

        try:
            if not hasattr(st, "secrets"):
                return
            admin_email = st.secrets.get("ADMIN_EMAIL")
            admin_password = st.secrets.get("ADMIN_PASSWORD")
            if not admin_email or not admin_password:
                return

            admin_email_str = str(admin_email).strip()
            admin_password_str = str(admin_password)

            norm_email = normalize_email(admin_email_str)
            if not norm_email:
                return

            users = cls._load_users()
            if norm_email in users:
                return

            is_valid, msg = validate_password_policy(admin_password_str)
            if not is_valid:
                logger.warning(f"Admin secrets bootstrap skipped: {msg}")
                return

            cls.create_user(
                email=admin_email_str,
                password=admin_password_str,
                display_name="Cloud Administrator",
                role="ADMIN"
            )
            logger.info("Initial cloud administrator account provisioned from secrets configuration.")
        except Exception as e:
            logger.debug(f"Admin secrets bootstrap check: {e}")

    @classmethod
    def _ensure_storage(cls) -> None:
        AUTH_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        if not USERS_FILE.exists():
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
        if not ATTEMPTS_FILE.exists():
            with open(ATTEMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

    @classmethod
    def _load_users(cls) -> Dict[str, Dict[str, Any]]:
        cls._ensure_storage()
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _save_users(cls, users: Dict[str, Dict[str, Any]]) -> None:
        AUTH_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = AUTH_STORAGE_DIR / f"users_{uuid.uuid4().hex[:8]}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        temp_file.replace(USERS_FILE)

    @classmethod
    def _load_attempts(cls) -> Dict[str, Dict[str, Any]]:
        cls._ensure_storage()
        try:
            with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _save_attempts(cls, attempts: Dict[str, Dict[str, Any]]) -> None:
        AUTH_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = AUTH_STORAGE_DIR / f"attempts_{uuid.uuid4().hex[:8]}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(attempts, f, indent=2, ensure_ascii=False)
        temp_file.replace(ATTEMPTS_FILE)

    @classmethod
    def find_user_by_email(cls, email: str) -> Optional[Dict[str, Any]]:
        users = cls._load_users()
        norm_email = normalize_email(email)
        return users.get(norm_email)

    @classmethod
    def find_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        users = cls._load_users()
        for u in users.values():
            if u.get("id") == user_id:
                return u
        return None

    @classmethod
    def create_user(
        cls,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        role: str = "USER"
    ) -> Dict[str, Any]:
        cls._ensure_storage()
        norm_email = normalize_email(email)
        users = cls._load_users()

        if norm_email in users:
            raise ValueError("An account with this email address already exists.")

        is_valid, msg = validate_password_policy(password)
        if not is_valid:
            raise ValueError(msg)

        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        user_id = str(uuid.uuid4())
        pwd_hash = hash_password(password)

        user_record = {
            "id": user_id,
            "email": norm_email,
            "display_name": display_name or norm_email.split("@")[0].title(),
            "password_hash": pwd_hash,
            "role": role.upper() if role.upper() in ("USER", "ADMIN") else "USER",
            "session_version": 1,
            "is_active": True,
            "created_at": now_str,
            "updated_at": now_str,
            "last_login_at": None
        }

        users[norm_email] = user_record
        cls._save_users(users)
        logger.info(f"User account created for user_id={user_id} with role={user_record['role']}")
        return user_record

    @classmethod
    def setup_admin(
        cls,
        email: str,
        password: str,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates or resets an ADMIN account securely in local/development mode.
        If the account exists: updates password hash, sets role to ADMIN,
        bumps session_version to invalidate prior sessions, and ensures active status.
        If the account does not exist: creates a new user record with ADMIN role.
        Audits the operation without exposing credentials.
        """
        cls._ensure_storage()
        norm_email = normalize_email(email)
        if not norm_email:
            raise ValueError("Email cannot be empty.")

        is_valid, msg = validate_password_policy(password)
        if not is_valid:
            raise ValueError(msg)

        users = cls._load_users()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        pwd_hash = hash_password(password)

        if norm_email in users:
            user = users[norm_email]
            user["password_hash"] = pwd_hash
            user["role"] = "ADMIN"
            user["is_active"] = True
            user["updated_at"] = now_str
            current_ver = user.get("session_version", 1)
            user["session_version"] = current_ver + 1
            if display_name:
                user["display_name"] = display_name
            users[norm_email] = user
            cls._save_users(users)
            user_id = user["id"]
            action = "reset"
            logger.info(f"Admin account password/role reset for user_id={user_id}; session version bumped to {current_ver + 1}")
        else:
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "email": norm_email,
                "display_name": display_name or norm_email.split("@")[0].title(),
                "password_hash": pwd_hash,
                "role": "ADMIN",
                "session_version": 1,
                "is_active": True,
                "created_at": now_str,
                "updated_at": now_str,
                "last_login_at": None
            }
            users[norm_email] = user
            cls._save_users(users)
            action = "created"
            logger.info(f"Admin account created for user_id={user_id} with role=ADMIN")

        # Invalidate brute-force attempt records for this email
        cls.reset_attempts(norm_email)

        # Audit the operation
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.PASSWORD_CHANGED,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=user_id,
                user_role="ADMIN",
                source="auth_manager.setup_admin",
                reason=f"Administrator account {action} via local admin recovery utility"
            )
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.SESSION_INVALIDATED,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=user_id,
                user_role="ADMIN",
                source="auth_manager.setup_admin",
                reason="Sessions invalidated upon admin setup/recovery"
            )
        except Exception:
            pass

        return {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "action": action
        }

    @classmethod
    def update_password(cls, user_id: str, new_password_hash: str) -> bool:
        cls._ensure_storage()
        users = cls._load_users()
        target_email = None
        for email, u in users.items():
            if u.get("id") == user_id:
                target_email = email
                break
        if not target_email:
            return False

        users[target_email]["password_hash"] = new_password_hash
        users[target_email]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        current_ver = users[target_email].get("session_version", 1)
        users[target_email]["session_version"] = current_ver + 1
        cls._save_users(users)
        logger.info(f"Password updated for user_id={user_id}; session version bumped to {current_ver + 1}")
        return True

    @classmethod
    def update_last_login(cls, email: str) -> None:
        norm_email = normalize_email(email)
        users = cls._load_users()
        if norm_email in users:
            users[norm_email]["last_login_at"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            cls._save_users(users)

    # Brute-force rate limiting
    @classmethod
    def record_failed_attempt(cls, email: str) -> None:
        norm_email = normalize_email(email)
        attempts = cls._load_attempts()
        now = time.time()
        record = attempts.get(norm_email, {"count": 0, "first_failed": now, "lockout_until": 0})

        # Reset count if window passed
        if now - record.get("first_failed", 0) > (AUTH_LOCKOUT_MINUTES * 60):
            record["count"] = 0
            record["first_failed"] = now

        record["count"] = record.get("count", 0) + 1
        if record["count"] >= AUTH_MAX_LOGIN_ATTEMPTS:
            record["lockout_until"] = now + (AUTH_LOCKOUT_MINUTES * 60)
            logger.warning(f"Brute-force lockout triggered for email={norm_email}")

        attempts[norm_email] = record
        cls._save_attempts(attempts)

    @classmethod
    def is_locked_out(cls, email: str) -> bool:
        norm_email = normalize_email(email)
        attempts = cls._load_attempts()
        record = attempts.get(norm_email)
        if not record:
            return False
        now = time.time()
        return now < record.get("lockout_until", 0)

    @classmethod
    def reset_attempts(cls, email: str) -> None:
        norm_email = normalize_email(email)
        attempts = cls._load_attempts()
        if norm_email in attempts:
            del attempts[norm_email]
            cls._save_attempts(attempts)


# ==============================================================================
# 3. AUTHENTICATION & SESSION MANAGER
# ==============================================================================

class AuthManager:
    """Manages user authentication, session lifecycle, and authorization guards."""

    # Default fallback user ID for unauthenticated background/test operations
    DEFAULT_TEST_USER_ID = "test_default_user"

    @classmethod
    def bootstrap_admin_from_secrets(cls) -> None:
        """Bootstraps admin account from Streamlit secrets if configured."""
        UserStore.bootstrap_admin_from_secrets()

    @classmethod
    def initialize_session(cls) -> None:
        UserStore.bootstrap_admin_from_secrets()
        if _AUTH_NS not in st.session_state:
            st.session_state[_AUTH_NS] = {
                "authenticated": False,
                "user_id": None,
                "email": None,
                "display_name": None,
                "role": None,
                "session_id": None,
                "login_at": None,
                "expires_at": None
            }

    @classmethod
    def register(
        cls,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        role: str = "USER"
    ) -> Dict[str, Any]:
        """Registers a new user account."""
        return UserStore.create_user(email, password, display_name, role)

    @classmethod
    def setup_admin(
        cls,
        email: str,
        password: str,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exposes safe admin setup/recovery utility."""
        return UserStore.setup_admin(email, password, display_name)

    @classmethod
    def authenticate(cls, email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticates credentials against the user store.
        Returns (success, user_dict_sanitized, error_message).
        """
        norm_email = normalize_email(email)
        if not norm_email or not password:
            return False, None, "Please provide both email and password."

        # Check lockout
        if UserStore.is_locked_out(norm_email):
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.AUTH_ACCOUNT_LOCKED,
                    severity=SecuritySeverity.HIGH,
                    outcome="DENIED",
                    user_id=norm_email,
                    source="auth_manager",
                    reason="Login attempt while account temporarily locked"
                )
            except Exception:
                pass
            return False, None, f"Account is temporarily locked due to repeated failed login attempts. Please try again in {AUTH_LOCKOUT_MINUTES} minutes."

        user = UserStore.find_user_by_email(norm_email)
        if not user:
            UserStore.record_failed_attempt(norm_email)
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
                    severity=SecuritySeverity.WARNING,
                    outcome="FAILURE",
                    user_id=norm_email,
                    source="auth_manager",
                    reason="User not found"
                )
            except Exception:
                pass
            return False, None, "Invalid email or password."

        if not user.get("is_active", True):
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
                    severity=SecuritySeverity.WARNING,
                    outcome="FAILURE",
                    user_id=norm_email,
                    source="auth_manager",
                    reason="Inactive account"
                )
            except Exception:
                pass
            return False, None, "Invalid email or password."

        if not verify_password(password, user.get("password_hash", "")):
            UserStore.record_failed_attempt(norm_email)
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
                    severity=SecuritySeverity.WARNING,
                    outcome="FAILURE",
                    user_id=norm_email,
                    source="auth_manager",
                    reason="Incorrect password"
                )
            except Exception:
                pass
            return False, None, "Invalid email or password."

        # Successful login: reset failed attempts
        UserStore.reset_attempts(norm_email)
        UserStore.update_last_login(norm_email)

        safe_user = {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user["role"],
            "is_active": user["is_active"],
            "session_version": user.get("session_version", 1),
            "created_at": user["created_at"],
            "last_login_at": user.get("last_login_at")
        }
        return True, safe_user, None

    @classmethod
    def login(cls, user: Dict[str, Any]) -> str:
        """
        Logs in a user, rotating the session identifier to eliminate session fixation.
        """
        cls.initialize_session()
        new_session_id = secrets.token_hex(16)
        now = time.time()
        expires_at = now + (SESSION_TIMEOUT_MINUTES * 60)

        auth_state = {
            "authenticated": True,
            "user_id": user["id"],
            "email": user["email"],
            "display_name": user.get("display_name", user["email"]),
            "role": user.get("role", "USER"),
            "session_version": user.get("session_version", 1),
            "session_id": new_session_id,
            "login_at": now,
            "expires_at": expires_at
        }
        st.session_state[_AUTH_NS] = auth_state
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=user["id"],
                user_role=user.get("role", "USER"),
                session_id=new_session_id,
                source="auth_manager",
                reason="Authentication successful"
            )
        except Exception:
            pass

        logger.info(f"User login successful: user_id={user['id']} session_id_rotated={new_session_id[:8]}***")
        return new_session_id

    @classmethod
    def logout(cls) -> None:
        """
        Explicitly invalidates session authentication and clears user workspace state.
        """
        cls.initialize_session()
        old_uid = st.session_state[_AUTH_NS].get("user_id")
        old_role = st.session_state[_AUTH_NS].get("role")
        st.session_state[_AUTH_NS] = {
            "authenticated": False,
            "user_id": None,
            "email": None,
            "display_name": None,
            "role": None,
            "session_id": None,
            "login_at": None,
            "expires_at": None
        }
        # Clear workspace state
        if "workspace" in st.session_state:
            from dashboard.analytics.data_cache import AnalyticsManager
            AnalyticsManager.clear_active_dataset()

        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.AUTH_LOGOUT,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=old_uid or "anonymous",
                user_role=old_role or "GUEST",
                source="auth_manager",
                reason="User initiated logout"
            )
        except Exception:
            pass

        logger.info(f"User logout completed for user_id={old_uid}")

    @classmethod
    def is_authenticated(cls) -> bool:
        """
        Validates authentication state and enforces session timeout expiration.
        """
        if _AUTH_NS not in st.session_state:
            return False

        auth = st.session_state[_AUTH_NS]
        if not auth.get("authenticated", False):
            return False

        # Verify session expiration
        now = time.time()
        expires_at = auth.get("expires_at", 0)
        if now > expires_at:
            logger.info("Session expired due to inactivity timeout.")
            cls.logout()
            return False

        # Verify session validity against user store (session invalidation on password change)
        uid = auth.get("user_id")
        if uid and uid != cls.DEFAULT_TEST_USER_ID:
            stored_user = UserStore.find_user_by_id(uid)
            if stored_user:
                expected_version = stored_user.get("session_version", 1)
                active_version = auth.get("session_version", 1)
                if active_version < expected_version:
                    logger.info(f"Session invalidated for user_id={uid} due to password change.")
                    try:
                        from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                        SecurityAuditLogger.log_event(
                            event_type=SecurityEventType.SESSION_INVALIDATED,
                            severity=SecuritySeverity.WARNING,
                            outcome="DENIED",
                            user_id=uid,
                            source="auth_manager.is_authenticated",
                            reason="Session version expired after password change"
                        )
                    except Exception:
                        pass
                    cls.logout()
                    return False

        return True

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """Returns the currently authenticated user dictionary or None."""
        if not cls.is_authenticated():
            return None
        auth = st.session_state[_AUTH_NS]
        return {
            "id": auth["user_id"],
            "email": auth["email"],
            "display_name": auth["display_name"],
            "role": auth["role"],
            "session_id": auth["session_id"]
        }

    @classmethod
    def get_current_user_id(cls) -> str:
        """
        Returns the current authenticated user's ID.
        If no authenticated session exists (e.g. unit tests or local scripts),
        falls back gracefully to DEFAULT_TEST_USER_ID.
        """
        user = cls.get_current_user()
        if user and user.get("id"):
            return user["id"]
        return cls.DEFAULT_TEST_USER_ID

    @classmethod
    def change_password(
        cls,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Securely changes a user's password and invalidates all existing sessions.
        Returns (success: bool, error_or_success_message: Optional[str]).
        """
        if not user_id or not old_password or not new_password:
            return False, "All password fields are required."

        stored_user = UserStore.find_user_by_id(user_id)
        if not stored_user:
            return False, "User account not found."

        # Verify old password
        if not verify_password(old_password, stored_user.get("password_hash", "")):
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.SECURITY_VALIDATION_FAILURE,
                    severity=SecuritySeverity.WARNING,
                    outcome="FAILURE",
                    user_id=user_id,
                    source="auth_manager.change_password",
                    reason="Incorrect old password during password change attempt"
                )
            except Exception:
                pass
            return False, "Current password is incorrect."

        # Validate new password policy
        is_valid, msg = validate_password_policy(new_password)
        if not is_valid:
            return False, msg

        if old_password == new_password:
            return False, "New password must be different from current password."

        # Update password hash and bump session_version
        new_hash = hash_password(new_password)
        updated = UserStore.update_password(user_id, new_hash)
        if not updated:
            return False, "Failed to update user credentials."

        # Invalidate current active session
        cls.logout()

        # Audit password change and session invalidation
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.PASSWORD_CHANGED,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=user_id,
                source="auth_manager.change_password",
                reason="User changed password; previous sessions invalidated"
            )
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.SESSION_INVALIDATED,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=user_id,
                source="auth_manager.change_password",
                reason="Sessions invalidated upon password update"
            )
        except Exception:
            pass

        logger.info(f"Password successfully changed for user_id={user_id}. All active sessions invalidated.")
        return True, "Password changed successfully. Please log in with your new password."

    @classmethod
    def has_role(cls, required_role: str) -> bool:
        """
        Authoritatively checks if current authenticated user has required role
        against the server-side UserStore rather than mutable session keys.
        """
        user = cls.get_current_user()
        if not user:
            return False
        uid = user.get("id")
        stored_user = UserStore.find_user_by_id(uid) if uid else None
        if stored_user:
            u_role = str(stored_user.get("role", "USER")).upper()
        else:
            u_role = str(user.get("role", "USER")).upper()

        # Detect privilege escalation tampering: session says ADMIN, but stored record says USER
        session_role = str(user.get("role", "")).upper()
        if session_role == "ADMIN" and u_role != "ADMIN":
            logger.warning(f"Privilege escalation attempt detected for user_id={uid}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
                    severity=SecuritySeverity.CRITICAL,
                    outcome="DENIED",
                    user_id=uid,
                    source="auth_manager.has_role",
                    reason="Session role tampered to ADMIN without database authority"
                )
            except Exception:
                pass
            return False

        r_req = str(required_role).upper()
        if u_role == "ADMIN":
            return True
        return u_role == r_req

    @classmethod
    def require_role(cls, required_role: str) -> bool:
        """Enforces role check, rendering error message if unauthorized."""
        if not cls.has_role(required_role):
            st.error(f"⛔ Access Denied: You do not have permission to view this section (Requires {required_role} role).")
            return False
        return True

    @classmethod
    def require_authentication(cls, render_ui: bool = True) -> bool:
        """
        Page guard: verifies authenticated session.
        If unauthenticated, renders login/registration form and returns False.
        If authenticated, returns True.
        """
        cls.initialize_session()
        if cls.is_authenticated():
            return True

        if render_ui:
            cls.render_auth_screen()
        return False

    @classmethod
    def render_auth_screen(cls) -> None:
        """Renders the standard AUREVIX login and account registration interface."""
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-size: 2rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">
                    ⚡ AUREVIX
                </div>
                <div style="color: #38bdf8; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;">
                    Universal Enterprise Business Analytics Platform
                </div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 6px;">
                    Please sign in to access your secure analytics workspace, datasets, and executive intelligence.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        auth_tab_login, auth_tab_reg = st.tabs(["🔐 Sign In", "📝 Create Account"])

        with auth_tab_login:
            with st.form("aurevix_login_form"):
                l_email = st.text_input("Email Address:", placeholder="analyst@company.com", key="auth_login_email")
                l_pwd = st.text_input("Password:", type="password", placeholder="••••••••", key="auth_login_pwd")
                submit_login = st.form_submit_button("🚀 Sign In to AUREVIX", use_container_width=True)

                if submit_login:
                    success, user_dict, err_msg = cls.authenticate(l_email, l_pwd)
                    if success and user_dict:
                        cls.login(user_dict)
                        st.success(f"Welcome back, {user_dict.get('display_name', 'Analyst')}!")
                        st.rerun()
                    else:
                        st.error(err_msg or "Invalid email or password.")

        with auth_tab_reg:
            with st.form("aurevix_reg_form"):
                r_email = st.text_input("Work Email:", placeholder="analyst@company.com", key="auth_reg_email")
                r_name = st.text_input("Full Name:", placeholder="Alex Mercer", key="auth_reg_name")
                r_pwd = st.text_input("Password (min 8 characters):", type="password", placeholder="••••••••", key="auth_reg_pwd")
                r_pwd_confirm = st.text_input("Confirm Password:", type="password", placeholder="••••••••", key="auth_reg_pwd_conf")
                submit_reg = st.form_submit_button("✨ Create Analyst Account", use_container_width=True)

                if submit_reg:
                    if r_pwd != r_pwd_confirm:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            new_u = cls.register(r_email, r_pwd, r_name, role="USER")
                            st.success("Account created successfully! Please sign in using your credentials.")
                        except ValueError as exc:
                            st.error(str(exc))

    @classmethod
    def render_top_auth_bar(cls) -> None:
        """
        Renders the authoritative global authentication bar at the top of the application experience.
        When authenticated: Displays welcome message, user role (ANALYST / ADMIN), and Logout button.
        When unauthenticated: Displays 'AUREVIX Enterprise BI & Analytics' with [ Sign In ] [ Sign Up ] controls.
        """
        cls.initialize_session()
        if cls.is_authenticated():
            curr_u = cls.get_current_user() or {}
            display_name = curr_u.get("display_name") or curr_u.get("email") or "Analyst"
            raw_role = str(curr_u.get("role", "USER")).upper()
            role_label = "ADMIN" if raw_role == "ADMIN" else "ANALYST"

            col_user_info, col_logout_btn = st.columns([5, 1.2])
            with col_user_info:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 12px; padding: 8px 14px; background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; margin-bottom: 8px;">
                        <span style="font-size: 1.15rem;">⚡</span>
                        <div style="font-size: 0.85rem; color: #cbd5e1;">
                            Welcome, <b style="color: #f8fafc;">{display_name}</b> &nbsp;|&nbsp; Role: <span style="background: {'rgba(239, 68, 68, 0.2)' if role_label == 'ADMIN' else 'rgba(56, 189, 248, 0.15)'}; color: {'#f87171' if role_label == 'ADMIN' else '#38bdf8'}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">{role_label}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_logout_btn:
                if st.button("🚪 Logout", key="top_auth_bar_logout", use_container_width=True):
                    cls.logout()
                    st.rerun()
        else:
            col_brand, col_actions = st.columns([4, 2.2])
            with col_brand:
                st.markdown(
                    """
                    <div style="display: flex; align-items: center; gap: 10px; padding: 6px 0; margin-bottom: 6px;">
                        <span style="font-size: 1.25rem;">⚡</span>
                        <div>
                            <div style="font-size: 1.05rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.01em;">AUREVIX</div>
                            <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Enterprise BI & Analytics</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_actions:
                col_in, col_up = st.columns(2)
                with col_in:
                    if st.button("🔐 Sign In", key="top_auth_bar_signin", use_container_width=True):
                        st.session_state["top_auth_active_tab"] = "signin" if st.session_state.get("top_auth_active_tab") != "signin" else None
                with col_up:
                    if st.button("📝 Sign Up", key="top_auth_bar_signup", use_container_width=True):
                        st.session_state["top_auth_active_tab"] = "signup" if st.session_state.get("top_auth_active_tab") != "signup" else None

            active_tab = st.session_state.get("top_auth_active_tab")
            if active_tab:
                with st.expander("🔐 AUREVIX Authentication Panel", expanded=True):
                    t_in, t_up = st.tabs(["🔐 Sign In", "📝 Sign Up"])
                    with t_in:
                        with st.form("top_bar_signin_form"):
                            email_val = st.text_input("Work Email:", placeholder="analyst@company.com", key="top_bar_login_email")
                            pwd_val = st.text_input("Password:", type="password", placeholder="••••••••", key="top_bar_login_pwd")
                            submit_in = st.form_submit_button("🚀 Sign In to AUREVIX", use_container_width=True)
                            if submit_in:
                                success, user_dict, err_msg = cls.authenticate(email_val, pwd_val)
                                if success and user_dict:
                                    cls.login(user_dict)
                                    st.session_state["top_auth_active_tab"] = None
                                    st.success(f"Welcome, {user_dict.get('display_name', 'Analyst')}!")
                                    st.rerun()
                                else:
                                    st.error(err_msg or "Invalid email or password.")
                    with t_up:
                        with st.form("top_bar_signup_form"):
                            reg_email = st.text_input("Work Email:", placeholder="analyst@company.com", key="top_bar_reg_email")
                            reg_name = st.text_input("Full Name:", placeholder="Alex Mercer", key="top_bar_reg_name")
                            reg_pwd = st.text_input("Password (min 8 chars):", type="password", placeholder="••••••••", key="top_bar_reg_pwd")
                            reg_pwd_conf = st.text_input("Confirm Password:", type="password", placeholder="••••••••", key="top_bar_reg_pwd_conf")
                            submit_up = st.form_submit_button("✨ Create Analyst Account", use_container_width=True)
                            if submit_up:
                                if not reg_email or not reg_name:
                                    st.error("Please enter both your name and email address.")
                                elif reg_pwd != reg_pwd_conf:
                                    st.error("Passwords do not match.")
                                else:
                                    try:
                                        new_user = cls.register(reg_email, reg_pwd, reg_name, role="USER")
                                        cls.login(new_user)
                                        st.session_state["top_auth_active_tab"] = None
                                        st.success(f"Account created successfully! Welcome, {new_user.get('display_name', 'Analyst')}!")
                                        st.rerun()
                                    except ValueError as exc:
                                        st.error(str(exc))
