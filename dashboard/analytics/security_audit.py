"""
AUREVIX — Centralized Security Audit Logging & Integrity Engine (Phase 6)
Provides tamper-evident audit logging with SHA-256 hash chaining, log rotation,
retention pruning, correlation IDs, and non-sensitive structured event recording.
"""

import os
import sys
import json
import time
import uuid
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import streamlit as st

# Ensure project root is available on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.common.logger import get_logger, sanitize_log_text

logger = get_logger("aurevix.security_audit")

# ==============================================================================
# 1. CONSTANTS & EVENT DEFINITIONS
# ==============================================================================

class SecuritySeverity:
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityEventType:
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    AUTH_ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_UNAUTHORIZED_ACCESS = "AUTH_UNAUTHORIZED_ACCESS"
    AUTH_FORBIDDEN_ACCESS = "AUTH_FORBIDDEN_ACCESS"

    DATASET_UPLOAD = "DATASET_UPLOAD"
    DATASET_UPLOAD_REJECTED = "DATASET_UPLOAD_REJECTED"
    DATASET_ACCESS = "DATASET_ACCESS"
    DATASET_ACCESS_DENIED = "DATASET_ACCESS_DENIED"
    DATASET_DELETED = "DATASET_DELETED"

    WORKSPACE_CREATED = "WORKSPACE_CREATED"
    WORKSPACE_LOADED = "WORKSPACE_LOADED"
    WORKSPACE_DELETED = "WORKSPACE_DELETED"
    WORKSPACE_ACCESS_DENIED = "WORKSPACE_ACCESS_DENIED"

    FILE_SECURITY_REJECTION = "FILE_SECURITY_REJECTION"
    SQL_SECURITY_REJECTION = "SQL_SECURITY_REJECTION"
    NLP_SECURITY_REJECTION = "NLP_SECURITY_REJECTION"

    CLEANING_OPERATION = "CLEANING_OPERATION"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_EXPORT_REJECTED = "DATA_EXPORT_REJECTED"

    SECURITY_VALIDATION_FAILURE = "SECURITY_VALIDATION_FAILURE"
    RATE_LIMIT_TRIGGERED = "RATE_LIMIT_TRIGGERED"

    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    SESSION_INVALIDATED = "SESSION_INVALIDATED"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_USAGE_LIMIT_EXCEEDED = "AI_USAGE_LIMIT_EXCEEDED"
    CSRF_BLOCKED = "CSRF_BLOCKED"
    CORS_BLOCKED = "CORS_BLOCKED"
    ADMIN_ACCESS_DENIED = "ADMIN_ACCESS_DENIED"
    PRIVILEGE_ESCALATION_ATTEMPT = "PRIVILEGE_ESCALATION_ATTEMPT"
    SECURITY_CONFIGURATION_FAILURE = "SECURITY_CONFIGURATION_FAILURE"
    DATABASE_PRIVILEGE_CHECK_FAILURE = "DATABASE_PRIVILEGE_CHECK_FAILURE"


# Environment Configurations
DEFAULT_AUDIT_DIR = Path("data/security/audit")
DEFAULT_MAX_MB = 25
DEFAULT_RETENTION_DAYS = 30

AUDIT_DIR = Path(os.getenv("SECURITY_AUDIT_DIR", str(DEFAULT_AUDIT_DIR)))
try:
    MAX_FILE_SIZE_BYTES = int(os.getenv("SECURITY_AUDIT_MAX_MB", str(DEFAULT_MAX_MB))) * 1024 * 1024
except Exception:
    MAX_FILE_SIZE_BYTES = DEFAULT_MAX_MB * 1024 * 1024

