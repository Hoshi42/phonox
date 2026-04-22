#!/bin/bash
# check_integrity.sh — wrapper that runs check_integrity.py inside the
# backend Docker container, where sqlalchemy, the database, and /app/uploads
# are natively available.
#
# Usage:
#   ./scripts/check_integrity.sh [options]
#
# All options are forwarded to check_integrity.py except --output, which is
# intercepted: the report is written inside the container and then copied to
# the requested host path.
#
# Examples:
#   ./scripts/check_integrity.sh
#   ./scripts/check_integrity.sh --output tmp/report.txt
#   ./scripts/check_integrity.sh --fix
#   ./scripts/check_integrity.sh --fix --output tmp/report.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTAINER="phonox_backend"
REMOTE_SCRIPT="/tmp/_phonox_check_integrity.py"
REMOTE_REPORT="/tmp/_phonox_integrity_report.txt"

# ─── Helpers ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
err()  { echo -e "${RED}✗ $*${NC}" >&2; }
info() { echo -e "${CYAN}→ $*${NC}"; }

# ─── Check container is running ───────────────────────────────────────────────
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    err "Container '${CONTAINER}' is not running."
    err "Start it with: docker compose up -d"
    exit 2
fi

# ─── Parse --output arg (intercept it so we can copy the file back) ───────────
OUTPUT_HOST=""
FORWARD_ARGS=()
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--output" && $# -gt 1 ]]; then
        OUTPUT_HOST="$2"
        # We'll write to a fixed path inside the container instead
        FORWARD_ARGS+=("--output" "${REMOTE_REPORT}")
        shift 2
    else
        FORWARD_ARGS+=("$1")
        shift
    fi
done

# ─── Copy script into container ────────────────────────────────────────────────
cd "${ROOT_DIR}"
info "Copying check_integrity.py into container..."
docker compose cp "${SCRIPT_DIR}/check_integrity.py" "backend:${REMOTE_SCRIPT}"

# ─── Run inside container ──────────────────────────────────────────────────────
info "Running integrity check inside ${CONTAINER}..."
echo ""
docker compose exec backend python3 "${REMOTE_SCRIPT}" "${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}"
RC=$?

# ─── Copy report back to host if --output was requested ───────────────────────
if [[ -n "$OUTPUT_HOST" ]]; then
    echo ""
    info "Copying report to host: ${OUTPUT_HOST}"
    mkdir -p "$(dirname "${OUTPUT_HOST}")"
    docker compose cp "backend:${REMOTE_REPORT}" "${OUTPUT_HOST}"
    info "Report saved: ${OUTPUT_HOST}"
    # Clean up report from container
    docker compose exec backend rm -f "${REMOTE_REPORT}" 2>/dev/null || true
fi

# ─── Clean up script from container ───────────────────────────────────────────
docker compose exec backend rm -f "${REMOTE_SCRIPT}" 2>/dev/null || true

exit $RC
