#!/bin/bash
# Starts uwsgi after creating the ini file using the current env.

set -e

envsubst < $SCRIPTS_DIR/myakuweb_uwsgi_template.ini > \
    $MYAKUWEB_BASE_DIR/myakuweb_uwsgi.ini

# Remove dev mode only settings from uwsgi ini if not in dev mode
if [ "$DJANGO_DEBUG_MODE" == "0" ]; then
    dev_settings_start_lineno="$(\
        grep -n "DEV MODE ONLY SETTINGS BELOW" \
            $MYAKUWEB_BASE_DIR/myakuweb_uwsgi.ini | \
            cut -d ":" -f 1 \
    )"
    head -n $dev_settings_start_lineno \
        $MYAKUWEB_BASE_DIR/myakuweb_uwsgi.ini > \
        $MYAKUWEB_BASE_DIR/myakuweb_uwsgi_prod.ini
    mv $MYAKUWEB_BASE_DIR/myakuweb_uwsgi_prod.ini \
        $MYAKUWEB_BASE_DIR/myakuweb_uwsgi.ini
fi

exec uwsgi --ini $MYAKUWEB_BASE_DIR/myakuweb_uwsgi.ini
