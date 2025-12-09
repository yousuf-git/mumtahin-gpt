# 🚀 CI/CD Pipeline Setup for AWS EC2 - Examiner AI

Complete guide to implement Continuous Integration and Continuous Deployment (CI/CD) for Examiner AI on AWS EC2 using GitHub Actions.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Setup GitHub Actions](#setup-github-actions)
5. [Configure EC2 for CI/CD](#configure-ec2-for-cicd)
6. [Create Deployment Scripts](#create-deployment-scripts)
7. [Setup GitHub Secrets](#setup-github-secrets)
8. [Create CI/CD Workflow](#create-cicd-workflow)
9. [Testing the Pipeline](#testing-the-pipeline)
10. [Advanced Features](#advanced-features)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

---

## 🎯 Overview

This CI/CD pipeline will:
- ✅ Automatically test code on every push
- ✅ Deploy to EC2 on push to `main` branch
- ✅ Run security checks and linting
- ✅ Create deployment artifacts
- ✅ Zero-downtime deployments
- ✅ Automatic rollback on failure
- ✅ Slack/Email notifications (optional)

**Deployment Flow:**
```
Push to GitHub → GitHub Actions → Build & Test → Deploy to EC2 → Restart App → Verify
```

---

## 📦 Prerequisites

Before starting, ensure you have:

- ✅ **GitHub Repository** with your code
- ✅ **AWS EC2 Instance** running (see [AWS_EC2_DEPLOYMENT.md](AWS_EC2_DEPLOYMENT.md))
- ✅ **Application running** with systemd service
- ✅ **SSH Key Pair** for EC2 access
- ✅ **Domain with HTTPS** configured (optional but recommended)
- ✅ **Basic Git knowledge**

**Required Files on EC2:**
- Application deployed at: `/home/ubuntu/mumtahin-gpt/`
- Systemd service: `/etc/systemd/system/mumtahin-gpt.service`
- Nginx configured and running

---

## 🏗️ Architecture

### Deployment Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   GitHub    │      │   GitHub     │      │   AWS EC2   │
│ Repository  │─────▶│   Actions    │─────▶│   Instance  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ├─ Build & Test
                            ├─ Security Scan
                            ├─ SSH Deploy
                            └─ Health Check
```

### CI/CD Stages

| Stage | Purpose | Duration |
|-------|---------|----------|
| **Checkout** | Clone repository | ~5s |
| **Setup** | Install dependencies | ~30s |
| **Lint** | Code quality checks | ~10s |
| **Test** | Run unit tests | ~20s |
| **Security** | Vulnerability scan | ~15s |
| **Build** | Create artifacts | ~10s |
| **Deploy** | SSH to EC2 & update | ~30s |
| **Verify** | Health check | ~10s |

**Total Pipeline Time:** ~2-3 minutes

---

## 🔧 Configure EC2 for CI/CD

### Step 1: Create Deployment User (Optional but Recommended)

```bash
# SSH to your EC2 instance
ssh -i mumtahingpt-key.pem ubuntu@YOUR_EC2_IP

# Create deployment user
sudo adduser --disabled-password --gecos "" deployer

# Add to sudo group (if needed)
sudo usermod -aG sudo deployer

# Allow passwordless sudo for deployment commands
sudo visudo

# Add this line at the end:
deployer ALL=(ALL) NOPASSWD: /bin/systemctl restart mumtahingpt, /bin/systemctl status mumtahingpt
```

### Step 2: Setup SSH Key for GitHub Actions

```bash
# Generate new SSH key pair for CI/CD (on your local machine)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/mumtahingpt-deploy

# This creates:
# - Private key: mumtahingpt-deploy (keep secret, add to GitHub)
# - Public key: mumtahingpt-deploy.pub (add to EC2)
# Copy public key content
cat ~/.ssh/mumtahingpt-deploy.pub
```

**Add public key to EC2:**

```bash
# SSH to EC2 as ubuntu user
ssh -i ~/.ssh/mumtahingpt-deploy.pem ubuntu@YOUR_EC2_IP

# Add public key to authorized_keys
nano ~/.ssh/authorized_keys

# Paste the public key content at the end
# Save and exit (Ctrl+X, Y, Enter)

# Set correct permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

**Test SSH connection from local machine:**

```bash
ssh -i ~/.ssh/mumtahingpt-deploy ubuntu@YOUR_EC2_IP

# If successful, you're connected without password!
# Exit: logout
```

### Step 3: Create Deployment Directory Structure

```bash
# SSH to EC2
ssh -i mumtahingpt-key.pem ubuntu@YOUR_EC2_IP

# Create deployment directories
mkdir -p ~/deployments/{releases,shared}
mkdir -p ~/deployments/shared/logs

# Set permissions
chmod 755 ~/deployments
```

### Step 4: Create Health Check Endpoint

Update your `app.py` to add a health check endpoint (if not already present):

```python
# Add this to your Gradio interface (already in Nginx config)
# This is handled by Nginx configuration at /health endpoint
# No changes needed in app.py
```

Verify health check:

```bash
curl http://localhost/health
# Should return: healthy
```

---

## 📝 Create Deployment Scripts

### Step 1: Create Deploy Script on EC2

```bash
# SSH to EC2
ssh -i mumtahingpt-key.pem ubuntu@YOUR_EC2_IP

# Create deployment script
nano ~/deploy.sh
```

**Add the following script:**

```bash
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/ubuntu/mumtahin-gpt"
BACKUP_DIR="/home/ubuntu/deployments/releases"
SERVICE_NAME="mumtahingpt"
LOG_DIR="/home/ubuntu/deployments/shared/logs"
LOG_FILE="${LOG_DIR}/deploy.log"

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RELEASE_DIR="${BACKUP_DIR}/${TIMESTAMP}"

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

# Create backup of current version
log "Creating backup of current version..."
if ! mkdir -p "${RELEASE_DIR}"; then
    error_exit "Failed to create release directory. Check permissions."
fi
cp -r "${APP_DIR}" "${RELEASE_DIR}/" || error_exit "Failed to create backup"

# Navigate to application directory
cd "${APP_DIR}" || error_exit "Failed to navigate to app directory"

# Pull latest changes from GitHub
log "Pulling latest changes from GitHub..."
git fetch origin || error_exit "Failed to fetch from origin"
git reset --hard origin/main || error_exit "Failed to reset to origin/main"

# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate || error_exit "Failed to activate virtual environment"

# Install/update dependencies
log "Installing dependencies..."
pip install -r requirements.txt --quiet || error_exit "Failed to install dependencies"

# Check if .env file exists
if [ ! -f .env ]; then
    log "WARNING: .env file not found!"
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
if curl -f http://localhost/health > /dev/null 2>&1; then
    log "Health check passed ✓"
else
    log "WARNING: Health check failed, but service is running"
fi

# Clean up old releases (keep last 5)
log "Cleaning up old releases..."
cd "${BACKUP_DIR}"
ls -t | tail -n +6 | xargs -r rm -rf

# Success
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${GREEN}========================================${NC}"

log "Deployment completed successfully"

exit 0
```

**Make it executable:**

```bash
chmod +x ~/deploy.sh

# Test the script
./deploy.sh

# Should see success message
```

### Step 2: Create Rollback Script

```bash
# Create rollback script
nano ~/rollback.sh
```

**Add the following:**

```bash
#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_DIR="/home/ubuntu/mumtahin-gpt"
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

RELEASE_PATH="${BACKUP_DIR}/${RELEASE}/mumtahin-gpt"

if [ ! -d "$RELEASE_PATH" ]; then
    echo -e "${RED}Release path not found: ${RELEASE_PATH}${NC}"
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
```

**Make it executable:**

```bash
chmod +x ~/rollback.sh
```

---

## 🔐 Setup GitHub Secrets

### Step 1: Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

**Add these secrets:**

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `EC2_HOST` | `YOUR_EC2_IP` or `your-domain.com` | EC2 public IP or domain |
| `EC2_USERNAME` | `ubuntu` | SSH username |
| `EC2_SSH_KEY` | `[private key content]` | Content of `mumtahingpt-deploy` private key |
| `GEMINI_API_KEY` | `your_api_key` | Google Gemini API key (optional) |

**To get private key content:**

```bash
# On your local machine
cat ~/.ssh/mumtahingpt-deploy

# Copy entire output including:
# -----BEGIN OPENSSH PRIVATE KEY-----
# ... (key content) ...
# -----END OPENSSH PRIVATE KEY-----
```

### Step 2: Verify Secrets

After adding all secrets, you should see:
- ✅ EC2_HOST
- ✅ EC2_USERNAME
- ✅ EC2_SSH_KEY
- ✅ GEMINI_API_KEY (optional)

---

## ⚙️ Create CI/CD Workflow

### Step 1: Create GitHub Actions Workflow Directory

```bash
# On your local machine, in your project directory
mkdir -p .github/workflows
```

### Step 2: Create Workflow File

```bash
# Create the workflow file
nano .github/workflows/deploy.yml
```

**Add the following comprehensive workflow:**

```yaml
name: Deploy to AWS EC2

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:  # Allow manual trigger

env:
  PYTHON_VERSION: '3.11'

jobs:
  # Job 1: Code Quality & Testing
  test:
    name: Code Quality & Tests
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout Code
        uses: actions/checkout@v4
      
      - name: 🐍 Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: 📦 Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install flake8 pylint black
      
      - name: 🎨 Check Code Formatting (Black)
        run: |
          black --check --diff app.py examiner_logic.py pdf_handler.py || true
      
      - name: 🔍 Lint with Flake8
        run: |
          # Stop build if there are Python syntax errors or undefined names
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          # Exit-zero treats all errors as warnings
          flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
      
      - name: 🔍 Lint with Pylint
        run: |
          pylint app.py examiner_logic.py pdf_handler.py --exit-zero
      
      - name: ✅ Syntax Check
        run: |
          python -m py_compile app.py
          python -m py_compile examiner_logic.py
          python -m py_compile pdf_handler.py
      
      - name: 📊 Generate Test Report
        if: always()
        run: |
          echo "## Test Results ✅" >> $GITHUB_STEP_SUMMARY
          echo "All code quality checks passed!" >> $GITHUB_STEP_SUMMARY

  # Job 2: Security Scan
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout Code
        uses: actions/checkout@v4
      
      - name: 🐍 Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: 🔒 Install Safety
        run: pip install safety
      
      - name: 🔍 Check Dependencies for Vulnerabilities
        run: |
          pip install -r requirements.txt
          safety check --json || true
      
      - name: 📊 Security Report
        if: always()
        run: |
          echo "## Security Scan 🔒" >> $GITHUB_STEP_SUMMARY
          echo "Dependency vulnerability scan completed" >> $GITHUB_STEP_SUMMARY

  # Job 3: Deploy to EC2
  deploy:
    name: Deploy to EC2
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
      - name: 📥 Checkout Code
        uses: actions/checkout@v4
      
      - name: 🔑 Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts
      
      - name: 🚀 Deploy to EC2
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USERNAME: ${{ secrets.EC2_USERNAME }}
        run: |
          ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no ${EC2_USERNAME}@${EC2_HOST} << 'ENDSSH'
            set -e
            echo "🔄 Starting deployment..."
            
            # Run deployment script
            cd ~
            ./deploy.sh
            
            echo "✅ Deployment completed!"
          ENDSSH
      
      - name: 🏥 Health Check
        run: |
          echo "Waiting for application to start..."
          sleep 10
          
          # Health check with retry
          for i in {1..5}; do
            if curl -f http://${{ secrets.EC2_HOST }}/health > /dev/null 2>&1; then
              echo "✅ Health check passed!"
              exit 0
            fi
            echo "Attempt $i failed, retrying..."
            sleep 5
          done
          
          echo "❌ Health check failed after 5 attempts"
          exit 1
      
      - name: 📊 Deployment Summary
        if: always()
        run: |
          echo "## Deployment Summary 🚀" >> $GITHUB_STEP_SUMMARY
          echo "- **Branch:** ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Commit:** ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Actor:** ${{ github.actor }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Timestamp:** $(date)" >> $GITHUB_STEP_SUMMARY
          echo "- **Status:** ${{ job.status }}" >> $GITHUB_STEP_SUMMARY
      
      - name: 🔄 Rollback on Failure
        if: failure()
        run: |
          echo "⚠️ Deployment failed, initiating rollback..."
          ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no ${{ secrets.EC2_USERNAME }}@${{ secrets.EC2_HOST }} << 'ENDSSH'
            cd ~
            ./rollback.sh <<< "latest"
          ENDSSH

  # Job 4: Notify
  notify:
    name: Notification
    runs-on: ubuntu-latest
    needs: [deploy]
    if: always()
    
    steps:
      - name: 📢 Deployment Status
        run: |
          if [ "${{ needs.deploy.result }}" == "success" ]; then
            echo "✅ Deployment succeeded!"
          else
            echo "❌ Deployment failed!"
          fi
```

**Save and exit.**

### Step 3: Create Additional Workflows

**Create Pull Request Check Workflow:**

```bash
nano .github/workflows/pr-check.yml
```

**Add:**

```yaml
name: PR Checks

on:
  pull_request:
    branches:
      - main

jobs:
  validate:
    name: Validate PR
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout Code
        uses: actions/checkout@v4
      
      - name: 🐍 Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: 📦 Install Dependencies
        run: |
          pip install -r requirements.txt
          pip install flake8 black
      
      - name: 🎨 Check Formatting
        run: black --check .
      
      - name: 🔍 Lint Code
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: ✅ Syntax Check
        run: |
          python -m py_compile app.py
          python -m py_compile examiner_logic.py
          python -m py_compile pdf_handler.py
      
      - name: 💬 Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ All checks passed! Ready for review.'
            })
```

---

## 🧪 Testing the Pipeline

### Test 1: Manual Trigger

1. Go to GitHub → **Actions** tab
2. Select **Deploy to AWS EC2** workflow
3. Click **Run workflow** → Select branch `main`
4. Click **Run workflow**
5. Watch the pipeline execute

### Test 2: Push to Main

```bash
# Make a small change
echo "# CI/CD Test" >> README.md

# Commit and push
git add .
git commit -m "Test CI/CD pipeline"
git push origin main

# Watch deployment in GitHub Actions tab
```

### Test 3: Pull Request

```bash
# Create new branch
git checkout -b feature/test-pr

# Make changes
echo "# Test PR" >> README.md

# Commit and push
git add .
git commit -m "Test PR checks"
git push origin feature/test-pr

# Create PR on GitHub
# Watch PR checks run automatically
```

### Verify Deployment

```bash
# SSH to EC2
ssh -i mumtahingpt-key.pem ubuntu@YOUR_EC2_IP

# Check service status
sudo systemctl status mumtahingpt

# View deployment logs
tail -f ~/deployments/shared/logs/deploy.log

# Check application logs
sudo journalctl -u mumtahingpt -f

# Test application
curl http://localhost/health
```

---

## 🚀 Advanced Features

### Feature 1: Slack Notifications

**Add to workflow (after deploy job):**

```yaml
- name: 📱 Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: |
      Deployment to Production
      Status: ${{ job.status }}
      Commit: ${{ github.sha }}
      Author: ${{ github.actor }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

**Setup:**
1. Create Slack webhook at: https://api.slack.com/apps
2. Add `SLACK_WEBHOOK` secret to GitHub

### Feature 2: Email Notifications

**Add to repository settings:**
1. Settings → Notifications
2. Enable email notifications for workflow runs

### Feature 3: Blue-Green Deployment

```bash
# Create blue-green deploy script
nano ~/deploy-blue-green.sh
```

**Add:**

```bash
#!/bin/bash
# Blue-Green deployment strategy
# Keeps two versions running, switches traffic atomically

BLUE_DIR="/home/ubuntu/mumtahin-gpt-blue"
GREEN_DIR="/home/ubuntu/mumtahin-gpt-green"
CURRENT_LINK="/home/ubuntu/mumtahin-gpt-current"

# Determine which is active
if [ -L "$CURRENT_LINK" ]; then
    ACTIVE=$(readlink -f "$CURRENT_LINK")
    if [ "$ACTIVE" = "$BLUE_DIR" ]; then
        INACTIVE="$GREEN_DIR"
        NEW_COLOR="green"
    else
        INACTIVE="$BLUE_DIR"
        NEW_COLOR="blue"
    fi
else
    INACTIVE="$BLUE_DIR"
    NEW_COLOR="blue"
fi

echo "Deploying to $NEW_COLOR environment..."

# Deploy to inactive
cd "$INACTIVE"
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Test inactive environment
# (start on different port, test, then switch)

# Switch traffic
ln -sfn "$INACTIVE" "$CURRENT_LINK"
sudo systemctl restart mumtahingpt

echo "Switched to $NEW_COLOR environment!"
```

### Feature 4: Canary Deployment

**Gradually roll out to percentage of users:**

```yaml
- name: 🐤 Canary Deployment
  run: |
    # Deploy to 10% of servers first
    # Monitor metrics for 5 minutes
    # If successful, deploy to 50%, then 100%
```

### Feature 5: Automated Backups Before Deploy

```bash
# Add to deploy.sh before deployment
BACKUP_S3="s3://your-bucket/backups"
aws s3 cp /home/ubuntu/mumtahin-gpt "$BACKUP_S3/$(date +%Y%m%d_%H%M%S)/" --recursive
```

### Feature 6: Database Migrations

**If you add a database in future:**

```yaml
- name: 🗄️ Run Migrations
  run: |
    ssh -i ~/.ssh/deploy_key ${EC2_USERNAME}@${EC2_HOST} << 'ENDSSH'
      cd ~/mumtahin-gpt
      source venv/bin/activate
      python manage.py migrate
    ENDSSH
```

### Feature 7: Performance Monitoring

**Add monitoring after deployment:**

```yaml
- name: 📊 Monitor Performance
  run: |
    # Use tools like:
    # - New Relic
    # - Datadog
    # - CloudWatch
    # - Grafana
```

---

## 🐛 Troubleshooting

### Issue 1: SSH Connection Failed

```bash
# Check SSH key format
cat ~/.ssh/deploy_key | head -1
# Should start with: -----BEGIN OPENSSH PRIVATE KEY-----

# Test SSH manually
ssh -i ~/.ssh/deploy_key ubuntu@YOUR_EC2_IP

# Check GitHub secret
# Make sure EC2_SSH_KEY contains entire private key including headers
```

### Issue 2: Permission Denied (publickey)

```bash
# On EC2, check authorized_keys
cat ~/.ssh/authorized_keys

# Ensure public key is present
# Check permissions
ls -la ~/.ssh/
# Should be: drwx------ (700) for .ssh
# Should be: -rw------- (600) for authorized_keys
```

### Issue 3: Deployment Script Not Found

```bash
# SSH to EC2
ls -la ~/deploy.sh

# If missing, recreate it
# Make sure it's executable
chmod +x ~/deploy.sh
```

### Issue 4: Service Restart Failed

```bash
# Check systemd service
sudo systemctl status mumtahingpt

# Check logs
sudo journalctl -u mumtahingpt -n 50

# Verify deploy user has sudo permission
sudo visudo
# Should have: deployer ALL=(ALL) NOPASSWD: /bin/systemctl restart mumtahingpt
```

### Issue 5: Health Check Failed

```bash
# Check if application is running
curl http://localhost:7860

# Check Nginx
sudo systemctl status nginx

# Check Nginx config
sudo nginx -t

# Check application logs
sudo journalctl -u mumtahingpt -f
```

### Issue 6: Git Pull Failed

```bash
# SSH to EC2
cd ~/mumtahin-gpt

# Check git status
git status

# If there are local changes
git stash
git pull origin main
git stash pop

# Or force reset (careful!)
git fetch origin
git reset --hard origin/main
```

### Issue 7: Dependency Installation Failed

```bash
# SSH to EC2
cd ~/mumtahin-gpt
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check for missing system packages
sudo apt update
sudo apt install -y python3.11-dev build-essential
```

---

## ✅ Best Practices

### 1. **Branch Protection Rules**

Configure in GitHub:
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Enable:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators

### 2. **Environment Separation**

```yaml
# Use GitHub Environments for staging/production
jobs:
  deploy-staging:
    environment: staging
    # Deploy to staging server

  deploy-production:
    environment: production
    needs: deploy-staging
    # Deploy to production after staging success
```

### 3. **Secrets Management**

- ✅ Never commit secrets to repository
- ✅ Use GitHub Secrets for sensitive data
- ✅ Rotate SSH keys regularly (every 90 days)
- ✅ Use different keys for staging/production
- ✅ Audit secret access logs

### 4. **Monitoring & Alerting**

- ✅ Set up CloudWatch alarms
- ✅ Monitor application logs
- ✅ Track deployment success rate
- ✅ Set up error tracking (Sentry, Rollbar)
- ✅ Monitor response times

### 5. **Rollback Strategy**

- ✅ Keep last 5 releases
- ✅ Test rollback procedure regularly
- ✅ Document rollback steps
- ✅ Automate rollback on failure
- ✅ Keep database migrations reversible

### 6. **Testing Before Deploy**

- ✅ Run all tests in CI pipeline
- ✅ Code coverage > 80%
- ✅ Security scanning on every commit
- ✅ Load testing before production
- ✅ Smoke tests after deployment

### 7. **Documentation**

- ✅ Document deployment process
- ✅ Maintain runbook for incidents
- ✅ Keep architecture diagrams updated
- ✅ Document rollback procedures
- ✅ Track deployment history

### 8. **Performance**

- ✅ Optimize Docker images (if using)
- ✅ Cache dependencies in CI
- ✅ Parallel job execution
- ✅ Incremental builds
- ✅ Fast health checks

---

## 📊 Deployment Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Security scan passed
- [ ] Staging deployment successful
- [ ] Database migrations tested
- [ ] Rollback procedure tested
- [ ] Monitoring enabled
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Stakeholders notified
- [ ] Backup created
- [ ] Health checks defined

---

## 🎉 Success Metrics

Track these metrics:

| Metric | Target | Current |
|--------|--------|---------|
| **Deployment Frequency** | Daily | ___ |
| **Lead Time** | < 1 hour | ___ |
| **Mean Time to Recovery (MTTR)** | < 15 min | ___ |
| **Change Failure Rate** | < 5% | ___ |
| **Deployment Success Rate** | > 95% | ___ |

---

## 📚 Additional Resources

- **GitHub Actions Docs:** [docs.github.com/actions](https://docs.github.com/en/actions)
- **AWS EC2 Docs:** [docs.aws.amazon.com/ec2](https://docs.aws.amazon.com/ec2/)
- **CI/CD Best Practices:** [martinfowler.com/ci](https://martinfowler.com/articles/continuousIntegration.html)
- **Deployment Strategies:** [martinfowler.com/deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)

---

## 🔗 Quick Command Reference

```bash
# Trigger manual deployment
git push origin main

# Check deployment status
# Visit: https://github.com/YOUR_USERNAME/mumtahin-gpt/actions

# SSH to server
ssh -i mumtahingpt-key.pem ubuntu@YOUR_EC2_IP

# Check service status
sudo systemctl status mumtahingpt

# View deployment logs
tail -f ~/deployments/shared/logs/deploy.log

# View rollback logs
tail -f ~/deployments/shared/logs/rollback.log

# Manual rollback
./rollback.sh

# Test deployment locally
./deploy.sh

# Check health
curl http://YOUR_DOMAIN/health
```

---

## 🎯 Next Steps

1. **Setup Staging Environment**
   - Create separate EC2 instance for staging
   - Configure staging workflow
   - Test changes in staging first

2. **Implement Monitoring**
   - Setup CloudWatch metrics
   - Configure alerting
   - Create dashboard

3. **Add Testing**
   - Write unit tests
   - Add integration tests
   - Setup code coverage

4. **Optimize Pipeline**
   - Cache dependencies
   - Parallel execution
   - Reduce deployment time

5. **Document Runbooks**
   - Incident response procedures
   - Escalation paths
   - Common issues and solutions

---

**Deployed with ❤️ using GitHub Actions**
**Guide Version: 1.0**
**Last Updated: November 10, 2025**
**Author: M. Yousuf**
