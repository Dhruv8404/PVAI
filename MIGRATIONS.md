# Database Migration Guide (Alembic)

This document describes how to manage database schema migrations in **PVAI** using **Alembic**.

---

## 1. Overview

In production, database schemas are managed through incremental migration scripts to ensure data persistence and rollback support. We use Alembic with async SQLAlchemy (`postgresql+asyncpg`).

All migration scripts are located under `backend/alembic/versions/`.

---

## 2. Dynamic Configuration

Alembic is configured dynamically. When running commands, `backend/alembic/env.py` reads the active database connection string from your environment settings (`DATABASE_URL` / `ASYNC_DATABASE_URL`). You do not need to configure connection details inside `alembic.ini`.

---

## 3. Basic Migration Commands

Run all migration commands from the `backend/` directory within your virtual environment.

### Generate a Migration (Autogenerate)
To detect schema changes in your SQLAlchemy models and generate a migration script automatically:
```bash
# From the backend/ folder
alembic revision --autogenerate -m "Describe your changes"
```
This generates a new file under `backend/alembic/versions/`. Always inspect the generated script to verify the operations.

### Apply Migrations (Upgrade)
To apply all pending migrations and update the database schema:
```bash
# Upgrade to the latest version
alembic upgrade head

# Upgrade to a specific revision version
alembic upgrade <revision_id>
```

### Rollback a Migration (Downgrade)
To undo the last migration applied:
```bash
# Roll back by one step
alembic downgrade -1

# Roll back to a specific revision version
alembic downgrade <revision_id>

# Reset database to empty schema state
alembic downgrade base
```

### Check Migration History & Status
To view current database status and history of migrations:
```bash
# View migration history
alembic history --verbose

# View the currently applied version
alembic current
```

---

## 4. Best Practices

1. **Verify Generated Code:** Autogenerate is extremely helpful, but it does not catch everything (e.g. table renames, column renames, custom constraints). Always review and edit the generated python files.
2. **Handle Default Values:** When adding non-nullable (`nullable=False`) columns to existing populated tables, specify a default value or split the migration into nullable addition -> data backfill -> non-nullable constraint.
3. **Run Checks in CI/CD:** Our GitHub Actions pipeline automatically checks if migrations can be compiled without syntax errors.
