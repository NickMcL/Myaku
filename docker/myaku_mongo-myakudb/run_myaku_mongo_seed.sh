#!/bin/bash

# Get usernames and passwords from their docker secrets
backup_db_username=$(cat $MYAKU_DB_BACKUP_USERNAME_FILE)
backup_db_password=$(cat $MYAKU_DB_BACKUP_PASSWORD_FILE)
crawler_db_username=$(cat $MYAKU_DB_CRAWLER_USERNAME_FILE)
crawler_db_password=$(cat $MYAKU_DB_CRAWLER_PASSWORD_FILE)
web_db_username=$(cat $MYAKU_DB_WEB_USERNAME_FILE)
web_db_password=$(cat $MYAKU_DB_WEB_PASSWORD_FILE)

mongo --eval "\
    var myaku_db_name = \"$MYAKU_DB_NAME\"
    var backup_db_username = \"$backup_db_username\"
    var backup_db_password = \"$backup_db_password\"
    var crawler_db_username = \"$crawler_db_username\"
    var crawler_db_password = \"$crawler_db_password\"
    var web_db_username = \"$web_db_username\"
    var web_db_password = \"$web_db_password\"
" $MYAKU_MONGO_SEED_JS_PATH
