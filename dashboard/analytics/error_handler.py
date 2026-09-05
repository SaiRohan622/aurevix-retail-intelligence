"""
AUREVIX — Centralized Safe Error Handling & Exception Management (Phase 7)
Guarantees user-safe error messaging, correlation ID tracking, and secure internal
logging without exposing stack traces, credentials, filesystem paths, or system internals.
"""

import sys
import uuid
import traceback
import streamlit as st
from typing import Optional, Dict, Any

from src.common.logger import get_logger, sanitize_log_text
from dashboard.analytics.security_audit import (
    SecurityAuditLogger,
    SecurityEventType,
    SecuritySeverity,
    get_action_correlation_id
)

logger = get_logger("aurevix.error_handler")

# Standard user-friendly error messages that reveal zero internals
DEFAULT_SAFE_ERROR_MESSAGE = (
    "Something went wrong while processing your request. Please try again. "
    "If the issue persists, contact platform support."
)

SAFE_ERROR_MAP = {
    "ValueError": "The provided input or file is invalid. Please verify the format and try again.",
    "PermissionError": "You do not have permission to perform this action.",
    "FileNotFoundError": "The requested resource could not be found.",
    "TimeoutError": "The operation timed out. Please try again in a moment.",
    "KeyError": "A required data field was missing or unrecognized."
}


def get_correlation_id() -> str:
    """Returns the current request or session correlation ID."""
    return get_action_correlation_id()


def safe_error_message(exc: Exception, context: Optional[str] = None) -> str:
    """
    Returns a sanitized, professional error message suitable for end-user display.
    Never exposes internal file paths, passwords, stack traces, or module names.
    """
    exc_type = type(exc).__name__

    # If the exception is already a sanitized business/security ValueError, check if its message is safe
    msg_str = str(exc)
    sanitized_msg = sanitize_log_text(msg_str)

    # Check if the message contains dangerous system keywords (traceback, file path, passwords)
    dangerous_indicators = ("traceback", "line ", "\\", "/", ".py", "postgresql:", "secret", "password")
    if any(d in sanitized_msg.lower() for d in dangerous_indicators):
        return SAFE_ERROR_MAP.get(exc_type, DEFAULT_SAFE_ERROR_MESSAGE)

    # If it's a short, user-friendly validation error message from our security validators, allow it
    if exc_type == "ValueError" and len(sanitized_msg) < 160:
        return sanitized_msg

    return SAFE_ERROR_MAP.get(exc_type, DEFAULT_SAFE_ERROR_MESSAGE)


def log_internal_error(
    exc: Exception,
    context: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Securely logs the full error context internally with sensitive data redacted.
    Returns the correlation ID for user reference.
    """
    corr_id = correlation_id or get_correlation_id()
    exc_type = type(exc).__name__
    clean_context = sanitize_log_text(context)

    # Format and sanitize the traceback
    raw_tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    clean_tb = sanitize_log_text(raw_tb)

    log_entry = {
        "correlation_id": corr_id,
        "exception_type": exc_type,
        "context": clean_context,
        "user_id": user_id or "anonymous",
        "traceback": clean_tb
    }
    if extra_metadata:
        log_entry["metadata"] = extra_metadata

    logger.error(
        f"[CORRELATION_ID={corr_id}] Error during '{clean_context}': "
        f"{exc_type}: {sanitize_log_text(str(exc))}\n{clean_tb}"
    )

    # Also log to security audit trail
    try:
        SecurityAuditLogger.log_event(
            event_type=SecurityEventType.SECURITY_VALIDATION_FAILURE,
            severity=SecuritySeverity.WARNING,
            outcome="ERROR",
            user_id=user_id,
            source=f"error_handler.{clean_context}",
            reason=f"{exc_type}: {sanitize_log_text(str(exc))[:100]}",
            correlation_id=corr_id,
            metadata={"context": clean_context, "exception_type": exc_type}
        )
    except Exception:
        pass

    return corr_id


def handle_application_error(
    exc: Exception,
    context: str,
    user_id: Optional[str] = None,
    show_ui: bool = True
) -> str:
    """
    Central error handling pipeline:
    1. Logs internal error details securely with sanitized traceback.
    2. Displays a safe, non-revealing error to the user if show_ui is True.
    Returns the user-safe error message.
    """
    corr_id = log_internal_error(exc, context, user_id)
    safe_msg = safe_error_message(exc, context)
    display_msg = f"{safe_msg} (Reference ID: `{corr_id}`)"

    if show_ui:
        try:
            st.error(display_msg)
        except Exception:
            pass

    return display_msg
