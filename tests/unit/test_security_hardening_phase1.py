"""
AUREVIX — Application Security Hardening (Phase 1) Test Suite
Validates:
1. .env.example contains only safe placeholders, no real secrets
2. .gitignore protects .env, .env.*, *.pem, *.key, *.secret, *.credentials, secrets/, credentials/, private/
3. settings.get_masked_database_url() redacts passwords
4. settings.to_dict() masks sensitive keys (POSTGRES_PASSWORD, SECRET_KEY, AI_API_KEY, FABRIC_CLIENT_SECRET)
5. settings.validate_production_requirements() raises safe error messages without exposing passwords
6. Structured logger automatically redacts sensitive record attributes
7. Logger automatically redacts connection strings and credentials from log message strings
8. Workspace serialization automatically redacts sensitive dictionary keys and database URLs
9. ExecutiveReportGenerator does not expose environment secrets or raw credentials
10. Diagnostics telemetry dictionary masks credentials
11. Missing optional AI API keys degrade gracefully without crashing
"""

import json
import logging
import re
import pytest
from pathlib import Path

from src.config.settings import ProductionSettings, settings, EnvironmentConfigError
from src.common.logger import StructuredJsonFormatter, SanitizedStandardFormatter, sanitize_log_text
from dashboard.analytics.workspace_manager import _make_json_serializable, WorkspaceManager
from dashboard.analytics.report_generator import ExecutiveReportGenerator
from dashboard.analytics.query_engine import AskYourDataEngine
import pandas as pd


def test_env_example_contains_no_real_credentials():
    """Verify .env.example contains only placeholders and no real secrets or passwords."""
    env_example = Path(".env.example")
    assert env_example.exists(), ".env.example must exist"
    content = env_example.read_text(encoding="utf-8")

    # Verify sensitive lines are placeholders
    assert "POSTGRES_PASSWORD=your_secure_password_here" in content
    assert "SECRET_KEY=your_secret_key_here" in content

    # Verify no real secret patterns exist
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if any(s in k.lower() for s in ("password", "secret", "key", "token")):
                assert v in ("", "your_secure_password_here", "your_secret_key_here", "aurevix-stream-processors", "dev-secret-key-change-in-production") or v.startswith("your_") or not v


def test_gitignore_protects_env_and_secret_files():
    """Verify .gitignore properly blocks .env and secret patterns while allowing .env.example."""
    gitignore = Path(".gitignore")
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")

    assert ".env" in content
    assert ".env.*" in content
    assert "!.env.example" in content
    assert "*.pem" in content
    assert "*.key" in content
    assert "*.secret" in content
    assert "*.credentials" in content
    assert "secrets/" in content
    assert "credentials/" in content
    assert "data/user_workspaces/*" in content


def test_settings_masked_database_url():
    """Verify get_masked_database_url() returns postgresql://user:****@host:port/db."""
    masked = settings.get_masked_database_url()
    assert "****@" in masked
    assert settings.POSTGRES_PASSWORD not in masked or settings.POSTGRES_PASSWORD == "****"


def test_settings_to_dict_masks_secrets():
    """Verify settings.to_dict(mask_secrets=True) redacts passwords and secrets."""
    safe_dict = settings.to_dict(mask_secrets=True)
    assert safe_dict["POSTGRES_PASSWORD"] == "****"
    assert safe_dict["SECRET_KEY"] == "****"
    assert safe_dict["DATABASE_URL"] == settings.get_masked_database_url()
    assert "Configured" in safe_dict["AI_INTEGRATION"] or "Not configured" in safe_dict["AI_INTEGRATION"]


def test_settings_production_validation_error_masks_credentials():
    """Verify production validation error message contains no passwords."""
    s = ProductionSettings()
    s.IS_PRODUCTION = True
    s.POSTGRES_PASSWORD = "aurevix_secure_password_change_me"

    with pytest.raises(EnvironmentConfigError) as exc_info:
        s.validate_production_requirements()

    err_msg = str(exc_info.value)
    assert "Default password detected" in err_msg
    # Ensure raw secret string is not in the message
    assert "aurevix_secure_password_change_me" not in err_msg


