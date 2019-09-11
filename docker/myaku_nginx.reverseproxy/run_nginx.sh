#!/bin/bash
# Starts nginx after creating the conf file using the current env

# Errors can happen if nginx starts at the same time uwsgi is starting in the
# Myaku web container, so wait for uwsgi to be ready
uwsgi_available=0
for ((i = 0; i < 20; i++))
do
    nc -zv -w 1 $MYAKUWEB_HOST $MYAKUWEB_UWSGI_PORT
    if [ $? -eq 0 ]; then
        echo "uWSGI available after $i seconds"
        uwsgi_available=1
        break
    fi
done
if [ $uwsgi_available -eq 0 ]; then
    echo "ERROR: uWSGI not available after 20 seconds"
    exit 1
fi


# Set allowed hosts from docker config file
export MYAKUWEB_ALLOWED_HOSTS="$(\
    cat $MYAKUWEB_ALLOWED_HOSTS_FILE | tr '\n' ' ' | sed 's/ $//g' \
)"

envsubst < $NGINX_RUN_FILES_DIR/nginx_template.conf > \
    /etc/nginx/conf.d/myaku_reverseproxy.conf
exec nginx -g 'daemon off;'
