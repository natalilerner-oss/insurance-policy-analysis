#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing frontend dependencies..."
pip install --upgrade pip
pip install -r frontend/requirements.txt
