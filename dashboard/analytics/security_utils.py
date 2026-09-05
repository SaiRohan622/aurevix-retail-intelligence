"""
AUREVIX — Comprehensive Security Utilities (Phases 1, 2, & 3)
Provides centralized file validation, format allowlisting, filename sanitization,
magic byte inspection, formula-injection export protection, path containment,
read-only SQL query validation, NLP prompt-injection firewall, HTML escaping,
and safe identifier normalization.
"""

import os
import re
import io
import html
import math
from pathlib import Path
from typing import List, Any, Optional, Tuple, Set, Union, Dict
import pandas as pd
from src.common.logger import get_logger

logger = get_logger("aurevix.security_utils")

# ==============================================================================
# 1. ALLOWLISTS & LIMITS
# ==============================================================================

# Allowed Business Data Formats
ALLOWED_EXTENSIONS: Set[str] = {".csv", ".xlsx", ".xls", ".json", ".parquet"}

# Dangerous Executable / Script / Macro Formats
DANGEROUS_EXTENSIONS: Set[str] = {
    ".exe", ".bat", ".cmd", ".ps1", ".py", ".pyw", ".js", ".mjs", ".vbs",
    ".wsf", ".msi", ".dll", ".scr", ".com", ".pif", ".cpl", ".hta", ".jar",
    ".sh", ".bash", ".bin", ".xlsm", ".xltm", ".xla", ".xlam", ".docm", ".dotm"
}

# Windows Reserved Device Names
WINDOWS_RESERVED_NAMES: Set[str] = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# SQL Mutation / Dangerous Keywords (Case-Insensitive)
SQL_DANGEROUS_KEYWORDS: Set[str] = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "COPY", "CALL", "DO", "EXECUTE", "EXEC", "VACUUM",
    "REINDEX", "SHUTDOWN", "INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE"
}

# Protected Database Catalogs / System Tables
SQL_SYSTEM_SCHEMAS: Set[str] = {
    "pg_catalog", "information_schema", "pg_shadow", "pg_user",
    "pg_authid", "pg_tables", "pg_database", "pg_proc"
}

# Configurable Max Upload Size (Default 50 MB)
DEFAULT_MAX_UPLOAD_SIZE_MB = 50
try:
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", str(DEFAULT_MAX_UPLOAD_SIZE_MB)))
except Exception:
    MAX_UPLOAD_SIZE_MB = DEFAULT_MAX_UPLOAD_SIZE_MB

MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ==============================================================================
# 2. FILENAME & PATH SANITIZATION
# ==============================================================================

def sanitize_upload_filename(filename: str) -> str:
    """
    Sanitizes user-provided filenames against path traversal, Windows drive letters,
    UNC network shares, control characters, null bytes, and Windows reserved names.
    Returns a safe basename with valid extension.
    """
    if not filename or not isinstance(filename, str):
        return "dataset.csv"

    # 1. Strip null bytes and control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(filename)).strip()

    # 2. Extract basename, stripping drive letters (e.g. C:, D:) and UNC paths (\\\\server\\share)
    cleaned = re.sub(r'^[a-zA-Z]:[/\\]*', '', cleaned)
    cleaned = re.sub(r'^[/\\]+', '', cleaned)
    cleaned = cleaned.replace('\\', '/')

    # Use PurePosixPath to get basename cross-platform (handles Windows & Linux paths)
    from pathlib import PurePosixPath
    base = PurePosixPath(cleaned).name

    # 3. Strip directory traversal sequences (../ and ..\)
    base = base.replace('/', '').replace('\\', '').replace('..', '')

    # 4. Extract stem and extension
    dot_idx = base.rfind('.')
    if dot_idx > 0:
        stem = base[:dot_idx]
        ext = base[dot_idx:].lower()
    else:
        stem = base
        ext = ".csv"

    # Sanitize characters in stem
    stem = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', stem).strip('._-')
    if not stem:
        stem = "dataset"

    # Check for Windows reserved device names
    if stem.upper() in WINDOWS_RESERVED_NAMES or any(stem.upper().startswith(f"{res}.") for res in WINDOWS_RESERVED_NAMES):
        stem = f"safe_{stem}"

    # Verify extension safety
    if ext in DANGEROUS_EXTENSIONS or ext not in ALLOWED_EXTENSIONS:
        if ext in DANGEROUS_EXTENSIONS:
            return f"{stem}_blocked.txt"
        ext = ".csv"

    return f"{stem}{ext}"


