-- Nexus PostgreSQL Role & Privilege Initialization
-- Reference: NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.md Section 13.2 & ADR-07

-- 1. MIGRATION ROLE (Used by Alembic in CI/CD or startup migration runner)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nexus_migrator') THEN
        CREATE ROLE nexus_migrator WITH LOGIN PASSWORD 'migrator_dev_password';
    END IF;
END $$;

GRANT ALL PRIVILEGES ON DATABASE nexus_dev TO nexus_migrator;
GRANT ALL ON SCHEMA public TO nexus_migrator;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nexus_migrator;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nexus_migrator;

-- 2. APPLICATION RUNTIME ROLE (Used by FastAPI web service pods)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nexus_app') THEN
        CREATE ROLE nexus_app WITH LOGIN PASSWORD 'app_dev_password';
    END IF;
END $$;

GRANT CONNECT ON DATABASE nexus_dev TO nexus_app;
GRANT USAGE ON SCHEMA public TO nexus_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nexus_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO nexus_app;

-- 3. SCHEDULED MAINTENANCE ROLE (Used by isolated retention worker pod at 03:00 UTC)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nexus_maintenance') THEN
        CREATE ROLE nexus_maintenance WITH LOGIN PASSWORD 'maint_dev_password';
    END IF;
END $$;

GRANT CONNECT ON DATABASE nexus_dev TO nexus_maintenance;
GRANT USAGE ON SCHEMA public TO nexus_maintenance;

