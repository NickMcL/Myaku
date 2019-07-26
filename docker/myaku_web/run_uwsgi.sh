#!/bin/bash
# Starts uwsgi after creating the ini file using the current env.

set -e

envsubst < /myakuweb_uwsgi_template.ini > /myakuweb_uwsgi.ini
exec uwsgi --ini /myakuweb_uwsgi.ini
