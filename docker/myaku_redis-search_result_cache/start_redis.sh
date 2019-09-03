#!/bin/bash

exec redis-server $REDIS_CONF_FILE \
    --requirepass "$(cat $MYAKU_SEARCH_RESULT_CACHE_PASSWORD_FILE)" \
    --dir "$REDIS_DATA_DIR"