def sanitize_workspace_name(name: str, max_len: int = 64) -> str:
    """
    Sanitizes workspace and snapshot names, preventing directory traversal and
    Windows reserved device name conflicts.
    """
    if not name or not isinstance(name, str):
        return "workspace"

    # Convert to lowercase and strip null bytes and control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(name).lower()).strip()
    # Strip drive letters and directory separators
    cleaned = re.sub(r'^[a-zA-Z]:[/\\]*', '', cleaned)
    cleaned = cleaned.replace('/', '').replace('\\', '').replace('..', '')

    # Retain alphanumeric, hyphens, underscores
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', cleaned).strip('._-')
    if not safe_name:
        safe_name = "workspace"

    if len(safe_name) > max_len:
        safe_name = safe_name[:max_len]

    if safe_name.upper() in WINDOWS_RESERVED_NAMES:
        safe_name = f"safe_{safe_name}"

    return safe_name


def is_safe_path(target_path: Path, base_dir: Path) -> bool:
    """
    Verifies that target_path is canonical and strictly contained inside base_dir
    to eliminate directory traversal vulnerabilities.
    """
    try:
        resolved_target = target_path.resolve()
        resolved_base = base_dir.resolve()
        return resolved_base in resolved_target.parents or resolved_target == resolved_base
    except Exception:
        return False


# ==============================================================================
# 3. FILE CONTENT & SIZE VALIDATION
# ==============================================================================

def validate_file_security(file_bytes: bytes, filename: str) -> None:
    """
    Validates file size, non-empty payload, extension allowlist, and format magic bytes.
    Raises ValueError with controlled, user-safe error messages if invalid.
    """
    # 1. Size Validation
    if not file_bytes or len(file_bytes.strip()) == 0:
        raise ValueError("The uploaded file is empty. Please upload a dataset with data rows.")

    file_size = len(file_bytes)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            f"File exceeds the maximum allowed upload size ({MAX_UPLOAD_SIZE_MB} MB). "
            f"Uploaded size: {file_size / (1024 * 1024):.1f} MB."
        )

    # 2. Extension Validation
    name_lower = str(filename).lower().strip()
    ext = Path(name_lower).suffix.lower()

    if ext in DANGEROUS_EXTENSIONS:
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.FILE_SECURITY_REJECTION,
                severity=SecuritySeverity.HIGH,
                outcome="REJECTED",
                source="security_utils.validate_file_security",
                reason=f"Dangerous file extension: {ext}",
                metadata={"filename": sanitize_upload_filename(filename)}
            )
        except Exception:
            pass
        raise ValueError(
            f"Upload rejected: '{ext}' is an executable or unsafe file type. "
            "Only business data formats (.csv, .xlsx, .xls, .json, .parquet) are supported."
        )

    if ext and ext not in ALLOWED_EXTENSIONS:
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.FILE_SECURITY_REJECTION,
                severity=SecuritySeverity.WARNING,
                outcome="REJECTED",
                source="security_utils.validate_file_security",
                reason=f"Unsupported file extension: {ext}",
                metadata={"filename": sanitize_upload_filename(filename)}
            )
        except Exception:
            pass
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            "Supported formats: .csv, .xlsx, .xls, .parquet, .json"
        )

    # 3. Magic Byte & Content Structure Inspection
    if ext == ".parquet":
        if len(file_bytes) < 8 or not (file_bytes.startswith(b"PAR1") or file_bytes.endswith(b"PAR1")):
            raise ValueError("Unable to parse Parquet file: invalid Parquet file signature.")
    elif ext == ".xlsx":
        if len(file_bytes) < 4 or not file_bytes.startswith(b"PK\x03\x04"):
            raise ValueError("Unable to parse Excel file: invalid workbook structure or corrupted archive.")
    elif ext == ".json":
        stripped = file_bytes.strip()
        if stripped.startswith(b'\xef\xbb\xbf'):
            stripped = stripped[3:].strip()
        if not (stripped.startswith(b"{") or stripped.startswith(b"[")):
            raise ValueError("Unable to parse JSON dataset: invalid JSON root structure (expected object or array).")