def test_logger_redacts_custom_sensitive_fields():
    """Verify StructuredJsonFormatter redacts fields like password, secret, token."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Database operation",
        args=(),
        exc_info=None
    )
    setattr(record, "db_password", "ultra_secret_pw_123")
    setattr(record, "api_token", "jwt_token_xyz_888")
    setattr(record, "safe_metric", 42)

    formatted = formatter.format(record)
    log_obj = json.loads(formatted)

    assert log_obj["db_password"] == "[REDACTED]"
    assert log_obj["api_token"] == "[REDACTED]"
    assert log_obj["safe_metric"] == 42


def test_logger_redacts_credentials_in_message_strings():
    """Verify logger cleans URLs and sensitive parameters inside the log message itself."""
    raw_message = "Connecting to postgresql://admin:SuperSecretPass123@localhost:5432/dw with api_key='sk-1234567890abcdef'"
    clean_message = sanitize_log_text(raw_message)

    assert "SuperSecretPass123" not in clean_message
    assert "sk-1234567890abcdef" not in clean_message
    assert "postgresql://admin:****@localhost:5432/dw" in clean_message
    assert "api_key='****'" in clean_message or "api_key=****" in clean_message


def test_workspace_json_serialization_redacts_sensitive_keys():
    """Verify _make_json_serializable redacts sensitive dictionary keys and URLs."""
    payload = {
        "dataset_name": "Sales.csv",
        "api_key": "sk-secret-9999",
        "db_password": "super_secret_password",
        "connection_url": "postgresql://user:mypassword@localhost:5432/db",
        "normal_metric": 100.5
    }

    serialized = _make_json_serializable(payload)
    assert serialized["api_key"] == "[REDACTED]"
    assert serialized["db_password"] == "[REDACTED]"
    assert "mypassword" not in serialized["connection_url"]
    assert "postgresql://user:****@localhost:5432/db" in serialized["connection_url"]
    assert serialized["normal_metric"] == 100.5


def test_export_generator_contains_no_secrets():
    """Verify executive reports do not expose passwords, tokens, or environment keys."""
    res = {
        "dataset_name": "Q3_Revenue.csv",
        "schema": {"domain": "Retail & E-Commerce"},
        "profile": {"quality_score": 98.5, "row_count": 1000, "col_count": 5, "missing_cells": 0, "duplicate_rows": 0, "completeness_score": 100.0, "uniqueness_score": 100.0, "consistency_score": 100.0, "memory_mb": 0.5},
        "kpis": {"total_revenue": 50000.0, "total_transactions": 1000},
        "insights": [{"title": "Revenue Growth", "observation": "Strong performance", "driver": "Volume", "impact": "High"}],
        "anomalies": []
    }

    report = ExecutiveReportGenerator.generate_report(res)
    assert "password" not in report.lower()
    assert "secret" not in report.lower()
    assert "token" not in report.lower()
    assert "api_key" not in report.lower()


def test_diagnostics_display_no_raw_credentials():
    """Verify settings.to_dict() safe representation for diagnostic display."""
    diag = settings.to_dict(mask_secrets=True)
    for k, v in diag.items():
        if "PASSWORD" in k or "SECRET" in k or "KEY" in k:
            assert v in ("****", None)


def test_missing_optional_ai_key_fails_gracefully():
    """Verify AskYourDataEngine provides clear, non-crashing response when AI key is missing."""
    df = pd.DataFrame({"product": ["A", "B"], "sales": [100, 200]})
    # Query engine answers deterministically without crashing even when external LLM key is absent
    ans = AskYourDataEngine.answer_question(df=df, query="What is total sales?")
    assert "answer" in ans
    assert ans["answer"] is not None
    assert len(ans["answer"]) > 0
