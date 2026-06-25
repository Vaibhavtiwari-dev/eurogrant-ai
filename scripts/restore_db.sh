#!/bin/bash
set -e

# EuroGrant AI - Database Restore Script
# Usage: ./scripts/restore_db.sh <backup_file_path>

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file_path>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found."
    exit 1
fi

# Load environment variables
if [ -f "backend/.env" ]; then
    export $(grep -v '^#' backend/.env | xargs)
fi

echo "Starting database restore from ${BACKUP_FILE}..."

# Copy backup file to db container
docker compose cp "${BACKUP_FILE}" db:/tmp/db_restore.dump

# Terminate existing connections and drop the database before restoring
echo "Preparing database..."
docker compose exec -T db psql -U ${POSTGRES_USER:-postgres} -d postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${POSTGRES_DB:-eurogrant}' AND pid <> pg_backend_pid();"
docker compose exec -T db psql -U ${POSTGRES_USER:-postgres} -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-eurogrant};"
docker compose exec -T db psql -U ${POSTGRES_USER:-postgres} -d postgres -c "CREATE DATABASE ${POSTGRES_DB:-eurogrant};"

echo "Restoring data..."
docker compose exec -T db pg_restore -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-eurogrant} -1 /tmp/db_restore.dump

echo "Restore completed successfully!"
