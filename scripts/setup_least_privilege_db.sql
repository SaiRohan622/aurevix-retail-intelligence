-- ==============================================================================
-- AUREVIX — PostgreSQL Runtime User Least-Privilege Provisioning Script
-- Defines minimal operational permissions for runtime analytics execution.
-- ==============================================================================

-- 1. Create dedicated runtime application user (replace placeholder password)
CREATE USER aurevix_app WITH PASSWORD 'CHANGE_TO_STRONG_PRODUCTION_SECRET';

-- 2. Grant basic connection rights
GRANT CONNECT ON DATABASE aurevix_dw TO aurevix_app;

-- 3. Grant schema usage (no DDL schema creation)
GRANT USAGE ON SCHEMA gold TO aurevix_app;
GRANT USAGE ON SCHEMA monitoring TO aurevix_app;

-- 4. Grant read/write data manipulation on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gold TO aurevix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO aurevix_app;

-- 5. Set default permissions for future tables created by migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aurevix_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aurevix_app;

-- 6. Explicitly revoke administrative privileges
REVOKE CREATE ON SCHEMA gold FROM aurevix_app;
REVOKE CREATE ON SCHEMA monitoring FROM aurevix_app;
REVOKE ALL ON SCHEMA public FROM aurevix_app;

-- 7. Verification query: Verify account is NOT SUPERUSER, CREATEDB, or CREATEROLE
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication
FROM pg_roles
WHERE rolname = 'aurevix_app';
