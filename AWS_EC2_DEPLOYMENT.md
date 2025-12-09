# 🚀 AWS EC2 Deployment Guide - MumtahinGPT

Complete guide to deploy MumtahinGPT on AWS EC2 with custom domain, SSL certificate, and public accessibility.

**Note:** This guide is configured for **v2_rag** (RAG-based version with ChromaDB) by default. 
For **v1_basic** deployment instructions, see comments marked with `# For v1_basic`.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [EC2 Instance Creation](#ec2-instance-creation)
4. [Server Configuration](#server-configuration)
5. [Application Deployment](#application-deployment)
6. [Nginx Configuration](#nginx-configuration)
7. [Domain Configuration](#domain-configuration)
8. [SSL Certificate Setup](#ssl-certificate-setup)
9. [Firewall & Security](#firewall--security)
10. [Process Management](#process-management)
11. [Monitoring & Maintenance](#monitoring--maintenance)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 Prerequisites

Before starting, ensure you have:

- ✅ AWS Account with billing enabled
- ✅ Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- ✅ Domain name (from GoDaddy, Namecheap, Route53, etc.)
- ✅ Basic Linux command line knowledge
- ✅ SSH client (Terminal on Mac/Linux, PuTTY on Windows)
- ✅ Credit card for AWS billing (Free tier available)

**Estimated Costs:**
- EC2 Instance (t2.medium): ~$30-40/month (or free tier t2.micro)
- Elastic IP: Free (if attached to running instance)
- Domain: ~$10-15/year
- SSL Certificate: Free (Let's Encrypt)

---

## 🔐 AWS Account Setup

### Step 1: Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Fill in:
   - Email address
   - Password
   - Account name
4. Enter contact information
5. Add payment method (credit card)
6. Verify identity (phone verification)
7. Select support plan: **Basic (Free)**
8. Complete registration

### Step 2: Enable MFA (Security Best Practice)

1. Sign in to AWS Console
2. Click your account name (top right) → Security Credentials
3. Under "Multi-factor authentication (MFA)" → Activate MFA
4. Choose:
   - **Virtual MFA device** (Google Authenticator, Authy)
   - Follow setup wizard
5. Scan QR code with authenticator app
6. Enter two consecutive MFA codes
7. Click "Assign MFA"

### Step 3: Create IAM User (Best Practice)

1. Go to **IAM** service in AWS Console
2. Click **Users** → **Add users**
3. User name: `mumtahingpt-admin`
4. Access type: 
   - ✅ **Programmatic access** (for CLI)
   - ✅ **AWS Management Console access**
5. Set password → Custom password → Require password reset: No
6. Attach policies:
   - ✅ **AdministratorAccess** (or EC2FullAccess for limited access)
7. Click **Create user**
8. **Download credentials CSV** (save securely!)
9. Sign out and sign in as new IAM user

---

## 🖥️ EC2 Instance Creation

### Step 1: Launch EC2 Instance

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. Go to **EC2** service (search in top bar)
3. Click **Launch Instance**

### Step 2: Configure Instance

**Name and Tags:**
```
Name: mumtahingpt-production
Environment: Production
Application: MumtahinGPT
```

**Application and OS Images:**
- **Quick Start**: Ubuntu
- **AMI**: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
- **Architecture**: 64-bit (x86)

**Instance Type:**

**Option 1: Free Tier (Limited)**
```
Instance: t2.micro
vCPUs: 1
Memory: 1 GiB
Good for: Testing, light usage
Cost: Free (750 hours/month for 12 months)
```

**Option 2: Recommended (Production)**
```
Instance: t2.medium
vCPUs: 2
Memory: 4 GiB
Good for: Production, multiple users
Cost: ~$0.0464/hour (~$33/month)
```

**Option 3: High Performance**
```
Instance: t3.large
vCPUs: 2
Memory: 8 GiB
Good for: Heavy usage, fast response
Cost: ~$0.0832/hour (~$60/month)
```

**Key Pair (Login):**
1. Click **Create new key pair**
2. Key pair name: `mumtahingpt-key`
3. Key pair type: **RSA**
4. Private key file format: 
   - **Linux/Mac**: `.pem`
   - **Windows (PuTTY)**: `.ppk`
5. Click **Create key pair**
6. **Save the downloaded file securely** (you can't download it again!)

**Network Settings:**
1. Click **Edit**
2. **VPC**: Default VPC (or create new)
3. **Subnet**: No preference (or select specific AZ)
4. **Auto-assign public IP**: **Enable**

**Firewall (Security Groups):**

Create security group: `mumtahingpt-sg`

Add inbound rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | My IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0, ::/0 | Web traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0, ::/0 | Secure web traffic |
| Custom TCP | TCP | 7860 | 0.0.0.0/0, ::/0 | Gradio app (temporary) |

**Configure Storage:**
```
Volume Type: gp3 (General Purpose SSD)
Size: 20 GiB (minimum) - 30 GiB recommended
Delete on termination: Yes (or No to preserve data)
```

**Advanced Details:**
- Leave defaults (or customize as needed)

### Step 3: Launch Instance

1. Review all settings
2. Click **Launch Instance**
3. Wait 2-3 minutes for instance to start
4. Status should show: ✅ **Running**

### Step 4: Allocate Elastic IP (Static IP)

**Why do we need Elastic IP?**

When you create an EC2 instance, AWS assigns a **public IP automatically**, BUT this IP **changes every time** you stop/start the instance. This breaks your domain configuration and causes downtime.

**Comparison:**

| Feature | Regular Public IP | Elastic IP |
|---------|------------------|------------|
| **Permanence** | ❌ Changes on stop/start | ✅ Never changes |
| **Domain Stability** | ❌ Must update DNS | ✅ Set once, works forever |
| **Cost (Running)** | Free | Free |
| **Cost (Stopped)** | IP Lost | $0.005/hr (~$3.60/month) |
| **Use Case** | Testing only | Production ✅ |

**For production with custom domain, Elastic IP is REQUIRED.**

**Steps:**

1. In EC2 Dashboard → **Elastic IPs** (left menu)
2. Click **Allocate Elastic IP address**
3. Network Border Group: Default
4. Click **Allocate**
5. Select the new Elastic IP
6. Click **Actions** → **Associate Elastic IP address**
7. Select your instance: `mumtahingpt-production`
8. Click **Associate**

**Note:** Elastic IP is free when associated with a running instance, but costs money if unused!

---

## 🔌 Connect to EC2 Instance

### Method 1: SSH from Linux/Mac Terminal

1. **Set correct permissions** for key file:
```bash
chmod 400 ~/Downloads/mumtahingpt-key.pem
```

2. **Connect via SSH:**
```bash
ssh -i ~/Downloads/mumtahingpt-key.pem ubuntu@YOUR_ELASTIC_IP
```

Replace `YOUR_ELASTIC_IP` with your actual Elastic IP (e.g., `54.123.45.67`)

3. Type `yes` when prompted about fingerprint

### Method 2: SSH from Windows (PuTTY)

1. **Download PuTTY**: [putty.org](https://www.putty.org/)
2. **Open PuTTYgen** (comes with PuTTY)
3. Click **Load** → Select your `.ppk` file (or convert `.pem` to `.ppk`)
4. **Open PuTTY**
5. Enter:
   - Host Name: `ubuntu@YOUR_ELASTIC_IP`
   - Port: `22`
6. In left menu: **Connection** → **SSH** → **Auth**
7. Browse and select your `.ppk` key file
8. Click **Open**
9. Click **Yes** to accept server key

### Method 3: EC2 Instance Connect (Browser)

1. In EC2 Dashboard → **Instances**
2. Select your instance
3. Click **Connect** button (top)
4. Select **EC2 Instance Connect** tab
5. Click **Connect** (opens browser terminal)

**You should now see:**
```bash
ubuntu@ip-172-31-xx-xx:~$
```

---

## ⚙️ Server Configuration

### Step 1: Update System

```bash
# Update package lists
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential curl wget git vim ufw
```

### Step 2: Install Python 3.11

```bash
# Add deadsnakes PPA for latest Python
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Install pip
sudo apt install -y python3-pip

# Verify installation
python3.11 --version  # Should show Python 3.11.x
```

### Step 3: Install Nginx (Web Server)

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx  # Should show "active (running)"

# Test in browser: http://YOUR_ELASTIC_IP
# You should see "Welcome to nginx!" page
```

### Step 4: Install Certbot (SSL Certificates)

```bash
# Install Certbot and Nginx plugin
sudo apt install -y certbot python3-certbot-nginx
```

---

## 📦 Application Deployment

### Step 1: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository (replace with your GitHub URL)
git clone https://github.com/yousuf-git/mumtahin-gpt.git
cd mumtahin-gpt

# The repository contains two versions:
# - v1_basic/ (Basic version without RAG)
# - v2_rag/ (RAG-based version with ChromaDB - RECOMMENDED)

# Or upload files manually:
# Use SCP from your local machine:
# scp -i mumtahin-key.pem -r /path/to/mumtahin-gpt ubuntu@YOUR_ELASTIC_IP:~/
```

### Step 2: Setup Application

```bash
# ========================================
# MAIN VERSION: v2_rag (RAG-based with ChromaDB)
# ========================================
# Navigate to v2_rag directory
cd ~/mumtahin-gpt/v2_rag

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
cd ..
pip install -r requirements.txt

# This will install (v2_rag includes additional RAG dependencies):
# - gradio==4.19.2
# - google-generativeai==0.8.2
# - PyMuPDF==1.24.10
# - pdfplumber==0.11.4
# - python-dotenv==1.0.1
# - reportlab==4.0.7
# - chromadb==0.4.24 (for RAG)
# - sentence-transformers==2.3.1 (for embeddings)

# ========================================
# ALTERNATIVE: v1_basic (Basic version without RAG)
# ========================================
# If you prefer the basic version without RAG:
# cd ~/mumtahin-gpt/v1_basic
# python3.11 -m venv venv
# source venv/bin/activate
# pip install --upgrade pip
# cd ..
# pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

```bash
# Create .env file
nano .env

# Add your Gemini API key:
GEMINI_API_KEY=your_actual_api_key_here

# Save and exit (Ctrl+X, then Y, then Enter)

# Secure the file
chmod 600 .env
```

### Step 4: Test Application

```bash
# ========================================
# For v2_rag (RAG-based version)
# ========================================
# Make sure you're in the v2_rag directory with venv activated
cd ~/mumtahin-gpt/v2_rag
source venv/bin/activate

# Run the application
python3 app.py

# You should see:
# ✅ Application initialized successfully with RAG support!
# 🔍 RAG system initialized with ChromaDB
# Running on local URL:  http://0.0.0.0:7860

# ========================================
# For v1_basic (Basic version)
# ========================================
# cd ~/mumtahin-gpt/v1_basic
# source venv/bin/activate
# python3 app.py
```

**Test in browser:** `http://YOUR_ELASTIC_IP:7860`

**Stop the application:** Press `Ctrl+C`

---

## 🌐 Nginx Configuration (Reverse Proxy)

### Step 1: Create Nginx Configuration

```bash
# Create new Nginx site configuration
sudo nano /etc/nginx/sites-available/mumtahingpt
```

**Add the following configuration:**

```nginx
# Basic configuration without SSL (we'll add SSL later)
server {
    listen 80;
    listen [::]:80;
    
    server_name your-domain.com www.your-domain.com;
    
    # Increase timeouts for AI processing
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;
    
    # Max upload size for PDFs
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Disable buffering for streaming
        proxy_buffering off;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

**Replace `your-domain.com` with your actual domain!**

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

### Step 2: Enable the Site

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/mumtahingpt /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Should show:
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload Nginx
sudo systemctl reload nginx
```

---

## 🌍 Domain Configuration

### Step 1: Configure DNS Records

Go to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.) and add these DNS records:

**Option 1: Using Cloudflare (Recommended)**

1. Sign up at [cloudflare.com](https://cloudflare.com)
2. Add your domain
3. Update nameservers at your registrar
4. In Cloudflare DNS settings, add:

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | @ | YOUR_ELASTIC_IP | Proxied | Auto |
| A | www | YOUR_ELASTIC_IP | Proxied | Auto |

**Option 2: Direct DNS (Without Cloudflare)**

At your domain registrar's DNS settings:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_ELASTIC_IP | 3600 |
| A | www | YOUR_ELASTIC_IP | 3600 |

**Example for GoDaddy:**
1. Log in to GoDaddy
2. Go to **My Products** → **Domains**
3. Click **DNS** next to your domain
4. Add/Edit A records as above

**DNS Propagation:**
- Wait 5-60 minutes for DNS to propagate
- Check status: [whatsmydns.net](https://whatsmydns.net)

### Step 2: Verify Domain Resolution

```bash
# Test DNS resolution
ping your-domain.com

# Should show your Elastic IP
# Press Ctrl+C to stop

# Test with nslookup
nslookup your-domain.com

# Should return your Elastic IP
```

---

## 🔒 SSL Certificate Setup (HTTPS)

### Step 1: Obtain SSL Certificate with Certbot

```bash
# Make sure Nginx is running
sudo systemctl status nginx

# Run Certbot
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts:
# 1. Enter email address for urgent renewal notices
# 2. Agree to Terms of Service: Yes (Y)
# 3. Share email with EFF: Your choice (Y/N)
# 4. Redirect HTTP to HTTPS: Yes (option 2) - RECOMMENDED

# Certbot will automatically:
# - Obtain certificate from Let's Encrypt
# - Update Nginx configuration
# - Add HTTPS redirect
# - Setup auto-renewal
```

### Step 2: Test SSL Certificate

**Visit:** `https://your-domain.com`

You should see:
- ✅ Padlock icon in browser
- ✅ "Connection is secure"
- ✅ Your Examiner AI application

**Test SSL Grade:** [ssllabs.com/ssltest](https://www.ssllabs.com/ssltest/)

### Step 3: Auto-Renewal

```bash
# Certbot automatically sets up renewal
# Test renewal process (dry run)
sudo certbot renew --dry-run

# Should show: "Congratulations, all simulated renewals succeeded"

# Check renewal timer
sudo systemctl status certbot.timer

# Should show "active (waiting)"
```

**Certificates auto-renew every 60 days.**

---

## 🔥 Firewall & Security Configuration

### Step 1: Configure UFW (Uncomplicated Firewall)

```bash
# Check UFW status
sudo ufw status

# Configure firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Type 'y' to confirm

# Verify rules
sudo ufw status verbose

# Should show:
# Status: active
# To                         Action      From
# --                         ------      ----
# 22/tcp                     ALLOW       Anywhere
# 80/tcp                     ALLOW       Anywhere
# 443/tcp                    ALLOW       Anywhere
```

### Step 2: Update EC2 Security Group

Go back to AWS Console:

1. **EC2** → **Security Groups**
2. Select `mumtahingpt-sg`
3. **Inbound rules** → **Edit inbound rules**
4. **Remove or restrict port 7860** (no longer needed, using Nginx)
5. Keep only:
   - SSH (22) from Your IP
   - HTTP (80) from anywhere
   - HTTPS (443) from anywhere
6. Click **Save rules**

### Step 3: Additional Security Hardening

```bash
# Disable root login
sudo nano /etc/ssh/sshd_config

# Find and set:
PermitRootLogin no
PasswordAuthentication no

# Save and restart SSH
sudo systemctl restart sshd

# Install fail2ban (prevents brute force attacks)
sudo apt install -y fail2ban

# Enable and start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status
```

---

## 🔄 Process Management (Keep App Running)

### Method 1: Systemd Service (Recommended)

Create a systemd service to run the application automatically:

```bash
# Create service file
sudo nano /etc/systemd/system/mumtahingpt.service
```

**Add the following (for v2_rag):**

```ini
[Unit]
Description=MumtahinGPT - AI-Powered Document Examiner with RAG
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mumtahin-gpt/v2_rag
Environment="PATH=/home/ubuntu/mumtahin-gpt/v2_rag/venv/bin"
ExecStart=/home/ubuntu/mumtahin-gpt/v2_rag/venv/bin/python3 /home/ubuntu/mumtahin-gpt/v2_rag/app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/mumtahingpt/output.log
StandardError=append:/var/log/mumtahingpt/error.log

[Install]
WantedBy=multi-user.target
```

**For v1_basic (alternative):**
```ini
# Change WorkingDirectory to: /home/ubuntu/mumtahin-gpt/v1_basic
# Change Environment PATH to: /home/ubuntu/mumtahin-gpt/v1_basic/venv/bin
# Change ExecStart to: /home/ubuntu/mumtahin-gpt/v1_basic/venv/bin/python3 /home/ubuntu/mumtahin-gpt/v1_basic/app.py
```

Save and exit: `Ctrl+X`, `Y`, `Enter`

**Setup logging and start service:**

```bash
# Create log directory
sudo mkdir -p /var/log/mumtahingpt
sudo chown ubuntu:ubuntu /var/log/mumtahingpt

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable mumtahingpt

# Start service
sudo systemctl start mumtahingpt

# Check status
sudo systemctl status mumtahingpt

# Should show: "active (running)"
# For v2_rag, you should see: "RAG system initialized with ChromaDB"

# View logs
sudo tail -f /var/log/mumtahingpt/output.log

# Stop service (if needed)
# sudo systemctl stop mumtahingpt

# Restart service (after updates)
# sudo systemctl restart mumtahingpt
```

### Method 2: Screen (Simple Alternative)

```bash
# Install screen
sudo apt install -y screen

# Create a new screen session
screen -S mumtahingpt

# Navigate to project and run (v2_rag)
cd ~/mumtahin-gpt/v2_rag
source venv/bin/activate
python3 app.py

# You should see:
# ✅ Application initialized successfully with RAG support!
# 🔍 RAG system initialized with ChromaDB

# Detach from screen: Press Ctrl+A, then D

# Reattach to screen
screen -r mumtahingpt

# List all screens
screen -ls

# Kill screen session
# screen -X -S mumtahingpt quit
```

### Verify Application is Running

```bash
# Check if app is running on port 7860
sudo netstat -tulpn | grep 7860

# Test locally
curl http://localhost:7860

# Should return HTML content

# Test domain
curl https://your-domain.com

# Should return HTML content
```

---

## 📊 Monitoring & Maintenance

### Monitor System Resources

```bash
# Check CPU, memory, disk usage
htop

# If not installed:
sudo apt install -y htop

# Check disk space
df -h

# Check memory
free -h

# Monitor in real-time
watch -n 5 'free -h && df -h'
```

### Monitor Application Logs

```bash
# Systemd service logs
sudo journalctl -u mumtahingpt -f

# Application logs
sudo tail -f /var/log/mumtahingpt/output.log
sudo tail -f /var/log/mumtahingpt/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Setup Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/mumtahingpt
```

**Add:**

```
/var/log/mumtahingpt/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 ubuntu ubuntu
}
```

### Automated Backups

```bash
# Create backup script
nano ~/backup-mumtahingpt.sh
```

**Add:**

```bash
#!/bin/bash
# MumtahinGPT Backup Script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups"
APP_DIR="/home/ubuntu/mumtahin-gpt"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application files and .env
# For v2_rag (includes both versions)
tar -czf $BACKUP_DIR/mumtahingpt-$DATE.tar.gz \
    -C $APP_DIR \
    --exclude='v1_basic/venv' \
    --exclude='v2_rag/venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    .

# Keep only last 7 backups
ls -t $BACKUP_DIR/mumtahingpt-*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: mumtahingpt-$DATE.tar.gz"
```

**Make executable and schedule:**

```bash
# Make executable
chmod +x ~/backup-mumtahingpt.sh

# Add to crontab (daily at 2 AM)
crontab -e

# Add this line:
0 2 * * * /home/ubuntu/backup-mumtahingpt.sh >> /var/log/backup.log 2>&1

# Save and exit
```

### Update Application

```bash
# Stop service
sudo systemctl stop mumtahingpt

# Navigate to project root
cd ~/mumtahin-gpt

# Pull latest changes
git pull origin main

# For v2_rag (default):
cd v2_rag
source venv/bin/activate

# Update dependencies (from root)
cd ..
pip install -r requirements.txt --upgrade

# For v1_basic:
# cd v1_basic
# source venv/bin/activate
# cd ..
# pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl start mumtahingpt

# Check status
sudo systemctl status mumtahingpt

# Verify RAG initialization (v2_rag)
sudo journalctl -u mumtahingpt -n 20 | grep "RAG"
```

---

## 🐛 Troubleshooting

### Issue 1: Application Not Starting

```bash
# Check service status
sudo systemctl status mumtahingpt

# View recent logs
sudo journalctl -u mumtahingpt -n 50

# Check if port 7860 is in use
sudo netstat -tulpn | grep 7860

# Kill process using port (if needed)
sudo kill -9 $(sudo lsof -t -i:7860)

# For v2_rag, check ChromaDB initialization
sudo journalctl -u mumtahingpt | grep "ChromaDB"

# Restart service
sudo systemctl restart mumtahingpt
```

### Issue 2: 502 Bad Gateway

```bash
# Application not running
sudo systemctl restart mumtahingpt

# Check Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Issue 3: SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Test Nginx SSL configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Issue 4: High Memory Usage

```bash
# Check memory
free -h

# Check processes
htop

# For v2_rag, ChromaDB collections consume memory
# Check application logs for collection cleanup
sudo journalctl -u mumtahingpt | grep "collection"

# Restart application (clears in-memory ChromaDB)
sudo systemctl restart mumtahingpt

# Memory recommendations:
# v1_basic: 1GB RAM minimum (t2.micro)
# v2_rag: 2GB RAM minimum (t2.small), 4GB recommended (t2.medium)

# Consider upgrading to larger instance if consistently high
```

### Issue 5: ImportError with HuggingFace Hub

**Error:** `ImportError: cannot import name 'HfFolder' from 'huggingface_hub'`

**Cause:** Version incompatibility between Gradio 4.19.2 and newer HuggingFace Hub

**Solution:**

```bash
# Activate virtual environment (v2_rag or v1_basic)
cd ~/mumtahin-gpt/v2_rag  # or v1_basic
source venv/bin/activate

# Downgrade to compatible version
pip install huggingface_hub==0.19.4

# Restart application
sudo systemctl restart mumtahingpt

# Verify
sudo systemctl status mumtahingpt
```

### Issue 6: "gradio is not installed" with python3

**Cause:** Using system Python instead of venv Python

**Solution:**

```bash
# Always activate venv first (v2_rag or v1_basic)
cd ~/mumtahin-gpt/v2_rag  # or v1_basic
source venv/bin/activate

# Use python3.11 (not python3)
python3.11 app.py

# Or use systemd service (recommended)
sudo systemctl start mumtahingpt
```

### Issue 7: Can't Connect via SSH

```bash
### Issue 7: Can't Connect via SSH

```bash
# From AWS Console:
# 1. EC2 → Instances → Select instance
# 2. Actions → Monitor and troubleshoot → Get system log
# 3. Check for errors

# Verify security group allows SSH from your IP
# Verify key file permissions: chmod 400 mumtahingpt-key.pem
# Try EC2 Instance Connect from AWS Console
```

### Issue 8: Domain Not Resolving
```

### Issue 6: Domain Not Resolving

```bash
# Check DNS propagation
ping your-domain.com

# Check nameservers
nslookup your-domain.com

# Wait 30-60 minutes for DNS propagation
# Use https://whatsmydns.net to check globally
```

---

## 📈 Performance Optimization

### Enable Gzip Compression

```bash
sudo nano /etc/nginx/nginx.conf

# Add in http block:
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
```

### Enable Caching

```bash
sudo nano /etc/nginx/sites-available/mumtahingpt

# Add in server block:
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### Increase Instance Resources (if needed)

1. AWS Console → EC2 → Instances
2. Select instance → Actions → Instance state → Stop
3. Actions → Instance settings → Change instance type
4. Select larger type (e.g., t2.medium → t2.large)
5. Start instance

---

## 💰 Cost Optimization

### Tips to Reduce Costs:

1. **Use t2.micro** for free tier (first 12 months)
2. **Stop instance** when not in use (billed only when running)
3. **Use Reserved Instances** for 1-3 year commitment (up to 75% savings)
4. **Set up billing alerts** in AWS Console
5. **Release unused Elastic IPs** (costs money if not attached)
6. **Use Cloudflare** for free CDN and DDoS protection
7. **Monitor usage** with AWS Cost Explorer

### Setup Billing Alarm:

1. AWS Console → CloudWatch → Alarms
2. Create alarm → Select metric → Billing
3. Set threshold (e.g., $10)
4. Create SNS topic for email notification
5. Receive alerts when threshold exceeded

---

## ✅ Final Checklist

After completing all steps, verify:

- [ ] EC2 instance is running
- [ ] Elastic IP is associated
- [ ] Application service is active: `sudo systemctl status mumtahingpt`
- [ ] Nginx is running: `sudo systemctl status nginx`
- [ ] Domain resolves to your IP: `ping your-domain.com`
- [ ] HTTPS works: `https://your-domain.com` shows padlock
- [ ] Can upload PDF and get questions
- [ ] Can export PDF reports
- [ ] **RAG system initialized (v2_rag):** Check logs for "ChromaDB" message
- [ ] **Chunking progress displays (v2_rag):** Verify during PDF upload
- [ ] Firewall is configured: `sudo ufw status`
- [ ] Auto-start is enabled: `sudo systemctl is-enabled mumtahingpt`
- [ ] SSL auto-renewal is configured: `sudo certbot renew --dry-run`
- [ ] Backups are scheduled: `crontab -l`
- [ ] Monitoring logs: `sudo tail -f /var/log/mumtahingpt/output.log`

---

## 🎉 Success!

Your MumtahinGPT is now:
- ✅ Running on AWS EC2
- ✅ **RAG-enabled for large documents (v2_rag)**
- ✅ Accessible via custom domain with HTTPS
- ✅ Protected by firewall
- ✅ Auto-starting on boot
- ✅ Auto-renewing SSL certificates
- ✅ Backed up daily
- ✅ Production-ready!

**Version deployed:**
- **v2_rag:** Advanced RAG-based examination with ChromaDB (recommended)
- **v1_basic:** Basic version for quick exams (see comments for setup)

**Access your application:**
- **URL:** `https://your-domain.com`
- **Admin:** SSH to `ubuntu@your-domain.com` or `ubuntu@YOUR_ELASTIC_IP`

---

## 📞 Support Resources

- **AWS Documentation:** [docs.aws.amazon.com](https://docs.aws.amazon.com)
- **Nginx Documentation:** [nginx.org/en/docs](https://nginx.org/en/docs/)
- **Certbot Documentation:** [certbot.eff.org](https://certbot.eff.org/)
- **Ubuntu Documentation:** [help.ubuntu.com](https://help.ubuntu.com/)

---

## 📝 Quick Reference Commands

```bash
# Service management
sudo systemctl start mumtahingpt
sudo systemctl stop mumtahingpt
sudo systemctl restart mumtahingpt
sudo systemctl status mumtahingpt

# View logs
sudo journalctl -u mumtahingpt -f
sudo tail -f /var/log/mumtahingpt/output.log

# Check RAG initialization (v2_rag)
sudo journalctl -u mumtahingpt | grep "RAG\|ChromaDB"

# Nginx management
sudo systemctl restart nginx
sudo nginx -t
sudo tail -f /var/log/nginx/error.log

# SSL management
sudo certbot certificates
sudo certbot renew
sudo certbot renew --dry-run

# Firewall
sudo ufw status
sudo ufw allow 443/tcp
sudo ufw reload

# System monitoring
htop
df -h
free -h

# Update application
cd ~/mumtahin-gpt && git pull && sudo systemctl restart mumtahingpt
```

---

**Deployed with ❤️ on AWS EC2**
**Project:** MumtahinGPT (github.com/yousuf-git/mumtahin-gpt)
**Guide Version: 2.0 (RAG Edition)**
**Last Updated: December 9, 2025**
