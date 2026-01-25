#!/bin/bash

# Backup script for Phonox database and uploads
BACKUP_DIR="${PWD}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"

echo "Backing up PostgreSQL database..."
docker exec phonox_db pg_dump -U phonox phonox > "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

echo "Backing up uploads..."
tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C data/uploads .

echo "Backup completed!"
echo "Database backup: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
echo "Uploads backup: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"

# Keep only last 7 days of backups
find "${BACKUP_DIR}" -name "phonox_*" -type f -mtime +7 -delete

echo "Old backups (>7 days) cleaned up."