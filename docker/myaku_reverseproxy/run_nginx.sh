#!/bin/bash
# Starts nginx after creating the conf file using the current env

set -e

# Errors can happen if nginx starts at the same time uwsgi is starting in the
# Myaku web container, so wait for uwsgi to be ready
wait-for-it $MYAKUWEB_HOST:$MYAKUWEB_UWSGI_PORT -t 10

if [ "$NGINX_DEBUG_MODE" == "1" ]; then
    # Allow all hosts in debug mode
    export ALLOWED_HOSTS="_"
else
    # Set allowed hosts from docker config file
    export MYAKUWEB_ALLOWED_HOSTS="$(\
        cat $MYAKUWEB_ALLOWED_HOSTS_FILE | tr '\n' ' ' | sed 's/ $//g' \
    )"
fi

envsubst < $NGINX_DOCKER_FILES_DIR/nginx_template.conf > \
    /etc/nginx/conf.d/myaku_reverseproxy.conf
exec nginx -g 'daemon off;'
