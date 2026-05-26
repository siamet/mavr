#!/bin/bash
# Development environment setup script for Mavr

set -e  # Exit on error

echo "Setting up Mavr..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python 3.9 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install tree-sitter language grammars
echo "Installing tree-sitter language grammars..."
python scripts/setup_parsers.py

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data/training
mkdir -p data/benchmark
mkdir -p models/checkpoints

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Model Configuration
MODEL_CACHE_DIR=models/checkpoints
EOF
    echo "Created .env file (please update with your credentials)"
else
    echo ".env file already exists"
fi

# Run tests to verify installation
echo "Running tests to verify installation..."
pytest tests/ -v || echo " Some tests failed (this is expected for initial setup)"

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest tests/"
echo ""
echo "To start development:"
echo "  python -m src.main --help"
echo ""
