#!/bin/bash
mkdir -p "$BACKUPS_DIR/backup_dumps"
mkdir -p "$BACKUPS_DIR/logs"

export BACKUP_TIMESTAMP="$(date -u -Iseconds | sed 's/:/,/g')"
bash "$DB_BACKUP_SCRIPT" >> "$BACKUPS_DIR/logs/${BACKUP_TIMESTAMP}.log" 2>&1
