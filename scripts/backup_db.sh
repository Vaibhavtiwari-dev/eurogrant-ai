#!/bin/bash
set -e

# EuroGrant AI - Database Backup Script
# Usage: ./scripts/backup_db.sh [backup_file_path]

BACKUP_FILE=${1:-"backup_$(date +%Y%m%d_%H%M%S).sql"}

# Load environment variables
if [ -f "backend/.env" ]; then
    export $(grep -v '^#' backend/.env | xargs)
fi

echo "Starting database backup to ${BACKUP_FILE}..."

docker compose exec -t db pg_dump -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-eurogrant} -F c -f /tmp/db_backup.dump

docker compose cp db:/tmp/db_backup.dump "${BACKUP_FILE}"

echo "Backup completed successfully!"
