# AUREVIX — Enterprise Defense-in-Depth Security Architecture

## 1. Executive Summary
AUREVIX is an enterprise-grade Universal Business Intelligence and Real-Time Lakehouse Analytics platform designed with layered defense-in-depth security, strict cross-user data isolation, cryptographic audit logging, and supply-chain verification.

---

## 2. Layered Defense-in-Depth Model

```
               [ User / Browser Client ]
                          │
                          ▼
            [ Reverse Proxy / TLS 1.3 ]
     (HSTS, CSP, X-Content-Type-Options, Frame Defense)
                          │
                          ▼
           [ Authentication & Session Layer ]
   (scrypt Password Hashing, Session Fixation Defense,
       Session Timeout, Non-reversible Token Hashing)
                          │
                          ▼
          [ Role-Based Access Control (RBAC) ]
    (ADMIN / USER Role Enforcement, Cross-User Isolation,
         Workspace & Dataset Ownership Verification)
                          │
                          ▼
        [ Input & File Ingestion Security Firewall ]
 (Extension Allowlist, Magic Byte Inspection, Filename Sanitation,
      Formula Injection Neutralization, Column Deduplication)
                          │
                          ▼
         [ SQL & AI/NLP Prompt Security Firewall ]
 (Read-Only AST Validation, SQL Comment Injection Blocking,
   Prompt Injection Defense, Secret Exfiltration Trapping)
                          │
                          ▼
          [ Central Business Analytics Core ]
      (Data Profiler, Metric Engine, Insight Engine,
            Cleaning Recipe, Anomaly Detector)
                          │
                          ▼
     [ Operational Monitoring & Tamper-Evident Audit ]
  (Sliding-Window Rate Limiting, Suspicious Sequence Detection,
     Sequential SHA-256 Hash Chained Audit Log, Log Rotation)
                          │
                          ▼
        [ Safe Output, Export & Error Handling ]
 (Spreadsheet Neutralization, HTML XSS Escaping, Sanitized Errors,
            Unique Request Correlation Tracking)
```

---

## 3. Security Implementation by Phase

### Phase 1: Secrets & Configuration Security
- **Strict Environment Isolation**: Credentials injected exclusively via `.env` with `.env.example` placeholders.
- **Log Sanitization**: Global filter redacting database passwords, API keys, and connection strings from standard output and log files.
- **Serialization Redaction**: Sanitizes workspace and export JSON payloads before persistence.

### Phase 2: Secure File Upload & Data Ingestion
- **Strict Allowlisting**: Only `.csv`, `.xlsx`, `.xls`, `.json`, and `.parquet` permitted; dangerous extensions (`.exe`, `.sh`, `.bat`, `.py`) strictly rejected.
- **Magic-Byte Signature Verification**: Rejects spoofed extensions and macro-enabled workbooks (`.xlsm`).
- **Filename Sanitization**: Eliminates path traversal (`../`, `..\\`), null bytes (`\x00`), and Windows device names (`CON`, `PRN`, `AUX`).
- **Spreadsheet Formula Injection Defense**: Prepends single quotes to formula triggers (`=`, `+`, `-`, `@`).

### Phase 3: Input Validation, Injection Protection & AI Query Security
- **Read-Only SQL AST Firewall**: Enforces `SELECT` and `WITH` queries; blocks destructive statements (`DROP`, `DELETE`, `INSERT`, `ALTER`, `GRANT`).
- **SQL Comment Injection Blocking**: Forbids `--`, `/*`, and `*/` comment sequences and multi-statement semicolons.
- **NLP / Ask-Your-Data Firewall**: Traps jailbreaks, system prompt overrides, credential exfiltration requests, and OS commands.
- **Output XSS Sanitization**: HTML entity encoding prevents script injection while preserving business readability.

### Phase 4: Authentication, Authorization & User Data Isolation
- **Memory-Hard Password Hashing**: Utilizes `hashlib.scrypt` ($N=16384, r=8, p=1$) with 16-byte random salt.
- **Constant-Time Verification**: Defends against timing attacks via `hmac.compare_digest`.
- **Session Lifecycle & Fixation Defense**: Rotates session tokens on login; enforces 60-minute inactivity timeout.
- **Strict Resource Isolation**: Enforces user ownership over saved workspaces and persistent datasets.

### Phase 5: Dependency, Supply-Chain, Secret Scanning & SAST
- **Automated Vulnerability Scanning**: Continuous `pip-audit` scanning reports 0 known CVEs.
- **Static Application Security Testing**: Bandit AST scanning confirms 0 Medium and 0 High severity issues.
- **CycloneDX 1.5 SBOM**: Automated generation script (`scripts/generate_sbom.py`) creates machine-readable package inventory.
- **Least-Privilege CI**: GitHub Actions workflows declare `permissions: contents: read`.

### Phase 6: Security Monitoring, Audit Logging & Abuse Detection
- **Tamper-Evident Audit Chain**: Append-only JSONL event stream linked via SHA-256 hash chaining (`previous_event_hash` $\to$ `event_hash`).
- **Audit Verification**: `verify_audit_integrity()` cryptographically detects any record tampering or deletion.
- **Sliding-Window Rate Limiting**: Protects login, file upload, Ask-Your-Data NLP queries, and export operations.
- **Admin Security Operations Center**: Administrator-exclusive dashboard (`dashboard/pages/11_Security_Center.py`).

### Phase 7: Production Web Security, Safe Error Handling & Privacy
- **Safe Error Management**: Replaces raw stack traces with sanitized user messages and traceable correlation IDs.
- **Production Safeguards**: `validate_production_security()` fails-fast if default credentials or insecure keys are detected in production.
- **Privacy Assurance**: Audit logs, application logs, and exports never store or expose passwords, session IDs, API keys, or raw DataFrames.
