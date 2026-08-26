# AUREVIX — dbt Operations Guide

```bash
# 1. Parse models
dbt parse --project-dir dbt_aurevix --profiles-dir dbt_aurevix

# 2. Run transformations
dbt run --project-dir dbt_aurevix --profiles-dir dbt_aurevix

# 3. Test constraints
dbt test --project-dir dbt_aurevix --profiles-dir dbt_aurevix
```
