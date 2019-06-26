#!/bin/bash

IMAGE_NAME_PREFIX="friedrice2/reibun_"

usage()
{
    echo "
usage: build_image.sh <image>

<image> must be one of:
    - crawler.dev
    - crawler.prod
    - mongo.reibundb
    - mongobackup
"
}

generate_image_id()
{
    timestamp="$(date -u +"%Y%m%dT%H%M%S")"
    git_hash="$(git log --oneline | head -n 1 | cut -d " " -f 1)"
    rand_hex="$(
        hexdump -n 4 -e '"%08X"' /dev/random | tr '[:upper:]' '[:lower:]'
    )"
    echo "${timestamp}-${git_hash}-${rand_hex}"
}


if [ $# -ne 1 ] ; then
    usage
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "
There are changes in the git working directory, so images cannot be built.
Please commit all changes then run again.
"
exit 1
fi

case $1 in
    "crawler.dev")
        dockerfile="./docker/dockerfiles/Dockerfile.crawler"
        target="--target dev"
        ;;

    "crawler.prod")
        dockerfile="./docker/dockerfiles/Dockerfile.crawler"
        target="--target prod"
        ;;

    "mongo.reibundb")
        dockerfile="./docker/dockerfiles/Dockerfile.mongo.reibundb"
        target=""
        ;;

    "mongobackup")
        dockerfile="./docker/dockerfiles/Dockerfile.mongobackup"
        target=""
        ;;

    * )
        usage
        exit 1
        ;;
esac

image_id="$(generate_image_id)"
image_name="${IMAGE_NAME_PREFIX}${1}"
sudo docker build $target -f $dockerfile -t "$image_name:${image_id}" .
sudo docker build $target -f $dockerfile -t "$image_name:latest" .
