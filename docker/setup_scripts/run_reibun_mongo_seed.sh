#!/bin/bash

# Get usernames and passwords from their docker secrets
backup_db_username=$(cat $REIBUN_DB_BACKUP_USERNAME_FILE)
backup_db_password=$(cat $REIBUN_DB_BACKUP_PASSWORD_FILE)
crawler_db_username=$(cat $REIBUN_DB_CRAWLER_USERNAME_FILE)
crawler_db_password=$(cat $REIBUN_DB_CRAWLER_PASSWORD_FILE)

mongo --eval "\
    var reibun_db_name = \"$REIBUN_DB_NAME\"
    var backup_db_username = \"$backup_db_username\"
    var backup_db_password = \"$backup_db_password\"
    var crawler_db_username = \"$crawler_db_username\"
    var crawler_db_password = \"$crawler_db_password\"
" $REIBUN_MONGO_SEED_JS_PATH
