# AUREVIX — Local Platform Deployment Guide

## 1. Prerequisites
- Python 3.12.x in isolated environment (`.venv`)
- Docker Desktop 20+ & Docker Compose v2+
- Java 17+ (for local Spark execution)

## 2. Environment Setup
```powershell
# Copy environment configuration
cp .env.example .env

# Activate isolated Python 3.12 virtual environment
.\.venv\Scripts\Activate.ps1
```

## 3. Launch Docker Services
```powershell
docker compose -f docker-compose.yml up -d
docker compose ps
```

## 4. Run Smoke Test & Dashboard
```powershell
# Run automated deployment smoke test
.\.venv\Scripts\python.exe scripts/health_check.py

# Launch Streamlit Enterprise Dashboard
.\.venv\Scripts\streamlit.exe run dashboard/app.py
```
Dashboard available at: `http://localhost:8501`
