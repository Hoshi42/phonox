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
if docker compose exec -T backend test -d /app/uploads > /dev/null 2>&1; then
    # Create temporary directory for uploads
    TEMP_UPLOADS=$(mktemp -d)
    
    # Copy uploads from container to temp location
    docker cp "phonox_backend:/app/uploads/." "${TEMP_UPLOADS}/uploads/" 2>/dev/null || mkdir -p "${TEMP_UPLOADS}/uploads"
    
    # Create tar archive from temp location
    if [ "$(ls -A ${TEMP_UPLOADS}/uploads 2>/dev/null)" ]; then
        tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/
        echo "Image backup: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
    else
        echo "⚠️  No image files to backup (uploads directory is empty)"
        tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/
    fi
    
    rm -rf "${TEMP_UPLOADS}"
else
    echo "⚠️  Backend container not running, creating empty uploads backup"
    TEMP_UPLOADS=$(mktemp -d)
    mkdir -p "${TEMP_UPLOADS}/uploads"
    tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/
    rm -rf "${TEMP_UPLOADS}"
fi

echo "Backup completed!"
echo "Database backup: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"

# Keep only last 7 days of backups
echo "Cleaning old backups (>7 days)..."
find "${BACKUP_DIR}" -name "phonox_db_*.sql" -type f -mtime +7 -delete
find "${BACKUP_DIR}" -name "phonox_uploads_*.tar.gz" -type f -mtime +7 -delete

echo "✅ Backup completed and old backups cleaned up."