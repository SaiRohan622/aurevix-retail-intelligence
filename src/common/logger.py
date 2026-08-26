"""
AUREVIX — Structured JSON & Contextual Logging Module
Provides enterprise-grade structured formatting, log level isolation,
and credential redaction.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

SENSITIVE_KEYS = {"password", "secret", "token", "key", "credential"}


class StructuredJsonFormatter(logging.Formatter):
    """Serializes log records into machine-readable JSON for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
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

        # Copy any extra custom attributes attached to the record
        for attr, val in record.__dict__.items():
            if attr not in standard_attrs and not attr.startswith("_"):
                log_obj[attr] = val

        # Sanitize sensitive fields
        for k in list(log_obj.keys()):
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                log_obj[k] = "[REDACTED]"

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


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
            formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
