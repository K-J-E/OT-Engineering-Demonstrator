PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS configuration_catalog (
    configuration_id TEXT PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    package_path TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    package_sha256 TEXT NOT NULL CHECK (length(package_sha256) = 64),
    data_sha256 TEXT NOT NULL CHECK (length(data_sha256) = 64),
    schema_sha256 TEXT NOT NULL CHECK (length(schema_sha256) = 64),
    source_references_json TEXT NOT NULL,
    registered_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_builds (
    application_build_id TEXT PRIMARY KEY CHECK (length(application_build_id) = 64),
    git_commit TEXT NOT NULL CHECK (length(git_commit) = 40),
    git_dirty INTEGER NOT NULL CHECK (git_dirty IN (0, 1)),
    python_version TEXT NOT NULL,
    node_version TEXT NOT NULL,
    npm_version TEXT NOT NULL,
    dependency_lock_hashes_json TEXT NOT NULL,
    backend_source_sha256 TEXT NOT NULL CHECK (length(backend_source_sha256) = 64),
    frontend_bundle_sha256 TEXT CHECK (
        frontend_bundle_sha256 IS NULL OR length(frontend_bundle_sha256) = 64
    ),
    manifest_json TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
