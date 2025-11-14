# 🚀 Deployment Guide: TN Electoral Search

Complete guide to deploy your application on free hosting platforms with High Availability (HA).

---

## 📊 **Application Requirements Analysis**

### Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLite (5.1 MB)
- **Frontend**: Embedded HTML/JavaScript (Single Page App)
- **Dependencies**: Lightweight (~50MB)

### Resource Needs
- **RAM**: ~512MB minimum
- **Storage**: ~100MB (app + database)
- **CPU**: 1 vCPU sufficient
- **Bandwidth**: Low (mostly static content + API calls)

---

## 🌟 **Recommended Free Hosting Options (Ranked)**

### 1. ⭐ **Railway.app** (BEST CHOICE)
- **Free Tier**: $5 monthly credit (500 hours runtime)
- **Features**: Auto-deploy from GitHub, SQLite persistent storage, HTTPS included
- **HA**: Good uptime, automatic restarts
- **Rating**: ⭐⭐⭐⭐⭐

### 2. **Render.com**
- **Free Tier**: 750 hours/month, sleeps after 15min inactivity
- **Features**: Auto-deploy, HTTPS, custom domains
- **HA**: Moderate (cold starts on inactivity)
- **Rating**: ⭐⭐⭐⭐

### 3. **Fly.io**
- **Free Tier**: 3 shared-cpu-1x VMs with 256MB RAM each
- **Features**: Global deployment, SQLite volumes, auto-scaling
- **HA**: Excellent (multi-region)
- **Rating**: ⭐⭐⭐⭐⭐

### 4. **AWS (Free Tier - Limited HA)**
- **Free Tier**: 12 months, t2.micro EC2 (1GB RAM)
- **Features**: Full control, persistent storage
- **HA**: Limited (single instance, requires setup)
- **Rating**: ⭐⭐⭐

### 5. **Google Cloud Run** (Pay-as-you-go, effectively free for low traffic)
- **Free Tier**: 2M requests/month, 360k GB-seconds
- **Features**: Serverless, auto-scaling, HTTPS
- **HA**: Excellent
- **Rating**: ⭐⭐⭐⭐

---

## 🏆 **OPTION 1: Railway.app (Easiest & Best for SQLite)**

### Why Railway?
✅ Best free tier for always-on apps  
✅ Native SQLite support with volumes  
✅ Zero cold starts  
✅ Auto-deploy from GitHub  
✅ No credit card for $5/month credit  

### Step-by-Step Deployment

#### **Step 1: Prepare Your Repository**

1. **Create `.railwayignore`** (optional):
```bash
cd /Users/bala-2082/ZC/POC/pdf-OCR-search/tn-electoral-search
cat > .railwayignore << 'EOF'
venv/
__pycache__/
*.pyc
.git/
tests/
docs/
.DS_Store
EOF
```

2. **Create `railway.json`** (Railway config):
```bash
cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python scripts/run_server.py",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF
```

3. **Update Dockerfile for Railway** (add volume mount):
```dockerfile
# Add this before CMD
VOLUME ["/app/database"]
```

4. **Commit changes**:
```bash
git add .
git commit -m "feat: Add Railway deployment config"
git push origin main
```

#### **Step 2: Deploy to Railway**

1. **Sign Up**: Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Login with GitHub

2. **Create New Project**:
   - Click "Deploy from GitHub repo"
   - Select `kbalakumar99/tn-electoral-search`
   - Railway auto-detects Dockerfile

3. **Configure Volume for SQLite**:
   - Go to your project → Settings → Volumes
   - Click "Add Volume"
   - Mount path: `/app/database`
   - Click "Add"

4. **Set Environment Variables** (if needed):
   - Go to Variables tab
   - Add any environment variables (GEMINI_API_KEY optional)

5. **Deploy**:
   - Railway automatically builds and deploys
   - Wait 3-5 minutes for first deployment

6. **Get Your URL**:
   - Go to Settings → Domains
   - Railway provides: `your-app.railway.app`
   - ✅ HTTPS enabled automatically!

#### **Step 3: Initialize Database** (First Time Only)

Railway runs `python scripts/init_db.py` during build (from Dockerfile).
Database persists on the volume.

#### **Step 4: Verify Deployment**

```bash
# Check health
curl https://your-app.railway.app/api/health

# Expected response:
# {
#   "status": "healthy",
#   "database": {
#     "districts": 29,
#     "constituencies": 197,
#     "polling_stations": 38397
#   }
# }
```

#### **Cost Estimate**:
- **Railway**: $5/month credit = ~500 hours = ~20 days of 24/7 runtime
- **If you need 24/7**: $5/month (very affordable)
- **If occasional use**: FREE (stays within credit)

---

## 🔥 **OPTION 2: Fly.io (Best for HA Multi-Region)**

