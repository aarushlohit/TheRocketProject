#!/bin/bash
# Rocket Agent Setup Script
# Sets up the development environment

set -e

echo "🚀 Rocket Agent Setup"
echo "==================="
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if ! python3 -c "import sys; sys.exit(not sys.version_info >= (3, 11))"; then
    echo -e "${RED}Python 3.11+ is required. You have $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $python_version found"
echo

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null
echo -e "${GREEN}✓${NC} pip upgraded"
echo

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"
echo

# Create config directory
echo "Setting up configuration..."
mkdir -p ~/.rocket
if [ ! -f ~/.rocket/config.yaml ]; then
    cp scripts/config.example.yaml ~/.rocket/config.yaml
    echo -e "${GREEN}✓${NC} Default config created at ~/.rocket/config.yaml"
else
    echo -e "${YELLOW}⚠${NC}  Config file already exists at ~/.rocket/config.yaml"
fi
echo

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓${NC} Logs directory created"
echo

# Run tests (optional)
if command -v pytest &> /dev/null; then
    echo "Running tests..."
    pytest tests/ -v --tb=short 2>/dev/null || echo -e "${YELLOW}⚠${NC}  Some tests failed (this is ok for initial setup)"
    echo
fi

echo -e "${GREEN}Setup complete!${NC}"
echo
echo "Next steps:"
echo "  1. Start the agent: python agent/main.py"
echo "  2. Check logs: tail -f logs/rocket-agent.log"
echo "  3. See documentation: docs/README.md"
echo
echo "Happy automating! 🚀"