try:
    RETENTION_DAYS = int(os.getenv("SECURITY_AUDIT_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)))
except Exception:
    RETENTION_DAYS = DEFAULT_RETENTION_DAYS

AUDIT_LOG_FILE = AUDIT_DIR / "audit.jsonl"
GENESIS_HASH = "0" * 64

# Sensitive key names strictly prohibited in audit log payloads
SENSITIVE_KEYS = {
    "password", "password_hash", "secret_key", "api_key", "secret", "token",
    "access_token", "refresh_token", "credentials", "database_url", "postgres_password",
    "ai_api_key", "raw_df", "filtered_df", "df", "private_key"
}


# ==============================================================================
# 2. SANITIZATION & HASHING HELPERS
# ==============================================================================

def get_action_correlation_id() -> str:
    """Returns or creates an action correlation ID for the active session."""
    try:
        if "action_correlation_id" not in st.session_state:
            st.session_state["action_correlation_id"] = secrets.token_hex(6)
        return st.session_state["action_correlation_id"]
    except Exception:
        return secrets.token_hex(6)


def hash_session_id(session_id: Optional[str]) -> Optional[str]:
    """Computes a non-reversible SHA-256 prefix hash of the session identifier."""
    if not session_id or not isinstance(session_id, str):
        return None
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]


def sanitize_audit_metadata(meta: Any) -> Any:
    """Recursively redacts sensitive credentials and DataFrame objects from audit payloads."""
    if isinstance(meta, dict):
        clean = {}
        for k, v in meta.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEYS):
                clean[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                clean[k] = sanitize_audit_metadata(v)
            elif isinstance(v, (str, int, float, bool)) or v is None:
                if isinstance(v, str):
                    clean[k] = sanitize_log_text(v)
                else:
                    clean[k] = v
            else:
                # If an unexpected complex object (e.g. DataFrame, Series) is passed, summarize it
                clean[k] = f"<{type(v).__name__}>"
        return clean
    elif isinstance(meta, list):
        return [sanitize_audit_metadata(item) for item in meta]
    elif isinstance(meta, str):
        return sanitize_log_text(meta)
    return meta


# ==============================================================================
# 3. SECURITY AUDIT LOGGER CLASS
# ==============================================================================

class SecurityAuditLogger:
    """Centralized, tamper-evident security audit logger with SHA-256 hash chaining."""

    @classmethod
    def _ensure_storage(cls) -> None:
        try:
            AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            if not AUDIT_LOG_FILE.exists():
                with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
                    pass
        except Exception as exc:
            logger.error(f"Audit directory initialization error: {exc}")

    @classmethod
    def _get_latest_hash(cls, file_path: Path) -> str:
        """Retrieves the event_hash of the last written record, or GENESIS_HASH."""
        if not file_path.exists():
            return GENESIS_HASH
        try:
            last_line = ""
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        last_line = line_str
            if last_line:
                record = json.loads(last_line)
                return record.get("event_hash", GENESIS_HASH)
        except Exception:
            pass
        return GENESIS_HASH

    @classmethod
    def _rotate_if_needed(cls) -> None:
        """Rotates the audit log file if it exceeds MAX_FILE_SIZE_BYTES."""
        try:
            if AUDIT_LOG_FILE.exists() and AUDIT_LOG_FILE.stat().st_size >= MAX_FILE_SIZE_BYTES:
                timestamp = int(time.time())
                rotated_path = AUDIT_DIR / f"audit_{timestamp}.jsonl"
                AUDIT_LOG_FILE.rename(rotated_path)
                logger.info(f"Audit log rotated to {rotated_path}")
        except Exception as exc:
            logger.error(f"Audit log rotation error: {exc}")

    @classmethod
    def _prune_retention(cls) -> None:
        """Prunes rotated log files older than RETENTION_DAYS."""
        try:
            now = time.time()
            cutoff = now - (RETENTION_DAYS * 86400)
            for f in AUDIT_DIR.glob("audit_*.jsonl"):
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    logger.info(f"Pruned expired audit log: {f}")
        except Exception as exc:
            logger.error(f"Audit log retention pruning error: {exc}")

    @classmethod
    def log_event(
        cls,
        event_type: str,
        severity: str = SecuritySeverity.INFO,
        outcome: str = "SUCCESS",
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        source: str = "aurevix.core",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        target_log_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Appends a structured security event to the audit log with SHA-256 hash chaining.
        Guaranteed to fail-safe without throwing exceptions to calling application logic.
        """
        try:
            log_path = target_log_file or AUDIT_LOG_FILE
            cls._ensure_storage()
            if target_log_file is None:
                cls._rotate_if_needed()
                cls._prune_retention()

            # 1. Resolve user context if not explicitly provided
            eff_user_id = user_id
            eff_role = user_role
            eff_sess_id = session_id
            if not (eff_user_id and eff_role and eff_sess_id):
                try:
                    import streamlit as st
                    auth = st.session_state.get("auth", {})
                    if isinstance(auth, dict) and auth.get("authenticated"):
                        eff_user_id = eff_user_id or auth.get("user_id")
                        eff_role = eff_role or auth.get("role")
                        eff_sess_id = eff_sess_id or auth.get("session_id")
                except Exception:
                    pass

            eff_user_id = eff_user_id or "anonymous"
            eff_role = eff_role or "GUEST"
            corr_id = correlation_id or get_action_correlation_id()
            event_id = str(uuid.uuid4())
            now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

            # 2. Sanitize metadata payload
            clean_meta = sanitize_audit_metadata(metadata or {})
            clean_reason = sanitize_log_text(str(reason)) if reason else None

            # 3. Form non-secret base record
            base_record = {
                "timestamp": now_iso,
                "event_id": event_id,
                "event_type": str(event_type),
                "severity": str(severity),
                "outcome": str(outcome),
                "user_id": str(eff_user_id),
                "user_role": str(eff_role),
                "session_id_hash": hash_session_id(eff_sess_id),
                "dataset_id": str(dataset_id) if dataset_id else None,
                "workspace_id": str(workspace_id) if workspace_id else None,
                "source": str(source),
                "reason": clean_reason,
                "metadata": clean_meta,
                "correlation_id": str(corr_id)
            }

            # 4. Compute cryptographic hash chain
            prev_hash = cls._get_latest_hash(log_path)
            canonical_repr = json.dumps(base_record, sort_keys=True, ensure_ascii=False)
            event_hash = hashlib.sha256(f"{canonical_repr}:{prev_hash}".encode("utf-8")).hexdigest()

            full_record = dict(base_record)
            full_record["previous_event_hash"] = prev_hash
            full_record["event_hash"] = event_hash

            # 5. Append to log file
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(full_record, ensure_ascii=False) + "\n")

            return full_record
        except Exception as exc:
            logger.error(f"Failed to record security audit event: {exc}")
            return {}

    @classmethod
    def verify_audit_integrity(cls, log_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Verifies the tamper-evident cryptographic hash chain of the audit log file.
        Returns validation result, record count, and first broken index if tampered.
        """
        path = log_file or AUDIT_LOG_FILE
        if not path.exists():
            return {"valid": True, "records_checked": 0, "first_broken_record": None, "message": "Log file empty or not found."}

        expected_prev = GENESIS_HASH
        records_checked = 0

        try:
            with open(path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    record = json.loads(line_str)
                    records_checked += 1

                    prev_in_rec = record.get("previous_event_hash")
                    stored_hash = record.get("event_hash")

                    # Verify chain link
                    if prev_in_rec != expected_prev:
                        return {
                            "valid": False,
                            "records_checked": records_checked,
                            "first_broken_record": idx,
                            "message": f"Broken chain link at record index {idx}: expected {expected_prev[:8]}..., found {str(prev_in_rec)[:8]}..."
                        }

                    # Recompute hash
                    base_rec = {k: v for k, v in record.items() if k not in ("previous_event_hash", "event_hash")}
                    canonical_repr = json.dumps(base_rec, sort_keys=True, ensure_ascii=False)
                    computed_hash = hashlib.sha256(f"{canonical_repr}:{prev_in_rec}".encode("utf-8")).hexdigest()

                    if computed_hash != stored_hash:
                        return {
                            "valid": False,
                            "records_checked": records_checked,
                            "first_broken_record": idx,
                            "message": f"Tampered record content at record index {idx} (hash mismatch)."
                        }

                    expected_prev = stored_hash

            return {
                "valid": True,
                "records_checked": records_checked,
                "first_broken_record": None,
                "message": f"Audit integrity verified successfully across {records_checked} records."
            }
        except Exception as exc:
            return {
                "valid": False,
                "records_checked": records_checked,
                "first_broken_record": records_checked,
                "message": f"Integrity check interrupted by error: {exc}"
            }

    @classmethod
    def get_audit_events(
        cls,
        limit: int = 100,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        outcome: Optional[str] = None,
        log_file: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves recent audit events matching optional search filters."""
        path = log_file or AUDIT_LOG_FILE
        if not path.exists():
            return []

        events = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in reversed(lines):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    record = json.loads(line_str)
                    if severity and record.get("severity") != severity:
                        continue
                    if event_type and record.get("event_type") != event_type:
                        continue
                    if user_id and record.get("user_id") != user_id:
                        continue
                    if outcome and record.get("outcome") != outcome:
                        continue
                    events.append(record)
                    if len(events) >= limit:
                        break
                except Exception:
                    continue
        except Exception as exc:
            logger.error(f"Error reading audit events: {exc}")

        return events

    @classmethod
    def get_security_summary(cls, log_file: Optional[Path] = None) -> Dict[str, Any]:
        """Calculates security telemetry counts and incident metrics for admin overview."""
        events = cls.get_audit_events(limit=500, log_file=log_file)
        summary = {
            "total_events": len(events),
            "severity_counts": {"INFO": 0, "WARNING": 0, "HIGH": 0, "CRITICAL": 0},
            "failed_logins": 0,
            "blocked_sql": 0,
            "blocked_nlp": 0,
            "blocked_uploads": 0,
            "rate_limit_events": 0,
            "access_denials": 0
        }

        for ev in events:
            sev = ev.get("severity", "INFO")
            if sev in summary["severity_counts"]:
                summary["severity_counts"][sev] += 1

            etype = ev.get("event_type")
            if etype == SecurityEventType.AUTH_LOGIN_FAILURE:
                summary["failed_logins"] += 1
            elif etype == SecurityEventType.SQL_SECURITY_REJECTION:
                summary["blocked_sql"] += 1
            elif etype == SecurityEventType.NLP_SECURITY_REJECTION:
                summary["blocked_nlp"] += 1
            elif etype in (SecurityEventType.FILE_SECURITY_REJECTION, SecurityEventType.DATASET_UPLOAD_REJECTED):
                summary["blocked_uploads"] += 1
            elif etype == SecurityEventType.RATE_LIMIT_TRIGGERED:
                summary["rate_limit_events"] += 1
            elif etype in (SecurityEventType.WORKSPACE_ACCESS_DENIED, SecurityEventType.DATASET_ACCESS_DENIED):
                summary["access_denials"] += 1

        return summary
