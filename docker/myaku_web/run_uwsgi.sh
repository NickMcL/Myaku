#!/bin/bash
# Starts uwsgi after creating the ini file using the current env.

set -e



envsubst < $SCRIPTS_DIR/myakuweb_uwsgi_template.ini > /myakuweb_uwsgi.ini

# Remove dev mode only settings from uwsgi ini if not in dev mode
if [ "$DJANGO_DEBUG_MODE" == "0" ]; then
    dev_settings_start_lineno="$(\
        grep -n "DEV MODE ONLY SETTINGS BELOW" /myakuweb_uwsgi.ini | \
        cut -d ":" -f 1 \
    )"
    head -n $dev_settings_start_lineno /myakuweb_uwsgi.ini > \
        /myakuweb_uwsgi_prod.ini
    mv /myakuweb_uwsgi_prod.ini /myakuweb_uwsgi.ini
fi

exec uwsgi --ini /myakuweb_uwsgi.ini
