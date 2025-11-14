#!/bin/bash
# Quick deployment helper script

echo "🚀 TN Electoral Search - Deployment Helper"
echo "=========================================="
echo ""

PS3="Choose deployment platform: "
options=("Railway.app" "Fly.io" "Render.com" "AWS EC2" "Exit")

select opt in "${options[@]}"
do
    case $opt in
        "Railway.app")
            echo ""
            echo "📦 Railway.app Deployment"
            echo "========================"
            echo ""
            echo "✅ Configuration files ready:"
            echo "   - railway.json"
            echo "   - .railwayignore"
            echo "   - Dockerfile (with volume support)"
            echo ""
            echo "📋 Next steps:"
            echo "   1. Commit and push changes:"
            echo "      git add ."
            echo "      git commit -m 'Add Railway deployment config'"
            echo "      git push origin main"
            echo ""
            echo "   2. Go to: https://railway.app"
            echo "   3. Click 'Start a New Project'"
            echo "   4. Login with GitHub"
            echo "   5. Select 'Deploy from GitHub repo'"
            echo "   6. Choose: kbalakumar99/tn-electoral-search"
            echo "   7. Add Volume:"
            echo "      - Settings → Volumes → Add Volume"
            echo "      - Mount path: /app/database"
            echo "   8. Deploy! 🎉"
            echo ""
            echo "📖 Full guide: docs/DEPLOYMENT_GUIDE.md"
            break
            ;;
        "Fly.io")
            echo ""
            echo "🪁 Fly.io Deployment"
            echo "===================="
            echo ""
            echo "✅ Configuration files ready:"
            echo "   - fly.toml"
            echo "   - Dockerfile"
            echo ""
            echo "📋 Next steps:"
            echo "   1. Install Fly CLI:"
            echo "      brew install flyctl   # macOS"
            echo "      # OR"
            echo "      curl -L https://fly.io/install.sh | sh   # Linux"
            echo ""
            echo "   2. Login:"
            echo "      flyctl auth login"
            echo ""
            echo "   3. Create volume:"
            echo "      flyctl volumes create electoral_data --region sin --size 1"
            echo ""
            echo "   4. Deploy:"
            echo "      flyctl deploy"
            echo ""
            echo "   5. Get URL:"
            echo "      flyctl info"
            echo ""
            echo "📖 Full guide: docs/DEPLOYMENT_GUIDE.md"
            break
            ;;
        "Render.com")
            echo ""
            echo "🎨 Render.com Deployment"
            echo "========================"
            echo ""
            echo "⚠️  Note: Free tier sleeps after 15min inactivity"
            echo ""
            echo "📋 Next steps:"
            echo "   1. Go to: https://render.com"
            echo "   2. Sign up with GitHub"
            echo "   3. Click 'New +' → 'Web Service'"
            echo "   4. Connect: kbalakumar99/tn-electoral-search"
            echo "   5. Configure:"
            echo "      - Build: pip install -r requirements.txt && python scripts/init_db.py"
            echo "      - Start: python scripts/run_server.py"
            echo "      - Plan: Free"
            echo "   6. Deploy! 🎉"
            echo ""
            echo "📖 Full guide: docs/DEPLOYMENT_GUIDE.md"
            break
            ;;
        "AWS EC2")
            echo ""
            echo "☁️  AWS EC2 Deployment"
            echo "======================"
            echo ""
            echo "⚠️  Note: Requires more setup but full control"
            echo ""
            echo "📋 Summary steps:"
            echo "   1. Sign up for AWS Free Tier"
            echo "   2. Launch t2.micro EC2 instance (Ubuntu)"
            echo "   3. SSH into instance"
            echo "   4. Install Python, Git, Nginx"
            echo "   5. Clone repository"
            echo "   6. Setup systemd service"
            echo "   7. Configure Nginx reverse proxy"
            echo "   8. Setup firewall"
            echo ""
            echo "📖 Full detailed guide: docs/DEPLOYMENT_GUIDE.md"
            echo "   (Includes all commands and configurations)"
            break
            ;;
        "Exit")
            echo "Goodbye! 👋"
            break
            ;;
        *) 
            echo "Invalid option $REPLY"
            ;;
    esac
done

echo ""
echo "💡 Need help? Check:"
echo "   - Full guide: docs/DEPLOYMENT_GUIDE.md"
echo "   - GitHub Issues: https://github.com/kbalakumar99/tn-electoral-search/issues"
echo ""
