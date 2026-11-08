#!/usr/bin/env bash
# ==============================================================================
# Nexus Production Deployment Script (Linux / macOS)
# ==============================================================================
set -euo pipefail

echo "========================================="
echo "  Deploying Nexus Platform (Production)  "
echo "========================================="

# 1. Check prerequisites
command -v docker >/dev/null 2>&1 || { echo >&2 "Error: docker is required but not installed."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo >&2 "Error: docker compose is required."; exit 1; }

# 2. Setup environment file
if [ ! -f .env.production ]; then
    if [ -f .env ]; then
        echo "Notice: .env.production not found, using existing .env"
        ENV_FILE=".env"
    else
        echo "Creating .env.production from .env.production.example..."
        cp .env.production.example .env.production
        ENV_FILE=".env.production"
    fi
else
    ENV_FILE=".env.production"
fi

# 3. Pull / build and start services
echo "Building and launching containers via docker-compose.prod.yml..."
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml up -d --build --remove-orphans

# 4. Wait for gateway to become healthy
echo "Waiting for services to become healthy..."
sleep 5
docker compose -f docker-compose.prod.yml ps

echo "========================================="
echo "  Nexus successfully deployed!           "
echo "  Web UI: http://localhost               "
echo "  API Docs: http://localhost/api/v1/docs "
echo "========================================="

