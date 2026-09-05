"""
AUREVIX — Structured JSON & Contextual Logging Module
Provides enterprise-grade structured formatting, log level isolation,
and automated credential / connection-string redaction.
"""

import os
import sys
import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

SENSITIVE_KEYS = {"password", "secret", "token", "key", "credential", "auth", "api_key", "client_secret"}


def sanitize_log_text(text: str) -> str:
    """
    Automated text scrubbing that masks database passwords, API keys, and auth tokens.
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""

    # 1. Mask database URLs: postgresql://user:password@host:port/db -> postgresql://user:****@host:port/db
    sanitized = re.sub(
        r'(postgres(?:ql)?:\/\/[^:\s\'\"]+:)[^@\s\'\"]+(@)',
        r'\1****\2',
        text,
        flags=re.IGNORECASE
    )

    # 2. Mask key=value and key: value pairs for sensitive keywords
    sanitized = re.sub(
        r'((?:api[_-]?key|secret[_-]?key|password|passwd|token|auth_token|client_secret)\s*[:=]\s*["\']?)([^"\'\s,;{}]+)(["\']?)',
        r'\1****\3',
        sanitized,
        flags=re.IGNORECASE
    )

    # 3. Mask Authorization: Bearer tokens
    sanitized = re.sub(
        r'(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}',
        r'\1****',
        sanitized,
        flags=re.IGNORECASE
    )

    # 4. Mask well-known API key token patterns (AIza, sk-, ghp)
    sanitized = re.sub(
        r'\b(AIza[0-9A-Za-z\-_]{15,}|sk-[a-zA-Z0-9]{15,}|ghp_[0-9a-zA-Z]{15,})\b',
        r'****',
        sanitized
    )

    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Serializes log records into machine-readable JSON for log aggregators with strict redaction."""

    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        clean_msg = sanitize_log_text(raw_msg)

        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": clean_msg,
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
            "environment": os.getenv("AUREVIX_ENV", "development")
        }

        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message"
        }

        # Copy and sanitize custom attributes attached to the record
        for attr, val in record.__dict__.items():
            if attr not in standard_attrs and not attr.startswith("_"):
                if any(s in attr.lower() for s in SENSITIVE_KEYS):
                    log_obj[attr] = "[REDACTED]"
                elif isinstance(val, str):
                    log_obj[attr] = sanitize_log_text(val)
                else:
                    log_obj[attr] = val

        if record.exc_info:
            raw_exc = self.formatException(record.exc_info)
            log_obj["exception"] = sanitize_log_text(raw_exc)

        return json.dumps(log_obj)


class SanitizedStandardFormatter(logging.Formatter):
    """Standard console formatter that automatically redacts credentials from messages."""

    def format(self, record: logging.LogRecord) -> str:
        orig_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = sanitize_log_text(record.msg)
        formatted = super().format(record)
        record.msg = orig_msg
        return sanitize_log_text(formatted)


def get_logger(name: str = "aurevix", level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    log_level_name = (level or os.getenv("AUREVIX_LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, log_level_name, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Use Structured JSON formatting in production or if requested
        if os.getenv("AUREVIX_STRUCTURED_LOGGING", "false").lower() == "true":
            handler.setFormatter(StructuredJsonFormatter())
        else:
            fmt = "[%(asctime)s UTC] [%(levelname)s] [%(name)s]: %(message)s"
            formatter = SanitizedStandardFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
