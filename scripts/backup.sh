#!/bin/bash

# Backup script for Phonox database and image uploads
# Backs up: PostgreSQL database + disk images
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"

# Backup database
echo "Backing up PostgreSQL database..."
docker compose exec -T db pg_dump -U phonox --no-comments phonox > "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

# Backup image uploads
echo "Backing up image uploads..."
if [ -d "${ROOT_DIR}/data/uploads" ]; then
    tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${ROOT_DIR}/data" uploads/
    echo "Image backup: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
else
    echo "⚠️  No uploads directory found"
fi

echo "Backup completed!"
echo "Database backup: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

# Keep only last 7 days of backups
echo "Cleaning old backups (>7 days)..."
find "${BACKUP_DIR}" -name "phonox_db_*.sql" -type f -mtime +7 -delete
find "${BACKUP_DIR}" -name "phonox_uploads_*.tar.gz" -type f -mtime +7 -delete

echo "✅ Backup completed and old backups cleaned up."