#!/bin/bash
# Collects Myaku web static in static root on the host machine.

cd ..
echo "Binding $(pwd) to /myakuweb/src"
sudo docker run -it --rm --entrypoint "/bin/bash" \
    -v $(pwd):/myakuweb/src \
    -e DJANGO_SECRET_KEY_FILE=/myakuweb/src/docker/test_secrets/web_django_secret_key_TESTUSEONLY.txt \
    friedrice2/myaku_web.dev:latest -c "\$PYTHON_BIN manage.py collectstatic"
sudo chown -R $USER ./myakuweb/static
