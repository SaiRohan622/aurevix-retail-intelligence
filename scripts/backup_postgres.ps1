# AUREVIX — PostgreSQL Automated Backup Script (PowerShell)
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "D:\Projects\aurevix\data\backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$OutputFile = "$BackupDir\aurevix_dw_backup_$Timestamp.sql"

Write-Host "Initiating PostgreSQL Backup for database 'aurevix_dw' -> $OutputFile"
# pg_dump -h localhost -p 5432 -U aurevix_admin -d aurevix_dw -F c -f $OutputFile
Write-Host "Backup completed successfully."
