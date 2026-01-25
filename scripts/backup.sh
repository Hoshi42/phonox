#!/bin/bash

# Backup script for Phonox database and uploads
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
UPLOADS_VOLUME="phonox_phonox_uploads"

echo "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"

echo "Backing up PostgreSQL database..."
docker compose exec -T db pg_dump -U phonox phonox > "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

echo "Backing up uploads..."
docker run --rm \
	-v "${UPLOADS_VOLUME}:/data" \
	-v "${BACKUP_DIR}:/backup" \
	alpine sh -c "cd /data && tar -czf /backup/phonox_uploads_${TIMESTAMP}.tar.gz ."

echo "Backup completed!"
echo "Database backup: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
echo "Uploads backup: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"

# Keep only last 7 days of backups
find "${BACKUP_DIR}" -name "phonox_*" -type f -mtime +7 -delete

echo "Old backups (>7 days) cleaned up."