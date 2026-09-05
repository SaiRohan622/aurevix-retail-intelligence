# AUREVIX — Platform Security & Supply-Chain Policy

## 1. Overview
AUREVIX is an enterprise-grade Universal Business Intelligence and Real-Time Lakehouse Analytics platform designed with comprehensive application security, defense-in-depth data protection, supply-chain verification, and strict user isolation.

---

## 2. Vulnerability Management & Reporting
If you discover a security vulnerability within the AUREVIX platform:
1. **Responsible Disclosure**: Please report details privately by contacting the platform security maintainers.
2. **Details to Include**: A clear description of the issue, affected component/module, steps to reproduce, and potential impact.
3. **Response Commitment**: Security reports are triaged and acknowledged within 48 hours.

---

## 3. Dependency & Supply-Chain Security Policy
AUREVIX enforces strict dependency hygiene and vulnerability management:

| Severity Level | CI/CD Action | Resolution Requirement |
| :--- | :--- | :--- |
| **CRITICAL** | **CI Build Failure** | Immediate patch or verified mitigation required. |
| **HIGH** | **CI Build Failure** | Patch required unless explicitly reviewed and documented. |
| **MEDIUM** | **Warning / Review** | Scheduled review during maintenance window. |
| **LOW** | **Informational** | Tracked in dependency audit log. |

### Running Dependency Security Audits:
```bash
# Scan active environment with pip-audit
pip-audit --desc
```

---

## 4. Static Application Security Testing (SAST)
Source code is continuously scanned for security vulnerabilities using **Bandit**:
```bash
# Execute SAST analysis across source code and dashboard
bandit -r src/ dashboard/ -x tests/ -ll
```

---

## 5. Secret Scanning & Credential Safety
- All secrets (passwords, tokens, API keys) must be passed exclusively via environment variables (`.env`).
- Live credentials and private keys (`.pem`, `.key`, `id_rsa`) are blocked by `.gitignore`.
- Secrets are masked in application logs via centralized sanitization filters (`src/common/logger.py`).
- Automated repository secret scanning is enforced using **Gitleaks**.

---

## 6. Software Bill of Materials (SBOM)
AUREVIX generates audit-ready Software Bill of Materials in **CycloneDX 1.5 JSON** format:
```bash
# Generate SBOM (saved to sbom.json)
python scripts/generate_sbom.py
```

---

## 7. Security Monitoring, Audit Logging & Tamper-Evident Integrity (Phase 6)
AUREVIX incorporates enterprise-grade operational security monitoring, structured audit logging, and suspicious activity detection:

### A. Tamper-Evident Audit Logging
- **Append-Only JSONL**: Stored locally in `data/security/audit/audit.jsonl` with automatic rotation (`SECURITY_AUDIT_MAX_MB=25`) and retention pruning (`SECURITY_AUDIT_RETENTION_DAYS=30`).
- **Cryptographic Hash Chaining**: Every audit event links back to the preceding record via a sequential SHA-256 hash chain (`previous_event_hash` $\to$ `event_hash`).
- **Chain Verification**: Audit integrity is cryptographically validated on demand:
  ```python
  from dashboard.analytics.security_audit import SecurityAuditLogger
  result = SecurityAuditLogger.verify_audit_integrity()
  print(result["message"])
  ```
- **Strict Data Redaction**: Passwords, hashes, raw session tokens, database URLs, and dataset row payloads are strictly redacted prior to serialization. Session identifiers are hashed using SHA-256 prefix truncations.

### B. Abuse Detection & Rate Limiting
- **In-Memory Sliding-Window Rate Limiting**: Protects authentication, file uploads, Ask-Your-Data NLP queries, exports, and workspace mutations.
- **Suspicious Sequence Detection**: Tracks threshold breaches for repeated failed logins, unauthorized cross-user workspace attempts, and SQL/NLP injection patterns.
- **Admin Security Center (`dashboard/pages/11_Security_Center.py`)**: Real-time security operations center accessible exclusively to users with the `ADMIN` role.

---

## 8. Security Testing & Verification
Execute the automated security test suites covering all hardening phases:
```powershell
# Run full Phase 1-6 security and regression test suite
.\.venv\Scripts\python.exe -m pytest tests/unit/ tests/integration/ -v
```
