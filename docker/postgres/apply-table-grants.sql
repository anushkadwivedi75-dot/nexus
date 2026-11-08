-- Post-Migration Grant Enforcement
-- Reference: NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.md Section 13.2

-- Grant runtime privileges to application role
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nexus_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nexus_app;

-- Strict immutability enforcement on audit_logs for nexus_app:
REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM nexus_app;

-- Grant retention maintenance privileges
GRANT SELECT, DELETE ON audit_logs TO nexus_maintenance;
GRANT SELECT, DELETE ON outbox_events TO nexus_maintenance;

