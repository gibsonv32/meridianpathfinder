#!/bin/bash
# Simple deployment script for local/DGX single-user setup

set -e

echo "MERIDIAN Local/DGX Deployment Script"
echo "====================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please run as your regular user, not root"
   exit 1
fi

# Installation directory
INSTALL_DIR="$HOME/meridianpathfinder"
SERVICE_NAME="meridian@$USER"

echo ""
echo "1. Setting up environment..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "   Created .env file - please update with your API keys"
fi

echo ""
echo "2. Installing dependencies..."
if command -v uv &> /dev/null; then
    echo "   Using uv..."
    uv sync
else
    echo "   Using pip..."
    pip install -e .
fi

echo ""
echo "3. Running tests..."
python -m pytest tests/ -v --tb=short || true

echo ""
echo "4. Setting up systemd service (optional)..."
echo "   To install as a systemd service, run:"
echo "   sudo cp meridian.service /etc/systemd/system/${SERVICE_NAME}.service"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable ${SERVICE_NAME}"
echo "   sudo systemctl start ${SERVICE_NAME}"

echo ""
echo "5. Starting API server..."
echo "   You can now start the API with:"
echo "   meridian api start"
echo "   Or if using uv:"
echo "   uv run meridian api start"

echo ""
echo "====================================="
echo "Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start the API: meridian api start"
echo "3. Access API docs at: http://localhost:8000/docs"
echo "4. Run demo: meridian demo --data your_data.csv --target target_col --row '{\"x1\": 0.5}'"