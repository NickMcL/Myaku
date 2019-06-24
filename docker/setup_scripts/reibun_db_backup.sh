#!/bin/bash

set -e
function cleanup {
    echo "Exiting Reibun db backup script at $(date)"
    echo
}
trap cleanup EXIT

echo "Starting Reibun db backup script at $(date)"

backup_db_username="$(cat $REIBUN_DB_USERNAME_FILE)"
backup_db_password="$(cat $REIBUN_DB_PASSWORD_FILE)"

backup_dump_dir="$REIBUN_DB_BACKUPS_DIR/backup_dumps"
backup_log_dir="$REIBUN_DB_BACKUPS_DIR/logs"

backup_filepath="$backup_dump_dir/$(date -I)_backup"
if [ ! -f "$backup_filepath" ]; then
    echo "$backup_filepath does not exist, so creating backup now"
    mongodump -h $REIBUN_DB_HOST -u "$backup_db_username" \
        -p "$backup_db_password" --gzip --archive="$backup_filepath"
else
    echo "$backup_filepath already exists, so will not create backup"
fi

current_backup_count=$(ls -1 "$backup_dump_dir" | wc -l)
if [ $current_backup_count -gt $REIBUN_DB_MAX_ALLOWED_BACKUPS ]; then
    excess_backup_count=$((\
        $current_backup_count - $REIBUN_DB_MAX_ALLOWED_BACKUPS\
    ))
    echo -n "Current backup count ($current_backup_count) is greater than max "
    echo -n "allowed count ($REIBUN_DB_MAX_ALLOWED_BACKUPS), so deleting the "
    echo "following backup files and backup logs:"

    # ls prints the directory contents in ascending sorted order by name by
    # default, so deleting the top N files printed will delete the N oldest
    # backups.
    backup_dumps_to_rm=$(\
        ls -1 -d $backup_dump_dir/* | head -n $excess_backup_count\
    )
    backup_logs_to_rm=$(\
        ls -1 -d $backup_log_dir/* | head -n $excess_backup_count\
    )

    echo $backup_dumps_to_rm
    echo $backup_logs_to_rm

    rm $backup_dumps_to_rm
    rm $backup_logs_to_rm
    exit 0
fi

echo -n "Current backup count ($current_backup_count) is less than "
echo -n "or equal to max allowed count ($REIBUN_DB_MAX_ALLOWED_BACKUPS), so "
echo "no backup files will be deleted"
exit 0
