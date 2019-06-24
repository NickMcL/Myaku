#!/bin/bash
mkdir -p "$REIBUN_DB_BACKUPS_DIR/backup_dumps"
mkdir -p "$REIBUN_DB_BACKUPS_DIR/logs"
bash "$REIBUN_DB_BACKUP_SCRIPT" >> \
    "$REIBUN_DB_BACKUPS_DIR/logs/$(date -I).log" 2>&1
