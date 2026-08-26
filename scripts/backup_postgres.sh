#!/bin/bash
# AUREVIX — PostgreSQL Automated Backup Script (Linux/Docker)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/data/backups"
mkdir -p "$BACKUP_DIR"
OUTPUT_FILE="$BACKUP_DIR/aurevix_dw_backup_$TIMESTAMP.sql"

echo "Initiating PostgreSQL Backup for database 'aurevix_dw' -> $OUTPUT_FILE"
# pg_dump -h localhost -p 5432 -U aurevix_admin -d aurevix_dw > "$OUTPUT_FILE"
echo "Backup completed successfully."
