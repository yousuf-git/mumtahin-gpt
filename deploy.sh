#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
# Main deployment is for v2_rag (RAG-based version)
# For v1_basic, change APP_DIR to: /home/ubuntu/mumtahin-gpt/v1_basic
APP_DIR="/home/ubuntu/mumtahin-gpt/v2_rag"
SERVICE_NAME="mumtahingpt"
LOG_DIR="/home/ubuntu/deployments/shared/logs"
LOG_FILE="${LOG_DIR}/deploy.log"

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

echo -e "${YELLOW}Starting deployment at ${TIMESTAMP}${NC}"

# Function to log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
error_exit() {
    echo -e "${RED}ERROR: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE" 2>/dev/null || echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    exit 1
}

# Repository root
REPO_ROOT="/home/ubuntu/mumtahin-gpt"

# Check if this is initial deployment or update
if [ -d "${REPO_ROOT}/.git" ]; then
    log "Existing repository found. Performing update..."
    
    # Navigate to repository root
    cd "${REPO_ROOT}" || error_exit "Failed to navigate to repo root"
    
    # Pull latest changes from GitHub
    log "Pulling latest changes from GitHub..."
    git fetch origin || error_exit "Failed to fetch from origin"
    git reset --hard origin/main || error_exit "Failed to reset to origin/main"
else
    log "Initial deployment detected. Cloning repository..."
    
    # Create parent directory if needed
    mkdir -p "$(dirname "${REPO_ROOT}")"
    
    # Clone the repository
    cd "$(dirname "${REPO_ROOT}")"
    git clone https://github.com/yousuf-git/mumtahin-gpt.git || error_exit "Failed to clone repository"
    
    cd "${REPO_ROOT}" || error_exit "Failed to navigate to repo root"
fi

# Navigate to application directory
cd "${APP_DIR}" || error_exit "Failed to navigate to app directory"

# Setup virtual environment (create if doesn't exist)
if [ ! -d "venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv venv || error_exit "Failed to create virtual environment"
fi

# Activate virtual environment (in version directory)
log "Activating virtual environment..."
source venv/bin/activate || error_exit "Failed to activate virtual environment"

# Install/update dependencies (from repo root)
log "Installing dependencies..."
cd "${REPO_ROOT}"
pip install -r requirements.txt --quiet || error_exit "Failed to install dependencies"
# cd "${APP_DIR}"
cd /home/ubuntu/mumtahin-gpt

# Check if .env file exists, create if missing
if [ ! -f .env ]; then
    log ".env file not found. Creating from environment variables..."
    
    # Check if GEMINI_API_KEY is provided as environment variable
    if [ -z "$GEMINI_API_KEY" ]; then
        log "WARNING: GEMINI_API_KEY environment variable not set!"
        log "Please create .env file with required environment variables:"
        log "  - GEMINI_API_KEY=your_gemini_api_key"
        log "  - Add other required variables as needed"
        echo -e "${YELLOW}Do you want to continue without .env file? (y/n)${NC}"
        read -r continue_deploy
        if [ "$continue_deploy" != "y" ] && [ "$continue_deploy" != "Y" ]; then
            error_exit "Deployment cancelled. Please create .env file and try again."
        fi
    else
        # Create .env file from environment variable
        log "Creating .env file with GEMINI_API_KEY from environment..."
        echo "GEMINI_API_KEY=${GEMINI_API_KEY}" > .env
        chmod 600 .env
        log ".env file created successfully"
    fi
else
    log ".env file already exists, skipping creation"
fi

# Run database migrations (if applicable)
# Uncomment if you have migrations
# log "Running migrations..."
# python manage.py migrate || error_exit "Failed to run migrations"

# Restart the application service
log "Restarting application service..."
sudo systemctl restart ${SERVICE_NAME} || error_exit "Failed to restart service"

# Wait for service to start
log "Waiting for service to start..."
sleep 5

# Check service status
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    log "Service is running successfully"
else
    error_exit "Service failed to start"
fi

# Health check
log "Performing health check..."
# Update URL to your actual domain
if curl -f http://localhost:7860 > /dev/null 2>&1; then
    log "Health check passed ✓"
else
    log "WARNING: Health check failed, but service is running"
fi

# Success
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${GREEN}========================================${NC}"

log "Deployment completed successfully {5^^||_3}"

exit 0
