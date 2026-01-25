#!/bin/bash

# Restore script for Phonox database and uploads
# Usage: ./restore.sh <backup_timestamp>
# Example: ./restore.sh 20260125_021500

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20260125_021500"
    echo ""
    echo "Available backups:"
    ls -1 backups/phonox_* 2>/dev/null | sed 's/.*phonox_[du]b_//' | sed 's/\.(sql|tar\.gz)$//' | sort -u
    exit 1
fi

TIMESTAMP="$1"
BACKUP_DIR="${PWD}/backups"

echo "Stopping containers..."
docker compose down

echo "Restoring PostgreSQL database..."
if [ -f "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" ]; then
    # Start only the database
    docker compose up -d db
    sleep 10
    
    # Restore database
    docker exec -i phonox_db psql -U phonox -d phonox < "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
    echo "Database restored successfully!"
else
    echo "Database backup file not found: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
fi

echo "Restoring uploads..."
if [ -f "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" ]; then
    # Clear existing uploads and restore
    rm -rf data/uploads/*
    tar -xzf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C data/uploads/
    echo "Uploads restored successfully!"
else
    echo "Uploads backup file not found: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
fi

echo "Starting all containers..."
docker compose up -d

echo "Restore completed!"