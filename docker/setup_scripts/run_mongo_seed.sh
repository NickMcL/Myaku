#!/bin/bash

# Get usernames and passwords from their docker secrets
crawler_db_username=$(cat $REIBUN_DB_CRAWLER_USERNAME_FILE)
crawler_db_password=$(cat $REIBUN_DB_CRAWLER_PASSWORD_FILE)

mongo --eval "\
    var reibun_db_name = \"$REIBUN_DB_NAME\"
    var crawler_db_username = \"$crawler_db_username\"
    var crawler_db_password = \"$crawler_db_password\"
" $MONGO_SEED_SCRIPT_PATH
