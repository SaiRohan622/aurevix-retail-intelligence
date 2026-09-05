"""
AUREVIX — Centralized Security Configuration & Production Validation (Phase 7)
Defines enterprise security thresholds, bounds validation, and fail-fast production checks.
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Immutable, strongly typed security configuration."""

    # File Ingestion
    MAX_UPLOAD_SIZE_MB: int = Field(default=100, ge=1, le=500)
    ALLOWED_EXTENSIONS: tuple = (".csv", ".xlsx", ".xls", ".parquet", ".json")

    # Session & Authentication
    SESSION_TIMEOUT_MINUTES: int = Field(default=60, ge=5, le=1440)
    AUTH_MAX_LOGIN_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    AUTH_LOCKOUT_MINUTES: int = Field(default=15, ge=1, le=180)
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=8, le=128)

    # Operational Security & Audit
    SECURITY_AUDIT_ENABLED: bool = Field(default=True)
    SECURITY_AUDIT_MAX_MB: int = Field(default=25, ge=1, le=1000)
    SECURITY_AUDIT_RETENTION_DAYS: int = Field(default=30, ge=1, le=365)

    # Rate Limiting & Abuse Detection
    SECURITY_FAILED_LOGIN_THRESHOLD: int = Field(default=5, ge=1, le=50)
    SECURITY_FORBIDDEN_THRESHOLD: int = Field(default=5, ge=1, le=50)
    SECURITY_INJECTION_THRESHOLD: int = Field(default=3, ge=1, le=20)
    SECURITY_EXPORT_THRESHOLD: int = Field(default=30, ge=5, le=500)
    NLP_QUERY_MAX_LENGTH: int = Field(default=500, ge=50, le=5000)

    # AI / Ask-Your-Data Abuse & Resource Controls
    AI_MAX_QUERIES_PER_MINUTE: int = Field(default=10, ge=1, le=120)
    AI_MAX_QUERIES_PER_HOUR: int = Field(default=100, ge=5, le=2000)
    AI_REQUEST_TIMEOUT_SECONDS: int = Field(default=15, ge=1, le=120)
    AI_MAX_CONCURRENT_REQUESTS: int = Field(default=3, ge=1, le=20)
    AI_MAX_RESPONSE_CHARS: int = Field(default=4000, ge=100, le=50000)

    # Web & Origin Security
    CORS_ALLOWED_ORIGINS: tuple = Field(default=())
    SESSION_INVALIDATE_ON_PASSWORD_CHANGE: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Loads configuration from environment variables with fallback to safe defaults."""
        cors_raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
        cors_tuple = tuple(x.strip() for x in cors_raw.split(",") if x.strip())
        return cls(
            MAX_UPLOAD_SIZE_MB=int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")),
            SESSION_TIMEOUT_MINUTES=int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")),
            AUTH_MAX_LOGIN_ATTEMPTS=int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5")),
            AUTH_LOCKOUT_MINUTES=int(os.getenv("AUTH_LOCKOUT_MINUTES", "15")),
            SECURITY_AUDIT_ENABLED=os.getenv("SECURITY_AUDIT_ENABLED", "true").lower() == "true",
            SECURITY_AUDIT_MAX_MB=int(os.getenv("SECURITY_AUDIT_MAX_MB", "25")),
            SECURITY_AUDIT_RETENTION_DAYS=int(os.getenv("SECURITY_AUDIT_RETENTION_DAYS", "30")),
            SECURITY_FAILED_LOGIN_THRESHOLD=int(os.getenv("SECURITY_FAILED_LOGIN_THRESHOLD", "5")),
            SECURITY_FORBIDDEN_THRESHOLD=int(os.getenv("SECURITY_FORBIDDEN_THRESHOLD", "5")),
            SECURITY_INJECTION_THRESHOLD=int(os.getenv("SECURITY_INJECTION_THRESHOLD", "3")),
            SECURITY_EXPORT_THRESHOLD=int(os.getenv("SECURITY_EXPORT_THRESHOLD", "30")),
            NLP_QUERY_MAX_LENGTH=int(os.getenv("NLP_QUERY_MAX_LENGTH", "500")),
            AI_MAX_QUERIES_PER_MINUTE=int(os.getenv("AI_MAX_QUERIES_PER_MINUTE", "10")),
            AI_MAX_QUERIES_PER_HOUR=int(os.getenv("AI_MAX_QUERIES_PER_HOUR", "100")),
            AI_REQUEST_TIMEOUT_SECONDS=int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "15")),
            AI_MAX_CONCURRENT_REQUESTS=int(os.getenv("AI_MAX_CONCURRENT_REQUESTS", "3")),
            AI_MAX_RESPONSE_CHARS=int(os.getenv("AI_MAX_RESPONSE_CHARS", "4000")),
            CORS_ALLOWED_ORIGINS=cors_tuple,
            SESSION_INVALIDATE_ON_PASSWORD_CHANGE=os.getenv("SESSION_INVALIDATE_ON_PASSWORD_CHANGE", "true").lower() == "true",
        )


def validate_production_security(
    env_name: Optional[str] = None,
    pg_password: Optional[str] = None,
    secret_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates platform security readiness for production deployments.
    Raises ValueError with masked descriptions if insecure default values are detected.
    """
    env = env_name or os.getenv("AUREVIX_ENV", "development").lower()
    pwd = pg_password or os.getenv("POSTGRES_PASSWORD", "")
    key = secret_key or os.getenv("SECRET_KEY", "")

    issues = []

    # In production mode, reject default or placeholder secrets
    if env == "production":
        default_pwds = {"aurevix_secure_password_change_me", "postgres", "admin", "password", "123456"}
        if pwd in default_pwds or not pwd:
            issues.append("Insecure or default database password detected for production deployment.")

        default_keys = {"your_secret_key_here", "secret", "change_me", "default"}
        if key in default_keys or len(key) < 16:
            issues.append("Production SECRET_KEY must be a cryptographically secure value with at least 16 characters.")

    if issues:
        raise ValueError(f"Production Security Safeguard Alert: {'; '.join(issues)}")

    return {
        "status": "VALID",
        "environment": env,
        "safeguards_active": True
    }


def validate_database_least_privilege(role_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates that a database account follows least-privilege principles.
    Raises ValueError if administrative or superuser privileges are detected.
    """
    violations = []
    if role_info.get("rolsuper", False) or role_info.get("is_superuser", False):
        violations.append("Database user possesses SUPERUSER privilege.")
    if role_info.get("rolcreatedb", False) or role_info.get("can_create_db", False):
        violations.append("Database user possesses CREATEDB privilege.")
    if role_info.get("rolcreaterole", False) or role_info.get("can_create_role", False):
        violations.append("Database user possesses CREATEROLE privilege.")
    if role_info.get("rolreplication", False) or role_info.get("is_replication", False):
        violations.append("Database user possesses REPLICATION privilege.")

    if violations:
        raise ValueError(f"Database Least-Privilege Violation: {'; '.join(violations)}")

    return {
        "status": "VALID",
        "least_privilege_verified": True,
        "role_name": role_info.get("rolname", role_info.get("user", "unknown"))
    }


# Singleton config instance
SECURITY_SETTINGS = SecurityConfig.from_env()
