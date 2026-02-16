#!/bin/bash

# Backup script for Phonox database and image uploads
# Backs up: PostgreSQL database + disk images

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

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

print_header "Phonox Backup"
print_info "Backup timestamp: $TIMESTAMP"
echo ""

echo "Creating backup directory..."
mkdir -p "${BACKUP_DIR}"

# Backup database
print_info "Backing up PostgreSQL database..."
if docker compose exec -T db pg_dump -U phonox --no-comments phonox > "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" 2>/dev/null; then
    DB_SIZE=$(du -h "${BACKUP_DIR}/phonox_db_${TIMESTAMP}.sql" | cut -f1)
    print_success "Database backup completed"
    print_info "  File: phonox_db_${TIMESTAMP}.sql"
    print_info "  Size: $DB_SIZE"
else
    print_error "Database backup failed"
    exit 1
fi

echo ""

# Backup image uploads
print_info "Backing up image uploads..."
if docker compose exec -T backend test -d /app/uploads > /dev/null 2>&1; then
    # Create temporary directory for uploads
    TEMP_UPLOADS=$(mktemp -d)
    
    # Copy uploads from container to temp location
    print_info "  Extracting images from container..."
    if docker cp "phonox_backend:/app/uploads/." "${TEMP_UPLOADS}/uploads/" 2>/dev/null; then
        # Count files
        IMAGE_COUNT=$(find "${TEMP_UPLOADS}/uploads" -type f 2>/dev/null | wc -l)
        
        if [ "$IMAGE_COUNT" -gt 0 ]; then
            print_info "  Found $IMAGE_COUNT image files"
            print_info "  Creating archive..."
            
            # Create tar archive from temp location
            if tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null; then
                UPLOADS_SIZE=$(du -h "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" | cut -f1)
                print_success "Image backup completed"
                print_info "  File: phonox_uploads_${TIMESTAMP}.tar.gz"
                print_info "  Size: $UPLOADS_SIZE"
            else
                print_error "Failed to create image archive"
            fi
        else
            print_warning "No image files found, creating empty archive..."
            tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
            print_success "Empty image archive created"
        fi
    else
        print_warning "Could not access images in container, creating empty archive..."
        mkdir -p "${TEMP_UPLOADS}/uploads"
        tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
        print_success "Empty image archive created"
    fi
    
    rm -rf "${TEMP_UPLOADS}"
else
    print_warning "Backend container not running, creating empty image archive"
    TEMP_UPLOADS=$(mktemp -d)
    mkdir -p "${TEMP_UPLOADS}/uploads"
    tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
    rm -rf "${TEMP_UPLOADS}"
    print_success "Empty image archive created"
fi

echo ""
print_header "Cleanup"

# Keep only last 7 days of backups
print_info "Cleaning old backups (>7 days)..."
DELETED_DB=$(find "${BACKUP_DIR}" -name "phonox_db_*.sql" -type f -mtime +7 -delete -print | wc -l)
DELETED_UPLOADS=$(find "${BACKUP_DIR}" -name "phonox_uploads_*.tar.gz" -type f -mtime +7 -delete -print | wc -l)

if [ "$DELETED_DB" -gt 0 ] || [ "$DELETED_UPLOADS" -gt 0 ]; then
    print_success "Old backups removed"
    print_info "  Deleted: $DELETED_DB database backups, $DELETED_UPLOADS upload archives"
else
    print_info "  No old backups to remove"
fi

echo ""
print_header "Backup Complete"
print_success "Backup finished successfully!"
echo ""
print_info "Backup files:"
ls -lh "${BACKUP_DIR}"/phonox_db_${TIMESTAMP}.sql "${BACKUP_DIR}"/phonox_uploads_${TIMESTAMP}.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
print_info "To restore this backup, run:"
print_info "  ./scripts/restore.sh $TIMESTAMP"
echo ""