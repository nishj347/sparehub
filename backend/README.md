# SpareHub Backend

FastAPI backend with SQLAlchemy 2.x, Alembic, and PostgreSQL.

## Automated Testing

The automated test suite runs against an isolated PostgreSQL test database (`sparehub_test`).

### 1. Test Database Setup
Create the test database in PostgreSQL:
```sql
CREATE DATABASE sparehub_test;
```

Ensure `TEST_DATABASE_URL` is configured in `backend/.env` (or environment):
```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sparehub_test
```
*Note: The test suite includes a safety check that immediately aborts if `TEST_DATABASE_URL` is missing, equals `DATABASE_URL`, or lacks the `_test` suffix.*

### 2. Running Tests
Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

Run pytest with coverage:
```bash
pytest
```

## User Administration CLI Tooling

### Create Initial Store Administrator
Create a super-admin user interactively with secure password entry via `getpass`:
```bash
python -m app.scripts.create_admin \
  --employee-id EMP001 \
  --name "Admin User" \
  --email "admin@example.com" \
  --location-code WH-NORTH
```
(You will be prompted securely for a password matching complexity rules).

### Bulk Import Users from CSV
Import users from a CSV roster (header: `employee_id,name,email,role,location_code`):
```bash
# Dry run validation
python -m app.scripts.import_users path/to/users.csv --dry-run

# Commit import and export generated passwords
python -m app.scripts.import_users path/to/users.csv --output generated_passwords.csv
```
The script runs in a single atomic transaction (all-or-nothing rollback) and generates secure 16-character temporary passwords.

