#!/bin/bash

# Restore script for Phonox database and image uploads
# Usage: ./restore.sh <backup_timestamp>
# Example: ./restore.sh 20260125_021500

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20260125_021500"
    echo ""
    echo "Available database backups:"
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
    
    # Wait for database to be ready (health check)
    echo "Waiting for PostgreSQL to be ready..."
    MAX_ATTEMPTS=60
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if docker compose exec -T db pg_isready -U phonox -h localhost > /dev/null 2>&1; then
            echo "PostgreSQL is ready!"
            break
        fi
        echo -n "."
        sleep 1
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo ""
        echo "❌ PostgreSQL did not start within 60 seconds"
        exit 1
    fi
    
    # Drop existing database and recreate it fresh
    echo ""
    echo "Preparing database..."
    docker compose exec -T db dropdb -U phonox phonox 2>/dev/null || true
    docker compose exec -T db createdb -U phonox phonox
    
    # Create a temp SQL file with \restrict line removed to avoid restricted mode
    TEMP_SQL=$(mktemp)
    sed '/^\\restrict/d' "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" > "${TEMP_SQL}"
    
    # Restore database with error checking
    echo "Restoring database from backup..."
    if docker compose exec -T db psql -U phonox -d phonox < "${TEMP_SQL}"; then
        echo "✅ Database restored successfully!"
    else
        echo "❌ Database restore failed"
        rm "${TEMP_SQL}"
        exit 1
    fi
    rm "${TEMP_SQL}"
else
    echo "❌ Database backup file not found: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
    exit 1
fi

echo "Starting all containers..."
docker compose up -d

# Restore image uploads if available
if [ -f "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" ]; then
    echo "Restoring image uploads..."
    # Extract to temporary location
    TEMP_UPLOADS=$(mktemp -d)
    tar -xzf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}"
    
    # Wait for backend to be ready (container must be running)
    echo "Waiting for backend container to be ready..."
    MAX_ATTEMPTS=60
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if docker compose exec -T backend test -d /app/uploads > /dev/null 2>&1; then
            echo "Backend is ready!"
            break
        fi
        echo -n "."
        sleep 1
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo ""
        echo "⚠️  Backend did not start within 60 seconds"
    fi
    
    # Copy uploads into the container's volume
    if [ -d "${TEMP_UPLOADS}/uploads" ]; then
        echo ""
        echo "Copying image files to container..."
        if docker cp "${TEMP_UPLOADS}/uploads/." "phonox_backend:/app/uploads/"; then
            echo "✅ Image uploads restored successfully!"
        else
            echo "❌ Failed to copy image files"
        fi
    else
        echo "⚠️  No uploads directory found in backup"
    fi
    
    rm -rf "${TEMP_UPLOADS}"
else
    echo "⚠️  Image backup not found: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
    echo "   (This is OK if no images were uploaded in that backup)"
fi

echo "✅ Restore completed!"