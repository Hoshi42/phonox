#!/bin/bash

# Restore script for Phonox database and image uploads
# Usage: ./restore.sh <backup_timestamp>
# Example: ./restore.sh 20260125_021500

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local label=$3
    local width=40
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    
    printf "\r${CYAN}%-30s${NC} [" "$label"
    printf "%${filled}s" | tr ' ' '='
    printf "%$((width - filled))s" | tr ' ' '-'
    printf "] ${CYAN}%3d%%${NC}" "$percentage"
}

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_info() {
    echo -e "${CYAN}→ $1${NC}"
}

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

print_header "Phonox Restore (Backup: $TIMESTAMP)"

# Check if backup exists
if [ ! -f "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" ]; then
    print_error "Database backup file not found: ${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql"
    exit 1
fi

# Show backup info
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" | cut -f1)
print_info "Database backup size: $BACKUP_SIZE"

# Stopping containers
print_info "Stopping containers..."
docker compose down > /dev/null 2>&1
print_success "Containers stopped"

echo ""
print_header "Database Restoration"

print_info "Starting PostgreSQL container..."
docker compose up -d db > /dev/null 2>&1

# Wait for database to be ready (health check)
print_info "Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker compose exec -T db pg_isready -U phonox -h localhost > /dev/null 2>&1; then
        print_success "PostgreSQL is ready!"
        break
    fi
    show_progress $ATTEMPT 60 "PostgreSQL startup"
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done
echo ""

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    print_error "PostgreSQL did not start within 60 seconds"
    exit 1
fi

# Drop existing database and recreate it fresh
print_info "Preparing database (dropping old data)..."
docker compose exec -T db dropdb -U phonox phonox 2>/dev/null || true
docker compose exec -T db createdb -U phonox phonox
print_success "Database prepared"

# Create a temp SQL file with \restrict line removed to avoid restricted mode
print_info "Processing backup file..."
TEMP_SQL=$(mktemp)
TOTAL_LINES=$(wc -l < "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql")
sed '/^\\restrict/d' "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" > "${TEMP_SQL}"
print_success "Backup file processed"

# Restore database with progress
print_info "Restoring database from backup..."
if docker compose exec -T db psql -q -U phonox -d phonox < "${TEMP_SQL}" 2>/dev/null; then
    print_success "Database restored successfully!"
else
    print_error "Database restore failed"
    rm "${TEMP_SQL}"
    exit 1
fi
rm "${TEMP_SQL}"

echo ""
print_header "Image Restoration"

# Restore image uploads if available
if [ -f "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" ]; then
    IMAGES_SIZE=$(du -h "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" | cut -f1)
    print_info "Image backup size: $IMAGES_SIZE"
    
    print_info "Extracting image files..."
    TEMP_UPLOADS=$(mktemp -d)
    tar -xzf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" 2>/dev/null
    print_success "Image files extracted"
    
    print_info "Starting remaining containers..."
    docker compose up -d > /dev/null 2>&1
    
    # Wait for backend to be ready (container must be running)
    print_info "Waiting for backend container to be ready..."
    MAX_ATTEMPTS=60
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if docker compose exec -T backend test -d /app/uploads > /dev/null 2>&1; then
            print_success "Backend is ready!"
            break
        fi
        show_progress $ATTEMPT 60 "Backend startup"
        sleep 1
        ATTEMPT=$((ATTEMPT + 1))
    done
    echo ""
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_warning "Backend did not start within 60 seconds, but continuing..."
    fi
    
    # Copy uploads into the container's volume with progress
    if [ -d "${TEMP_UPLOADS}/uploads" ]; then
        IMAGE_COUNT=$(find "${TEMP_UPLOADS}/uploads" -type f | wc -l)
        UPLOAD_SIZE=$(du -sh "${TEMP_UPLOADS}/uploads" 2>/dev/null | cut -f1)
        print_info "Copying $IMAGE_COUNT image files ($UPLOAD_SIZE) to container..."
        
        # Use tar to copy files efficiently
        if tar -C "${TEMP_UPLOADS}" -cf - uploads/ 2>/dev/null | \
           docker exec -i phonox_backend tar -xf - -C / 2>/dev/null; then
            
            # Verify copy was successful
            CONTAINER_FILE_COUNT=$(docker exec -T phonox_backend find /app/uploads -type f 2>/dev/null | wc -l)
            
            # Show progress completion
            show_progress "$IMAGE_COUNT" "$IMAGE_COUNT" "Copying images"
            echo ""
            
            if [ "$CONTAINER_FILE_COUNT" -eq "$IMAGE_COUNT" ]; then
                print_success "Image uploads restored successfully! ($CONTAINER_FILE_COUNT files)"
            else
                print_warning "$CONTAINER_FILE_COUNT of $IMAGE_COUNT image files were copied"
            fi
        else
            print_error "Failed to copy image files to container"
        fi
    else
        print_warning "No uploads directory found in backup"
    fi
    
    rm -rf "${TEMP_UPLOADS}"
else
    print_warning "Image backup not found: ${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
    print_warning "Starting all containers without images..."
    docker compose up -d > /dev/null 2>&1
fi

echo ""
print_header "Restore Complete"
print_success "All services are now running!"
echo ""
print_info "Access your application:"
print_info "  - Frontend: http://localhost:5173"
print_info "  - Backend API: http://localhost:8000"
echo ""