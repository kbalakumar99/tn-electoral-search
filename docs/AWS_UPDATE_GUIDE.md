# Simple AWS Update Guide

## 🚀 Quick Update (3 Steps)

### Step 1: Push Your Code to GitHub
```bash
# On your local machine
cd /Users/bala-2082/ZC/POC/pdf-OCR-search/tn-electoral-search
git push origin main
```

### Step 2: SSH into AWS EC2
```bash
ssh -i ~/path/to/your-key.pem ec2-user@your-ec2-ip-address
```

### Step 3: Run Deployment Script
```bash
cd ~/tn-electoral-search
./scripts/aws_deploy.sh
```

That's it! ✅ The script automatically:
- Pulls latest code from GitHub
- Updates dependencies if needed
- Restarts the server
- Performs health check

---

## 📋 Manual Update (If Script Fails)

### Step 1: SSH into EC2
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

### Step 2: Navigate to Project
```bash
cd ~/tn-electoral-search
```

### Step 3: Pull Latest Code
```bash
git pull origin main
```

### Step 4: Restart Server

**If using systemd:**
```bash
sudo systemctl restart tn-electoral-search
sudo systemctl status tn-electoral-search
```

**If running manually:**
```bash
# Stop server
pkill -f "uvicorn.*main:app"

# Start server
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Step 5: Verify
```bash
curl http://localhost:8000/api/health
```

---

## 🔧 Troubleshooting

### Check Server Status
```bash
# If using systemd
sudo systemctl status tn-electoral-search

# If manual
ps aux | grep uvicorn
```

### View Logs
```bash
# systemd logs
sudo journalctl -u tn-electoral-search -n 50 -f

# Manual logs
tail -f ~/tn-electoral-search/server.log
```

### Server Not Starting?
```bash
# Check port 8000 is free
sudo lsof -i :8000

# Kill any process using port 8000
sudo kill -9 $(sudo lsof -t -i:8000)

# Try starting again
cd ~/tn-electoral-search
./scripts/aws_deploy.sh
```

### Dependencies Issues?
```bash
cd ~/tn-electoral-search
source venv/bin/activate
pip install -r requirements-full.txt
```

---

## 🎯 Common Scenarios

### Scenario 1: Just Code Changes (HTML/CSS/Python)
```bash
ssh ec2-user@your-ec2-ip
cd ~/tn-electoral-search
./scripts/aws_deploy.sh
```
⏱️ Time: ~30 seconds

### Scenario 2: New Python Dependencies Added
```bash
ssh ec2-user@your-ec2-ip
cd ~/tn-electoral-search
git pull origin main
source venv/bin/activate
pip install -r requirements-full.txt
sudo systemctl restart tn-electoral-search
```
⏱️ Time: ~2 minutes

### Scenario 3: Major Changes (Database Schema, etc.)
```bash
ssh ec2-user@your-ec2-ip
cd ~/tn-electoral-search
git pull origin main

# Backup database
cp electoral_data.db electoral_data.db.backup

# Update dependencies
source venv/bin/activate
pip install -r requirements-full.txt

# Run migrations if any
# python migrations/migrate.py

# Restart
sudo systemctl restart tn-electoral-search
```
⏱️ Time: ~3-5 minutes

---

## 📊 Verify Update Success

### 1. Check Server is Running
```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"healthy",...}`

### 2. Access Web Interface
Open in browser: `http://your-ec2-ip:8000`

### 3. Check for Your Changes
- For UI changes: Look for the purple notice box at the top
- For backend changes: Test the affected functionality

---

## 🔐 Security Note

**Keep your `.pem` key secure:**
```bash
chmod 400 ~/path/to/your-key.pem
```

---

## 💡 Pro Tips

1. **Always test locally first** before pushing to AWS
2. **Check logs immediately** after deployment
3. **Keep a backup** of your database before major updates
4. **Use screen/tmux** for long-running operations
5. **Monitor logs** during first few minutes after update

---

## 🆘 Need Help?

### Full Deployment Guide
See: `docs/AWS_DEPLOY.md`

### First Time Setup
See: `docs/DEPLOYMENT_GUIDE.md`

### Automated Script
Location: `scripts/aws_deploy.sh`
