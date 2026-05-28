#!/bin/bash
# Development environment setup script for Mavr (uv-based)

set -e  # Exit on error

echo "Setting up Mavr..."

# Check uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed."
    echo "Install it: https://docs.astral.sh/uv/getting-started/installation/"
    echo "Quick install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "uv version: $(uv --version)"

# Sync dependencies (creates .venv and installs project + dev group)
echo "Syncing dependencies via uv..."
uv sync

# Install tree-sitter language grammars
echo "Installing tree-sitter language grammars..."
uv run python scripts/setup_parsers.py

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
uv run pytest tests/ -v || echo "Some tests failed (this is expected for initial setup)"

echo ""
echo "Setup complete!"
echo ""
echo "Run commands via uv (no manual activation needed):"
echo "  uv run pytest tests/"
echo "  uv run python -m src.main --help"
echo ""
echo "To activate the environment manually:"
echo "  source .venv/bin/activate"
echo ""
