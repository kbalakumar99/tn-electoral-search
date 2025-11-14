#!/bin/bash
# Quick fix to install PDF processing dependencies on AWS
# Run this once on your AWS instance to enable PDF import functionality

echo "🔧 Installing PDF processing dependencies..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Create it with: python3 -m venv venv"
    exit 1
fi

# Install full requirements
echo "📦 Installing requirements-full.txt..."
pip install -r requirements-full.txt

echo ""
echo "✅ PDF processing dependencies installed!"
echo ""
echo "Now restart the server:"
echo "  ./scripts/aws_deploy.sh"
echo ""
echo "Or manually:"
echo "  sudo systemctl restart tn-electoral-search"
