#!/bin/bash
set -e

# Setup data directory structure if using single volume mount
if [ -d "/app/data" ]; then
    echo "Setting up data directories from /app/data..."
    
    # Create subdirectories in /app/data if they don't exist
    mkdir -p /app/data/input /app/data/output /app/data/models
    
    # Create symbolic links from /app to /app/data
    ln -sfn /app/data/input /app/input
    ln -sfn /app/data/output /app/output
    ln -sfn /app/data/models /app/models
    
    # Link .env if it exists in data directory
    if [ -f "/app/data/.env" ]; then
        ln -sfn /app/data/.env /app/.env
    fi
    
    echo "Data directories linked successfully"
else
    # If not using /app/data mount, ensure directories exist
    mkdir -p /app/input /app/output /app/models
fi

# Execute the main command
exec "$@"
