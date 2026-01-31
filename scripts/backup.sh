#!/bin/bash

# Backup script for Phonox database
# Note: Image uploads are temporary and not persisted; only database backup needed
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"

echo "Backing up PostgreSQL database..."
docker compose exec -T db pg_dump -U phonox phonox > "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

echo "Backup completed!"
echo "Database backup: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

# Keep only last 7 days of backups
find "${BACKUP_DIR}" -name "phonox_db_*.sql" -type f -mtime +7 -delete

echo "Old backups (>7 days) cleaned up."