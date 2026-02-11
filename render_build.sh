#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing frontend dependencies..."
pip install --upgrade pip
pip install -r frontend/requirements.txt

# Verify critical dependencies are installed
echo "Verifying pydantic installation..."
python -c "import pydantic; print(f'pydantic {pydantic.__version__} OK')"

echo "Build complete."