### Why Fly.io?
✅ True multi-region deployment  
✅ 3 free VMs (HA out of the box)  
✅ SQLite + LiteFS for distributed SQLite  
✅ Zero cold starts  

### Step-by-Step Deployment

#### **Step 1: Install Fly CLI**

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
```

#### **Step 2: Login to Fly.io**

```bash
flyctl auth login
```

#### **Step 3: Create Fly App**

```bash
cd /Users/bala-2082/ZC/POC/pdf-OCR-search/tn-electoral-search

# Initialize Fly app
flyctl launch
```

**Answer prompts**:
- App name: `tn-electoral-search` (or auto-generate)
- Region: Choose closest to you (e.g., `sin` for Singapore)
- PostgreSQL: **No** (we use SQLite)
- Redis: **No**
- Deploy now: **No** (we'll configure first)

#### **Step 4: Configure `fly.toml`**

Fly creates `fly.toml`. Update it:

```toml
app = "tn-electoral-search"
primary_region = "sin"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[http_service.checks]]
  grace_period = "30s"
  interval = "15s"
  method = "GET"
  timeout = "5s"
  path = "/api/health"

[mounts]
  source = "electoral_data"
  destination = "/app/database"
```

#### **Step 5: Create Volume for SQLite**

```bash
# Create 1GB volume (free tier)
flyctl volumes create electoral_data --region sin --size 1
```

#### **Step 6: Deploy**

```bash
# Deploy to Fly.io
flyctl deploy

# Monitor deployment
flyctl logs
```

#### **Step 7: Scale for HA (Optional - uses more resources)**

```bash
# Add 2 more regions for HA (total 3 free VMs)
flyctl scale count 3 --region sin,hkg,bom
```

#### **Step 8: Get Your URL**

```bash
# Your app URL
flyctl info

# URL: https://tn-electoral-search.fly.dev
```

#### **Cost Estimate**:
- **Fly.io**: FREE for 3 VMs (256MB each)
- **Always-on**: Yes
- **HA**: Yes (multi-region if scaled)

---

## ☁️ **OPTION 3: AWS Free Tier (Traditional Hosting)**

### Why AWS?
✅ 12 months free  
✅ Full control (EC2 instance)  
✅ Good for learning AWS  
⚠️ Requires more setup  
⚠️ Limited HA (single instance)  

### Step-by-Step Deployment

#### **Step 1: Sign Up for AWS**

1. Go to [aws.amazon.com/free](https://aws.amazon.com/free)
2. Create account (requires credit card, but won't charge for free tier)
3. Verify email and phone

#### **Step 2: Launch EC2 Instance**

1. **Navigate to EC2**:
   - AWS Console → EC2 → Launch Instance

2. **Configure Instance**:
   - **Name**: `tn-electoral-search`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance Type**: `t2.micro` (1GB RAM, 1 vCPU) ✅ Free tier
   - **Key Pair**: Create new → Download `.pem` file (save securely!)
   - **Network Settings**:
     - ✅ Allow SSH (port 22) from My IP
     - ✅ Allow HTTP (port 80) from Anywhere
     - ✅ Allow HTTPS (port 443) from Anywhere
     - ✅ Allow Custom TCP (port 8000) from Anywhere
   - **Storage**: 8 GB gp3 (Free tier: 30GB)
   - Click "Launch Instance"

#### **Step 3: Connect to Instance**

```bash
# Set permissions on key file
chmod 400 ~/Downloads/tn-electoral-search.pem

# Connect via SSH (replace with your instance IP)
ssh -i ~/Downloads/tn-electoral-search.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
```

#### **Step 4: Install Dependencies on EC2**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git sqlite3 curl

# Install nginx (optional, for reverse proxy)
sudo apt install -y nginx
```

#### **Step 5: Clone and Setup Application**

```bash
# Clone repository
cd ~
git clone https://github.com/kbalakumar99/tn-electoral-search.git
cd tn-electoral-search

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py
```

#### **Step 6: Create Systemd Service (Auto-start on boot)**

```bash
# Create service file
sudo nano /etc/systemd/system/electoral-search.service
```

**Paste this configuration**:
```ini
[Unit]
Description=TN Electoral Search API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tn-electoral-search
Environment="PATH=/home/ubuntu/tn-electoral-search/venv/bin"
ExecStart=/home/ubuntu/tn-electoral-search/venv/bin/python /home/ubuntu/tn-electoral-search/scripts/run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable electoral-search
sudo systemctl start electoral-search
sudo systemctl status electoral-search
```

#### **Step 7: Configure Nginx Reverse Proxy (Optional but recommended)**

```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/electoral-search
```

