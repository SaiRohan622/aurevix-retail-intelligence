# AUREVIX — Platform Security Policy

## 1. Credentials & Secrets Management
- All authentication parameters (database passwords, API keys, Kafka secrets) MUST be injected through environment variables.
- The `.env` file is strictly ignored by version control.
- Never hardcode credentials in source code, Dockerfiles, or tests.

## 2. Principle of Least Privilege
- Database users are isolated to their designated schemas (`gold`, `analytics`, `monitoring`).
- Application containers run in non-privileged process space.

## 3. Vulnerability Reporting
To report a security vulnerability in the AUREVIX platform, please submit an issue to the security review team.
