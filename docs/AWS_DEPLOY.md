# AWS Deployment Guide

## Quick Deploy

SSH into your EC2 instance and run:

```bash
cd /path/to/tn-electoral-search
./scripts/aws_deploy.sh
```

This script will automatically:
- ✅ Pull latest code from GitHub
- ✅ Update dependencies if needed
- ✅ Stop the current server
- ✅ Start the new server
- ✅ Perform health check

## First Time Setup

If this is your first deployment, you'll need to set up the server to run automatically.

### Option 1: Using systemd (Recommended)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/tn-electoral-search.service
```

Add this content (adjust paths):

```ini
[Unit]
Description=TN Electoral Search API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/tn-electoral-search
Environment="PATH=/home/ec2-user/tn-electoral-search/venv/bin"
ExecStart=/home/ec2-user/tn-electoral-search/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tn-electoral-search
sudo systemctl start tn-electoral-search
```

Check status:

```bash
sudo systemctl status tn-electoral-search
```

### Option 2: Manual Start

If you prefer to run manually:

```bash
cd /path/to/tn-electoral-search
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

## Environment Variables

Make sure these are set on your EC2 instance:

```bash
# Add to ~/.bashrc or /etc/environment
export GEMINI_API_KEY='your-api-key-here'  # Optional, can be session-based
```

## Security Group Settings

Ensure your EC2 security group allows inbound traffic on port 8000:

- Type: Custom TCP
- Port: 8000
- Source: 0.0.0.0/0 (or your specific IP range)

## Troubleshooting

### Check if server is running:
```bash
ps aux | grep uvicorn
```

### View logs:
```bash
# If using systemd:
sudo journalctl -u tn-electoral-search -f

# If manual start:
tail -f /path/to/tn-electoral-search/server.log
```

### Stop server:
```bash
# If using systemd:
sudo systemctl stop tn-electoral-search

# If manual:
pkill -f "uvicorn.*main:app"
```

### Check port 8000:
```bash
netstat -tuln | grep 8000
```

### Test health endpoint:
```bash
curl http://localhost:8000/api/health
```

## One-Line Deploy Command

For convenience, you can run deployment from anywhere:

```bash
ssh -i tn-electoral-search.pem ec2-user@YOUR-EC2-IP "cd /path/to/tn-electoral-search && ./scripts/aws_deploy.sh"
```

Or create an alias in your local machine:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias deploy-tn="ssh -i ~/path/to/tn-electoral-search.pem ec2-user@YOUR-EC2-IP 'cd /path/to/tn-electoral-search && ./scripts/aws_deploy.sh'"
```

Then just run:
```bash
deploy-tn
```
