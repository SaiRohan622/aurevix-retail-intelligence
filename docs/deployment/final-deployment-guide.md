# AUREVIX — Final Production Deployment Guide

## 1. Quick Launch
```powershell
# 1. Start Docker services
docker compose up -d

# 2. Run Health Check Probe
.\.venv\Scripts\python.exe scripts/health_check.py

# 3. Launch Streamlit Operations Dashboard
.\.venv\Scripts\streamlit.exe run dashboard/app.py
```
Access UI at `http://localhost:8501`.

## 2. Automated Regression Test Execution
```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/ tests/integration/ -v
```
