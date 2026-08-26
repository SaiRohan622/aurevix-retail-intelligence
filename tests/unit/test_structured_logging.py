"""
AUREVIX — Unit Tests for Structured Logging & Credential Redaction
"""

import json
import logging
from src.common.logger import StructuredJsonFormatter, get_logger


def test_structured_json_formatting():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Pipeline batch transformation finished",
        args=(),
        exc_info=None
    )
    setattr(record, "pipeline", "batch_sales")
    setattr(record, "run_id", "run_999")
    setattr(record, "duration_seconds", 12.5)

    formatted = formatter.format(record)
    log_obj = json.loads(formatted)

    assert log_obj["level"] == "INFO"
    assert log_obj["pipeline"] == "batch_sales"
    assert log_obj["run_id"] == "run_999"
    assert log_obj["duration_seconds"] == 12.5


def test_structured_logging_credential_redaction():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=20,
        msg="Connecting to database",
        args=(),
        exc_info=None
    )
    setattr(record, "password", "my_secret_pw")
    formatted = formatter.format(record)
    log_obj = json.loads(formatted)

    assert log_obj.get("password") == "[REDACTED]"
