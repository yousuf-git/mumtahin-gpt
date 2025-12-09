#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Main rollback is for v2_rag (RAG-based version)
# For v1_basic, change APP_DIR to: /home/ubuntu/mumtahin-gpt/v1_basic
APP_DIR="/home/ubuntu/mumtahin-gpt/v2_rag"
BACKUP_DIR="/home/ubuntu/deployments/releases"
SERVICE_NAME="mumtahingpt"
LOG_DIR="/home/ubuntu/deployments/shared/logs"
LOG_FILE="${LOG_DIR}/rollback.log"

# Ensure directories exist
mkdir -p "${BACKUP_DIR}" "${LOG_DIR}"

# Function to log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
}

echo -e "${YELLOW}Available releases:${NC}"
if [ -z "$(ls -A "${BACKUP_DIR}" 2>/dev/null)" ]; then
    echo -e "${RED}No releases found in ${BACKUP_DIR}${NC}"
    exit 1
fi

ls -lt "${BACKUP_DIR}" | grep '^d' | awk '{print NR") "$9}'

echo ""
read -p "Enter release number to rollback to (or 'latest' for most recent): " choice

if [ "$choice" = "latest" ] || [ "$choice" = "1" ]; then
    RELEASE=$(ls -t "${BACKUP_DIR}" | head -1)
else
    RELEASE=$(ls -t "${BACKUP_DIR}" | sed -n "${choice}p")
fi

if [ -z "$RELEASE" ]; then
    echo -e "${RED}Invalid selection${NC}"
    exit 1
fi

# Handle both old backup structure and new structure
if [ -d "${BACKUP_DIR}/${RELEASE}/mumtahin-gpt/v2_rag" ]; then
    RELEASE_PATH="${BACKUP_DIR}/${RELEASE}/mumtahin-gpt/v2_rag"
elif [ -d "${BACKUP_DIR}/${RELEASE}/v2_rag" ]; then
    RELEASE_PATH="${BACKUP_DIR}/${RELEASE}/v2_rag"
else
    echo -e "${RED}Release path not found in ${BACKUP_DIR}/${RELEASE}${NC}"
    exit 1
fi

log "Rolling back to: ${RELEASE}"

# Backup current state
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ROLLBACK_BACKUP="${BACKUP_DIR}/rollback_${TIMESTAMP}"

log "Creating backup of current state..."
if ! mkdir -p "${ROLLBACK_BACKUP}"; then
    echo -e "${RED}Failed to create rollback backup directory${NC}"
    exit 1
fi

cp -r "${APP_DIR}" "${ROLLBACK_BACKUP}/" || {
    echo -e "${RED}Failed to backup current state${NC}"
    exit 1
}

# Restore from backup
log "Restoring files from backup..."
rm -rf "${APP_DIR}" || {
    echo -e "${RED}Failed to remove current application directory${NC}"
    exit 1
}

cp -r "${RELEASE_PATH}" "${APP_DIR}" || {
    echo -e "${RED}Failed to restore from backup${NC}"
    exit 1
}

# Restart service
log "Restarting service..."
if ! sudo systemctl restart ${SERVICE_NAME}; then
    echo -e "${RED}Failed to restart service${NC}"
    exit 1
fi

# Check status
log "Verifying service status..."
sleep 3
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Rollback completed successfully!${NC}"
    echo -e "${GREEN}Restored to: ${RELEASE}${NC}"
    echo -e "${GREEN}========================================${NC}"
    log "Rollback completed successfully to ${RELEASE}"
else
    echo -e "${RED}Service failed to start after rollback${NC}"
    log "ERROR: Service failed to start after rollback"
    exit 1
fi
