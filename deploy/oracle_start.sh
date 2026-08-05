#!/bin/bash
# Startup script for PM2 on Oracle Cloud
# Usage: pm2 start deploy/oracle_start.sh --name "jarvis"

# Get the absolute path of the directory containing this script, then go up one level to the project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Add the current directory to PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Run the application
python run.py
