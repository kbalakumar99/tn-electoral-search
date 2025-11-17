# ⚡ AWS Quick Update

## 3 Simple Steps

### 1️⃣ Push to GitHub (Local Machine)
```bash
cd ~/ZC/POC/pdf-OCR-search/tn-electoral-search
git push origin main
```

### 2️⃣ SSH to AWS
```bash
ssh -i ~/tn-electoral-search.pem ec2-user@your-ec2-ip
```

### 3️⃣ Run Update Script
```bash
cd ~/tn-electoral-search && ./scripts/aws_deploy.sh
```

✅ **Done!** Your changes are live in ~30 seconds.

---

## 🔍 Verify Update

```bash
# Check server health
curl http://localhost:8000/api/health

# View logs
tail -f ~/tn-electoral-search/server.log
```

---

## 🆘 Quick Fixes

**Server not responding?**
```bash
sudo systemctl restart tn-electoral-search
```

**Manual restart needed?**
```bash
pkill -f "uvicorn.*main:app"
cd ~/tn-electoral-search
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

---

📖 **Full Guide:** [docs/AWS_UPDATE_GUIDE.md](docs/AWS_UPDATE_GUIDE.md)
