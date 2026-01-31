#!/bin/bash

# Restore script for Phonox database
# Note: Image uploads are temporary and restored from backups is not needed
# Usage: ./restore.sh <backup_timestamp>
# Example: ./restore.sh 20260125_021500

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20260125_021500"
    echo ""
    echo "Available backups:"
    ls -1 backups/phonox_db_*.sql 2>/dev/null | sed 's/.*phonox_db_//' | sed 's/.sql$//' | sort
    exit 1
fi

TIMESTAMP="$1"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"

echo "Stopping containers..."
docker compose down

echo "Restoring PostgreSQL database..."
if [ -f "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" ]; then
    # Start only the database
    docker compose up -d db
    sleep 10
    
    # Restore database
    docker compose exec -T db psql -U phonox -d phonox < "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
    echo "Database restored successfully!"
else
    echo "Database backup file not found: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
    exit 1
fi

echo "Starting all containers..."
docker compose up -d

echo "Restore completed!"