# Disaster Recovery (DR) & Verification Policy

This document describes the automated disaster recovery validations and recovery policies.

---

## 1. Automated Non-Destructive Validations

The PVAI backend integrates a verification routine running at `/api/v1/ops/diagnostics` and at startup.

### Validation Parameters
The `run_dr_validation()` task checks:
1. **Schema Integrity:** Verifies database connectivity and check if the latest Alembic migration version number matches target schema version tables.
2. **Vector Store Integrity:** Pings ChromaDB client and checks collection structures.
3. **Uploads Persistence:** Scans database template paths and cross-checks that every file actually exists inside the storage provider (local disk or Cloudinary bucket).
4. **Reports Persistence:** Scans generated document metadata and verifies that the output HTML/PDF payloads are available for client retrieval.

---

## 2. Restore Procedures

If a validator flags missing assets:

### Database Recovery
1. Spin up a new Neon PostgreSQL server.
2. Apply schemas using migrations: `alembic upgrade head`.
3. Restore database dump using SQL backups:
   ```bash
   psql -h neon-host -U user -d db_name -f backup_dump.sql
   ```

### Storage Recovery
1. Set up storage provider credentials (e.g. Cloudinary cloud name and API secrets).
2. Run `scripts/production_check.py` or hit `/api/v1/ops/diagnostics` to confirm that all referenced assets resolve correctly.