# ==============================================================================
# 4. COLUMN NORMALIZATION & FORMULA EXPORT PROTECTION
# ==============================================================================

def sanitize_column_names(columns: List[Any]) -> List[str]:
    """
    Normalizes column names by stripping control characters, handling null/empty headers,
    trimming extreme lengths, and deterministically deduplicating collisions.
    """
    cleaned_cols: List[str] = []
    seen: dict = {}

    for idx, col in enumerate(columns):
        if col is None or pd.isna(col):
            c_str = f"unnamed_column_{idx + 1}"
        else:
            c_str = str(col).strip()
            c_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', c_str).strip()
            if not c_str:
                c_str = f"unnamed_column_{idx + 1}"

        if len(c_str) > 128:
            c_str = c_str[:128]

        if c_str in seen:
            seen[c_str] += 1
            cleaned_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            cleaned_cols.append(c_str)

    return cleaned_cols


def sanitize_for_spreadsheet_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formula Injection Neutralization for CSV and Excel exports.
    If a text/string cell begins with '=', '+', '-', or '@', prepends a single quote "'"
    to prevent spreadsheet engines (Excel, Calc) from executing it as a dynamic formula.
    Preserves genuine numeric values untouched.
    """
    if df is None or df.empty:
        return df

    export_df = df.copy()
    formula_triggers = ("=", "+", "-", "@")

    for col in export_df.columns:
        if export_df[col].dtype == object or pd.api.types.is_string_dtype(export_df[col]):
            def _neutralize(val):
                if isinstance(val, str) and len(val) > 0:
                    val_strip = val.lstrip('\t\r\n ')
                    if val_strip and val_strip[0] in formula_triggers:
                        first_char = val_strip[0]
                        if first_char in ("=", "@"):
                            return f"'{val}"
                        elif first_char in ("+", "-") and not val_strip[1:].replace(".", "", 1).isdigit():
                            return f"'{val}"
                return val

            try:
                export_df[col] = export_df[col].apply(_neutralize)
            except Exception:
                pass

    return export_df


# ==============================================================================
# 5. SQL INJECTION & READ-ONLY QUERY VALIDATION
# ==============================================================================

def validate_sql_query(query: str, allowed_tables: Optional[Set[str]] = None) -> bool:
    """
    Validates that a SQL query is strictly a read-only SELECT or WITH statement.
    Rejects DDL, DML mutations, multiple statements, SQL comment injection,
    and access to internal PostgreSQL system tables.
    """
    if not query or not isinstance(query, str):
        return False

    q_clean = query.strip()
    if not q_clean:
        return False

    # 1. Reject SQL comments used to manipulate query syntax
    if "--" in q_clean or "/*" in q_clean or "*/" in q_clean:
        logger.warning(f"SQL rejected: comment characters detected: {q_clean[:80]}")
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.SQL_SECURITY_REJECTION,
                severity=SecuritySeverity.CRITICAL,
                outcome="REJECTED",
                source="security_utils.validate_sql_query",
                reason="SQL comment injection pattern detected",
                metadata={"snippet": q_clean[:40]}
            )
        except Exception:
            pass
        return False

    # 2. Reject multi-statement execution (semicolons in query body)
    q_no_trailing_semi = q_clean.rstrip(";").strip()
    if ";" in q_no_trailing_semi:
        logger.warning(f"SQL rejected: multi-statement query detected: {q_clean[:80]}")
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.SQL_SECURITY_REJECTION,
                severity=SecuritySeverity.CRITICAL,
                outcome="REJECTED",
                source="security_utils.validate_sql_query",
                reason="Multi-statement SQL execution detected",
                metadata={"snippet": q_clean[:40]}
            )
        except Exception:
            pass
        return False

    # 3. Must start with SELECT or WITH
    q_upper = q_no_trailing_semi.upper()
    tokens = re.split(r'\s+', q_upper)
    first_token = tokens[0] if tokens else ""

    if first_token not in ("SELECT", "WITH"):
        logger.warning(f"SQL rejected: non-SELECT statement '{first_token}': {q_clean[:80]}")
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.SQL_SECURITY_REJECTION,
                severity=SecuritySeverity.CRITICAL,
                outcome="REJECTED",
                source="security_utils.validate_sql_query",
                reason=f"Non-SELECT statement: {first_token}",
                metadata={"statement_type": first_token}
            )
        except Exception:
            pass
        return False

    # 4. Check for mutation / destructive keywords
    for bad_kw in SQL_DANGEROUS_KEYWORDS:
        # Match keyword as standalone word token
        if re.search(rf'\b{re.escape(bad_kw)}\b', q_upper):
            logger.warning(f"SQL rejected: dangerous keyword '{bad_kw}': {q_clean[:80]}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.SQL_SECURITY_REJECTION,
                    severity=SecuritySeverity.CRITICAL,
                    outcome="REJECTED",
                    source="security_utils.validate_sql_query",
                    reason=f"Dangerous SQL keyword detected: {bad_kw}",
                    metadata={"keyword": bad_kw}
                )
            except Exception:
                pass
            return False

    # 5. Check for system schema / catalog access
    for sys_schema in SQL_SYSTEM_SCHEMAS:
        if re.search(rf'\b{re.escape(sys_schema)}\b', q_clean, re.I):
            logger.warning(f"SQL rejected: system catalog access '{sys_schema}': {q_clean[:80]}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.SQL_SECURITY_REJECTION,
                    severity=SecuritySeverity.CRITICAL,
                    outcome="REJECTED",
                    source="security_utils.validate_sql_query",
                    reason=f"System catalog access rejected: {sys_schema}",
                    metadata={"schema": sys_schema}
                )
            except Exception:
                pass
            return False

    # 6. Validate table allowlist if specified
    if allowed_tables is not None:
        table_pattern = re.compile(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)', re.I)
        matches = table_pattern.findall(q_clean)
        for m in matches:
            t_name = m.split(".")[-1].strip().lower()
            if t_name not in {t.lower() for t in allowed_tables}:
                logger.warning(f"SQL rejected: table '{t_name}' not in allowlist: {allowed_tables}")
                return False

    return True


def sanitize_sql_identifier(identifier: str, allowed_identifiers: Set[str]) -> str:
    """
    Validates a dynamic SQL identifier (e.g. column name, table name) against
    an explicit allowlist. Raises ValueError if not permitted.
    """
    clean_id = str(identifier).strip()
    if clean_id not in allowed_identifiers:
        # Check case-insensitive match
        match = next((a for a in allowed_identifiers if a.lower() == clean_id.lower()), None)
        if match:
            return match
        raise ValueError(f"Invalid SQL identifier '{clean_id}'. Identifier not in allowed schema.")
    return clean_id


# ==============================================================================
# 6. NLP / ASK-YOUR-DATA PROMPT INJECTION & EXFILTRATION FIREWALL
# ==============================================================================

NLP_INJECTION_PATTERNS = [
    # Jailbreaking / instruction hijacking
    re.compile(r'\b(ignore|disregard|forget|bypass)\s+(?:all\s+)?(all|previous|prior|system)\s+(instructions|rules|prompts|constraints)\b', re.I),
    re.compile(r'\b(jailbreak|dan\s+mode|\bdan\b|developer\s+mode|override\s+rules|system\s+prompt)\b', re.I),
    re.compile(r'\b(you are now|act as an unrestricted|unfiltered mode)\b', re.I),

    # Credential / secret exfiltration
    re.compile(r'\b(passwords?|passwd|api[_\s]*keys?|secret[_\s]*keys?|credentials?|private[_\s]*keys?|auth[_\s]*tokens?|db[_\s]*passwords?|database[_\s]*passwords?)\b', re.I),
    re.compile(r'\b(show|tell|reveal|give|print|dump|read|get|leak|what\s+is)\b.*?\b(passwords?|passwd|api[_\s]*keys?|secret[_\s]*keys?|credentials?|\.env|tokens?|database|config)\b', re.I),
    re.compile(r'\b(env\s+variables|environment\s+variables|\.env|env\s+file)\b', re.I),
    re.compile(r'\b(read\s+\.env|cat\s+\.env|dump\s+env)\b', re.I),

    # Destructive SQL execution requests
    re.compile(r'\b(drop\s+table|delete\s+from|truncate\s+table|alter\s+table|insert\s+into|grant\s+all)\b', re.I),

    # OS / Command injection requests
    re.compile(r'\b(os\.system|subprocess|cmd\.exe|powershell|/etc/passwd|/bin/sh|/bin/bash)\b', re.I),

    # Cross-workspace / Unauthorized data access
    re.compile(r'\b(access\s+(other|another)\s+(workspace|dataset|user)|dump\s+database|all\s+user\s+data)\b', re.I)
]


def validate_nlp_query(query: str, max_len: int = 500) -> Tuple[bool, Optional[str]]:
    """
    Validates natural language analytics queries against prompt injection,
    credential exfiltration, OS commands, destructive SQL, and length limits.
    Returns (is_safe, blocked_response_or_reason).
    """
    if not query or not isinstance(query, str):
        return True, None

    q_strip = query.strip()
    if not q_strip:
        return True, None

    # 1. Length Limit
    if len(q_strip) > max_len:
        return False, f"Your query exceeds the maximum allowed length ({max_len} characters). Please provide a concise analytical question."

    # 2. Check Security Firewall Patterns
    for pat in NLP_INJECTION_PATTERNS:
        if pat.search(q_strip):
            logger.warning(f"NLP Query blocked by security firewall: {q_strip[:80]}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.NLP_SECURITY_REJECTION,
                    severity=SecuritySeverity.HIGH,
                    outcome="REJECTED",
                    source="security_utils.validate_nlp_query",
                    reason="NLP prompt injection or secret exfiltration pattern detected",
                    metadata={"query_length": len(q_strip)}
                )
            except Exception:
                pass
            return False, (
                "I am the AUREVIX Business Intelligence Assistant. I provide analytics exclusively "
                "on your active workspace dataset. I cannot access system secrets, environment settings, "
                "other workspaces, or execute system/destructive commands."
            )

    return True, None


# ==============================================================================
# 7. HTML ESCAPING & OUTPUT SANITIZATION
# ==============================================================================

def escape_html_text(text: Any) -> str:
    """
    Safely escapes user-controlled strings for insertion into HTML components
    to prevent XSS attacks while preserving business readability.
    """
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def sanitize_numeric_input(val: Any, min_val: Optional[float] = None, max_val: Optional[float] = None, default: float = 0.0) -> float:
    """
    Safely parses and validates numeric bounds for targets, goals, and threshold inputs.
    """
    try:
        if val is None or val == "":
            return default
        num = float(val)
        if math.isnan(num) or math.isinf(num):
            return default
        if min_val is not None and num < min_val:
            return min_val
        if max_val is not None and num > max_val:
            return max_val
        return num
    except (ValueError, TypeError):
        return default


def sanitize_regex_pattern(pattern: str, max_len: int = 64) -> str:
    """
    Sanitizes user-supplied regular expressions to prevent ReDoS (catastrophic backtracking).
    """
    if not pattern or not isinstance(pattern, str):
        return ""

    cleaned = pattern.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]

    # Neutralize nested quantifiers e.g. (a+)+ -> (a+)
    cleaned = re.sub(r'(\([^)]*[\*\+\?]\))[\*\+\?]+', r'\1', cleaned)
    # Neutralize consecutive quantifiers e.g. ++, **
    cleaned = re.sub(r'[\*\+\?]{2,}', '*', cleaned)

    return cleaned


def validate_cors_origin(
    origin: Optional[str],
    allowed_origins: Optional[Tuple[str, ...]] = None,
    allow_credentials: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether an incoming HTTP Origin header is authorized under the CORS policy.
    1. Disallows wildcard '*' if credentials / authenticated session access is requested.
    2. Explicitly checks against configured allowed origins.
    3. Blocks untrusted, null, or missing origins for cross-origin access.
    Returns (is_allowed: bool, response_origin_or_error: Optional[str]).
    """
    from src.config.security_settings import SECURITY_SETTINGS

    configured = allowed_origins if allowed_origins is not None else getattr(SECURITY_SETTINGS, "CORS_ALLOWED_ORIGINS", ())

    if not origin:
        return False, "Missing or empty Origin header."

    origin_clean = origin.strip().lower()

    # Wildcard rejection for authenticated requests
    if origin_clean == "*" and allow_credentials:
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.CORS_BLOCKED,
                severity=SecuritySeverity.HIGH,
                outcome="DENIED",
                source="security_utils.validate_cors_origin",
                reason="Wildcard '*' disallowed for credentialed cross-origin requests"
            )
        except Exception:
            pass
        return False, "Wildcard '*' origin is prohibited for authenticated requests."

    # Normalized origin matching against allowed set
    allowed_set = {o.strip().lower() for o in configured if o.strip()}
    if origin_clean in allowed_set:
        return True, origin

    # If origin is not allowed, log and reject
    try:
        from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
        SecurityAuditLogger.log_event(
            event_type=SecurityEventType.CORS_BLOCKED,
            severity=SecuritySeverity.WARNING,
            outcome="DENIED",
            source="security_utils.validate_cors_origin",
            reason=f"Cross-origin request from untrusted origin: {origin_clean}"
        )
    except Exception:
        pass

    return False, f"Origin '{origin}' is not authorized by CORS policy."


