# 🚀 Deploy TN Electoral Search - Quick Reference

Choose your platform and deploy in minutes!

---

## 🥇 Railway.app (5 minutes - RECOMMENDED)

**Best for**: Easy setup, SQLite persistence, always-on

```bash
# Already configured! Just deploy:
1. Go to: https://railway.app
2. Click "Deploy from GitHub repo"
3. Select: kbalakumar99/tn-electoral-search
4. Add Volume: Settings → Volumes → /app/database
5. Done! 🎉
```

**Cost**: FREE (~20 days 24/7) then $5/month

---

## 🥈 Fly.io (15 minutes - BEST HA)

**Best for**: Multi-region HA, stays free forever

```bash
# Install CLI
brew install flyctl

# Deploy
flyctl auth login
flyctl volumes create electoral_data --size 1 --region sin
flyctl deploy

# Get URL
flyctl info
```

**Cost**: FREE forever (3 VMs included)

---

## 🥉 Render.com (2 minutes - EASIEST)

**Best for**: Quick demos, prototypes

```bash
1. Go to: https://render.com
2. New + → Web Service → Connect GitHub
3. Build: pip install -r requirements.txt && python scripts/init_db.py
4. Start: python scripts/run_server.py
5. Done! 🎉
```

**Cost**: FREE (sleeps after 15min)

---

## ☁️ AWS EC2 (45 minutes - FULL CONTROL)

**Best for**: Learning AWS, full control

See full guide: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#option-3-aws-free-tier)

**Cost**: FREE (12 months), then ~$10/month

---

## 📚 Full Documentation

- **Complete Guide**: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Comparison**: [docs/HOSTING_COMPARISON.md](docs/HOSTING_COMPARISON.md)
- **Interactive Helper**: `./scripts/deploy_helper.sh`

---

## 🎯 Quick Decision

- **Want easiest?** → Railway.app
- **Want free forever?** → Fly.io
- **Want HA/multi-region?** → Fly.io
- **Prototyping only?** → Render.com
- **Learning AWS?** → AWS EC2

---

## 🆘 Need Help?

- Read: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- Run: `./scripts/deploy_helper.sh`
- Issues: [GitHub Issues](https://github.com/kbalakumar99/tn-electoral-search/issues)

---

**Recommended**: Start with Railway.app - easiest deployment! 🚀
