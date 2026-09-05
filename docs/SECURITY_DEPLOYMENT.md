# AUREVIX — Production Deployment & Web Security Guide

## 1. Overview
This document outlines recommended configurations for deploying AUREVIX in production environments with enterprise-grade web security, reverse-proxy SSL/TLS termination, HTTP security headers, and session protection.

---

## 2. Reverse Proxy Architecture (Nginx + Streamlit)
Streamlit operates an internal Tornado HTTP and WebSocket server on port `8501`. In production, AUREVIX must sit behind an enterprise reverse proxy (e.g. Nginx, Cloudflare, AWS ALB) enforcing HTTPS and security headers.

### Production Nginx Configuration Example:
```nginx
server {
    listen 80;
    server_name analytics.aurevix.internal;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name analytics.aurevix.internal;

    # SSL / TLS Hardening
    ssl_certificate /etc/ssl/certs/aurevix.crt;
    ssl_certificate_key /etc/ssl/private/aurevix.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HTTP Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Content-Security-Policy (Streamlit & Plotly Compatible)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:; connect-src 'self' ws: wss:;" always;

    # Client Request Size Limits
    client_max_body_size 100M;

    # Disable Directory Listing
    autoindex off;

    # Block Direct Access to Hidden Files & Version Control (.git, .env, .gitignore)
    location ~ /\.(?!well-known).* {
        deny all;
        return 404;
    }

    # Block Direct Web Access to Sensitive Data Directories
    location ~* ^/(data/security|data/user_workspaces|data/auth|credentials|secrets|private)/ {
        deny all;
        return 404;
    }

    # Block Direct Access to SBOM, Environment, and Build Manifests
    location ~* ^/(sbom\.json|\.env|\.venv|requirements\.txt|setup\.py)$ {
        deny all;
        return 404;
    }

    # Streamlit Reverse Proxy & WebSocket Pass-through
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## 2.1 CORS & Cross-Origin Policy
AUREVIX is designed as an integrated analytics workspace without public cross-origin API endpoints.
- In production, cross-origin browser access is restricted by default.
- If external internal portals require cross-origin access, origins must be explicitly allowlisted in `.env` via `CORS_ALLOWED_ORIGINS=https://portal.aurevix.internal`. Wildcards (`*`) are strictly prohibited for credentialed requests.

---

## 2.2 PostgreSQL Least-Privilege Configuration
In production, the runtime application service account (`aurevix_app`) must NOT possess `SUPERUSER`, `CREATEDB`, `CREATEROLE`, or `REPLICATION` privileges.

### Least-Privilege Provisioning Script (`scripts/setup_least_privilege_db.sql`):
```sql
-- 1. Create dedicated runtime user
CREATE USER aurevix_app WITH PASSWORD 'CHANGE_TO_STRONG_PRODUCTION_SECRET';

-- 2. Grant connection rights to target warehouse
GRANT CONNECT ON DATABASE aurevix_dw TO aurevix_app;

-- 3. Grant schema usage without schema alteration rights
GRANT USAGE ON SCHEMA gold TO aurevix_app;
GRANT USAGE ON SCHEMA monitoring TO aurevix_app;

-- 4. Grant DML rights exclusively on analytics and monitoring tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gold TO aurevix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO aurevix_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aurevix_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aurevix_app;

-- 5. Explicitly revoke administrative and public schema privileges
REVOKE CREATE ON SCHEMA gold FROM aurevix_app;
REVOKE CREATE ON SCHEMA monitoring FROM aurevix_app;
REVOKE ALL ON SCHEMA public FROM aurevix_app;

---

## 3. Session & Cookie Security
- **Session ID Hashing**: Internal session IDs are never logged or stored in cleartext; only SHA-256 prefix hashes are recorded in audit logs.
- **Inactivity Timeout**: Configurable via `SESSION_TIMEOUT_MINUTES=60`. Sessions automatically expire after 60 minutes of inactivity.
- **Session Fixation Defense**: Re-authenticating automatically rotates the active session token.
- **Cookie Security Flags**: Reverse proxy SSL termination ensures `Secure`, `HttpOnly`, and `SameSite=Lax` flags are applied.

---

## 4. CSRF & State Mutation Protection
- **WebSocket Protocol Isolation**: Streamlit conducts state mutations over a persistent bidirectional WebSocket connection. Arbitrary cross-origin HTTP `POST` form submissions cannot invoke internal application actions.
- **Session Authentication Guard**: Every protected action checks `AuthManager.is_authenticated()` and validates user ownership before mutating any dataset or workspace.

---

## 5. Production Environment Checklist
Before deploying AUREVIX to production:
1. Set `AUREVIX_ENV=production` in `.env`.
2. Generate a cryptographically strong `SECRET_KEY` (minimum 32 characters).
3. Replace default PostgreSQL credentials with dedicated, least-privilege credentials.
4. Run `validate_production_security()` to verify configuration integrity.
5. Verify that `data/security/` and `.env` are omitted from version control.