def is_safe_web_path(target_path: str) -> bool:
    """
    Validates that a requested web path does not expose sensitive internal files,
    hidden files (.git, .env), or sensitive directories (credentials, secrets, data/security).
    """
    if not target_path or not isinstance(target_path, str):
        return False

    norm = target_path.replace("\\", "/").lower()

    # Block hidden files and directories
    parts = [p for p in norm.split("/") if p]
    for part in parts:
        if part.startswith(".") and not part == ".":
            return False

    # Block sensitive directories
    sensitive_segments = {
        "credentials", "secrets", "private", "security",
        "user_workspaces", "auth", ".git", ".env", ".venv"
    }
    if any(seg in parts for seg in sensitive_segments):
        return False

    # Block specific sensitive filenames
    sensitive_files = {
        "sbom.json", ".env", ".gitignore", "settings.py", "security_settings.py"
    }
    if any(p in sensitive_files for p in parts):
        return False

    return True


def verify_db_least_privilege(role_info: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verifies that the database runtime account does NOT possess superuser,
    createdb, createrole, or replication privileges.
    Returns (is_compliant: bool, list_of_violations: List[str]).
    """
    violations = []
    if role_info.get("rolsuper") or role_info.get("is_superuser"):
        violations.append("User has SUPERUSER privilege")
    if role_info.get("rolcreatedb") or role_info.get("can_create_db"):
        violations.append("User has CREATEDB privilege")
    if role_info.get("rolcreaterole") or role_info.get("can_create_role"):
        violations.append("User has CREATEROLE privilege")
    if role_info.get("rolreplication") or role_info.get("is_replication"):
        violations.append("User has REPLICATION privilege")

    if violations:
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.DATABASE_PRIVILEGE_CHECK_FAILURE,
                severity=SecuritySeverity.HIGH,
                outcome="DENIED",
                source="security_utils.verify_db_least_privilege",
                reason=f"Database user failed least-privilege checks: {', '.join(violations)}"
            )
        except Exception:
            pass
        return False, violations

    return True, []
