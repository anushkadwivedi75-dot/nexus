# ==============================================================================
# Nexus Production Deployment Script (Windows PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Deploying Nexus Platform (Production)  " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Verify Docker CLI
try {
    docker --version | Out-Null
} catch {
    Write-Error "Docker is not running or not in PATH. Please start Docker Desktop."
    exit 1
}

# 2. Setup environment file
$EnvFile = ".env.production"
if (-not (Test-Path ".env.production")) {
    if (Test-Path ".env") {
        Write-Host "Notice: .env.production not found, using .env" -ForegroundColor Yellow
        $EnvFile = ".env"
    } else {
        Write-Host "Creating .env.production from .env.production.example..." -ForegroundColor Green
        Copy-Item ".env.production.example" ".env.production"
    }
}

# 3. Build & launch stack
Write-Host "Building and launching containers via docker-compose.prod.yml..." -ForegroundColor Green
docker compose --env-file $EnvFile -f docker-compose.prod.yml up -d --build --remove-orphans

# 4. Check status
Write-Host "Waiting for services to become healthy..." -ForegroundColor Green
Start-Sleep -Seconds 5
docker compose -f docker-compose.prod.yml ps

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Nexus successfully deployed!           " -ForegroundColor Green
Write-Host "  Web UI: http://localhost               " -ForegroundColor Green
Write-Host "  API Docs: http://localhost/api/v1/docs " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

