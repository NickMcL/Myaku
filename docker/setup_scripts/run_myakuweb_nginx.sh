#!/bin/bash

set -e

# Collect django static files for nginx to serve.
cd $MYAKUWEB_PROJECT_DIR
$PYTHON_BIN manage.py collectstatic

# Sub env vars from docker into nginx conf template.
envsubst < $NGINX_CONF_TEMPLATE > \
    /etc/nginx/sites-available/myakuweb_nginx.conf
ln -s /etc/nginx/sites-available/myakuweb_nginx.conf /etc/nginx/sites-enabled/

rm /etc/nginx/sites-enabled/default
mkdir -p $NGINX_LOG_DIR
/etc/init.d/nginx start

uwsgi --socket $UWSGI_SOCKET_FILE --module myakuweb.wsgi \
    --chmod-socket=666