**Paste this configuration**:
```nginx
server {
    listen 80;
    server_name <YOUR_EC2_PUBLIC_IP>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable configuration**:
```bash
sudo ln -s /etc/nginx/sites-available/electoral-search /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### **Step 8: Setup HTTPS with Let's Encrypt (Free SSL)**

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain or use IP)
# Note: Let's Encrypt doesn't work with IP addresses, you need a domain
# For now, use HTTP or buy a cheap domain

# If you have a domain:
sudo certbot --nginx -d yourdomain.com
```

#### **Step 9: Setup Firewall**

```bash
# Configure UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

#### **Step 10: Verify Deployment**

```bash
# Test locally
curl http://localhost:8000/api/health

# Test from outside (replace with your IP)
curl http://<YOUR_EC2_PUBLIC_IP>/api/health
```

#### **Step 11: Setup Automatic Updates (Optional)**

```bash
# Create update script
cat > ~/update-app.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/tn-electoral-search
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart electoral-search
EOF

chmod +x ~/update-app.sh
```

#### **Cost Estimate**:
- **AWS Free Tier**: FREE for 12 months
- **After 12 months**: ~$8-10/month (t2.micro)
- **Data Transfer**: 100GB/month free, then $0.09/GB

---

## 🌐 **OPTION 4: Render.com (Easiest Setup)**

### Quick Deploy (5 minutes)

#### **Step 1: Push to GitHub** (already done)

#### **Step 2: Deploy on Render**

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Connect `kbalakumar99/tn-electoral-search`
5. Configure:
   - **Name**: `tn-electoral-search`
   - **Region**: Choose closest
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt && python scripts/init_db.py`
   - **Start Command**: `python scripts/run_server.py`
   - **Plan**: Free
6. Click "Create Web Service"

#### **Limitation**: Sleeps after 15 min inactivity (wakes on request - 30s delay)

---

## 📋 **Comparison Table**

| Feature | Railway | Fly.io | AWS EC2 | Render | GCP Cloud Run |
|---------|---------|--------|---------|--------|---------------|
| **Always-On** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Sleeps | ✅ Yes |
| **SQLite Support** | ✅ Great | ✅ Great | ✅ Yes | ⚠️ Ephemeral | ❌ No |
| **Free Tier Duration** | Ongoing | Ongoing | 12 months | Ongoing | Ongoing |
| **Setup Difficulty** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐⭐⭐ Hard | ⭐ Easy | ⭐⭐ Medium |
| **HA Support** | ⚠️ Single | ✅ Multi-region | ❌ Single | ❌ Single | ✅ Auto-scale |
| **Cold Starts** | ❌ None | ❌ None | ❌ None | ✅ 30s | ✅ 2-5s |
| **Custom Domain** | ✅ Free | ✅ Free | ✅ Free | ✅ Free | ✅ Free |
| **HTTPS** | ✅ Auto | ✅ Auto | ⚠️ Manual | ✅ Auto | ✅ Auto |
| **Backup/Restore** | ⭐⭐ Manual | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Full | ⚠️ None | ⚠️ None |

---

## 🏆 **Final Recommendation**

### **For Your Use Case (SQLite + HA + Free):**

1. **Best Overall**: **Railway.app** ⭐⭐⭐⭐⭐
   - Easy setup, SQLite persistence, always-on
   - Deploy now: 10 minutes

2. **Best for HA**: **Fly.io** ⭐⭐⭐⭐⭐
   - Multi-region, 3 free VMs, true HA
   - Deploy now: 15 minutes

3. **Budget After 12 Months**: **Railway** ($5/month)

---

## 🚀 **Quick Start Recommendation**

**Start with Railway.app** (5 minutes):
```bash
cd /Users/bala-2082/ZC/POC/pdf-OCR-search/tn-electoral-search

# Create Railway config
cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python scripts/run_server.py",
    "healthcheckPath": "/api/health"
  }
}
EOF

# Commit and push
git add railway.json
git commit -m "Add Railway deployment config"
git push origin main

# Then:
# 1. Go to railway.app
# 2. Sign in with GitHub
# 3. Deploy from repo
# 4. Add volume at /app/database
# 5. Done! 🎉
```

---

## 📞 **Support & Troubleshooting**

### Common Issues:

**Database not persisting:**
- Ensure volume is mounted correctly
- Check write permissions on `/app/database`

**Cold starts:**
- Use Railway or Fly.io (no cold starts)
- Or: Implement external health check ping

**Out of memory:**
- Railway/Fly: 512MB is enough
- AWS: t2.micro (1GB) is sufficient

---

## 📚 **Next Steps**

After deployment:
1. ✅ Test all features
2. ✅ Setup monitoring (UptimeRobot - free)
3. ✅ Configure custom domain (optional)
4. ✅ Setup backups (download SQLite file periodically)
5. ✅ Close GitHub Issue #1 (API key feature)

---

**Need help?** Open an issue on GitHub!

**Ready to deploy?** Choose Railway.app and follow the quick start above! 🚀
