#!/bin/bash
# fresh_db.sh — Create a fresh timestamped PostgreSQL database and update .env.

PSQL_CMD="psql postgres"          # change to "psql -U postgres postgres" if required
ENV_FILE="$(dirname "$0")/../.env"
DB_NAME="narrateink$(date +%s)"
DB_URL="postgresql://${DB_NAME}:${DB_NAME}@localhost:5432/${DB_NAME}"

echo "========================================"
echo "  fresh_db: $DB_NAME"
echo "  env file: $ENV_FILE"
echo "========================================"

# ── Create role + database ────────────────────────────────────────────────────
$PSQL_CMD <<SQL
CREATE USER "${DB_NAME}" WITH LOGIN PASSWORD '${DB_NAME}';
CREATE DATABASE "${DB_NAME}" OWNER "${DB_NAME}";
GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO "${DB_NAME}";
SQL

if [ $? -ne 0 ]; then
    echo "WARNING: psql returned an error (database may already exist)" >&2
fi

echo "Database ready: $DB_NAME"

# ── Patch DATABASE_URL in .env ────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env not found at $ENV_FILE" >&2
    exit 1
fi

# Use perl for reliable in-place replacement on macOS
perl -pi -e 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://'"${DB_NAME}"':'"${DB_NAME}"'\@localhost:5432/'"${DB_NAME}"'|' "$ENV_FILE"

echo "--- .env DATABASE_URL ---"
grep "^DATABASE_URL=" "$ENV_FILE"
echo "-------------------------"
