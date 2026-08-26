# AUREVIX — CI/CD Pipeline Specification

## 1. Pipeline Stages
1. **Lint & Config Validation:** Verifies `.env.example`, `Dockerfile`, and `docker-compose.yml`.
2. **dbt Parse & Compile:** Verifies all SQL transformations across staging, intermediate, and marts schemas.
3. **Automated Regression Suite:** Runs 45+ unit and integration tests across Phases 2 through 8.
4. **Container Build Validation:** Builds multi-stage Docker image and validates health check hooks.
