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

# Live spinner that also shows the growing size of a file/directory.
# Usage: start_progress "message" "/path/to/watch"
_spinner_pid=""
start_progress() {
    local msg="$1"
    local watch="$2"
    local start_epoch
    start_epoch=$(date +%s)
    local spin='-\|/'
    (
        i=0
        while true; do
            now=$(date +%s)
            elapsed=$(( now - start_epoch ))
            extra=""
            if [[ -n "$watch" && -e "$watch" ]]; then
                extra=" ($(du -sh "$watch" 2>/dev/null | cut -f1))"
            fi
            printf "\r${CYAN}→   ${msg}${NC}${extra} [${spin:$((i % 4)):1}] ${elapsed}s  "
            (( i++ )) || true
            sleep 0.4
        done
    ) &
    _spinner_pid=$!
}

stop_progress() {
    if [[ -n "$_spinner_pid" ]]; then
        kill "$_spinner_pid" 2>/dev/null
        wait "$_spinner_pid" 2>/dev/null
        _spinner_pid=""
        printf "\r%-80s\r" ""
    fi
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
    start_progress "Extracting images from container..." "${TEMP_UPLOADS}/uploads"
    docker compose cp backend:/app/uploads/. "${TEMP_UPLOADS}/uploads/" 2>/dev/null
    _cp_rc=$?
    stop_progress
    if [ $_cp_rc -eq 0 ]; then
        # Count files
        IMAGE_COUNT=$(find "${TEMP_UPLOADS}/uploads" -type f 2>/dev/null | wc -l)
        
        if [ "$IMAGE_COUNT" -gt 0 ]; then
            print_info "  Found $IMAGE_COUNT image files"
            print_info "  Creating archive..."
            
            # Create tar archive from temp location
            start_progress "Packing archive..." "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
            tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
            _tar_rc=$?
            stop_progress
            if [ $_tar_rc -eq 0 ]; then
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
        # docker compose cp may have copied files even if it returned non-zero
        # (e.g. permission error on individual files). Check what was actually copied.
        RECOVERED_COUNT=$(find "${TEMP_UPLOADS}/uploads" -type f 2>/dev/null | wc -l)
        if [ "$RECOVERED_COUNT" -gt 0 ]; then
            print_warning "docker compose cp exited with errors but $RECOVERED_COUNT file(s) were recovered"
            print_info "  Creating archive from recovered files..."
            start_progress "Packing recovered files..." "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz"
            tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
            _tar_rc=$?
            stop_progress
            if [ $_tar_rc -eq 0 ]; then
                UPLOADS_SIZE=$(du -h "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" | cut -f1)
                print_success "Image backup completed (partial/recovered)"
                print_info "  File: phonox_uploads_${TIMESTAMP}.tar.gz"
                print_info "  Size: $UPLOADS_SIZE"
            else
                print_error "Failed to create image archive"
            fi
        else
            print_warning "Could not access images in container, creating empty archive..."
            mkdir -p "${TEMP_UPLOADS}/uploads"
            tar -czf "${BACKUP_DIR}/phonox_uploads_${TIMESTAMP}.tar.gz" -C "${TEMP_UPLOADS}" uploads/ 2>/dev/null
            print_success "Empty image archive created"
        fi
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

# Policy: always keep the last 4 backups; only delete backups older than 7 days
# beyond that minimum of 4.
KEEP_MIN=4
MAX_AGE_DAYS=7

cleanup_backups() {
    local pattern="$1"
    local deleted=0
    local now
    now=$(date +%s)
    local cutoff=$(( now - MAX_AGE_DAYS * 86400 ))

    # Collect files sorted newest-first
    mapfile -t files < <(find "${BACKUP_DIR}" -maxdepth 1 -name "${pattern}" -type f \
        -printf '%T@ %p\n' | sort -rn | awk '{print $2}')

    local total=${#files[@]}
    for (( i=0; i<total; i++ )); do
        file="${files[$i]}"
        # Always keep the most-recent KEEP_MIN backups
        if (( i < KEEP_MIN )); then
            continue
        fi
        # Delete older-than-MAX_AGE files beyond the minimum
        file_mtime=$(stat -c '%Y' "${file}" 2>/dev/null || echo "$now")
        if (( file_mtime < cutoff )); then
            rm -f "${file}"
            (( deleted++ )) || true
        fi
    done
    echo "$deleted"
}

print_info "Cleaning old backups (keep last ${KEEP_MIN}; remove >=${MAX_AGE_DAYS} days beyond that)..."
DELETED_DB=$(cleanup_backups "phonox_db_*.sql")
DELETED_UPLOADS=$(cleanup_backups "phonox_uploads_*.tar.gz")

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