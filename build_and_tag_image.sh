#!/bin/bash
# Script for building and tagging Reibun images with unique tags.

set -e

IMAGE_NAME_PREFIX="friedrice2/reibun_"

function usage()
{
    cat << EOF
usage: build_and_tag_image.sh <image_type>

Builds a docker image of the given type and gives it a unique ID tag.

The unique ID tag has the form:

<timestamp>-<git_hash>-<

<image_type> must be one of:
    - crawler.dev
    - crawler.prod
    - mongo.reibundb
    - mongobackup
EOF
}

function generate_image_id()
{
    timestamp="$(date -u +"%Y%m%dT%H%M%S")"
    git_hash="$(git log --oneline | head -n 1 | cut -d " " -f 1)"
    rand_hex="$(hexdump -n 4 -e '"%08x"' /dev/urandom)"
    echo "${timestamp}-${git_hash}-${rand_hex}"
}


if [ $# -ne 1 ] ; then
    usage
    exit 1
fi

# To make sure that the most recent git commit is representative of the current
# state of the working directory, do not build images unless there are
# currently no uncommitted changes in the working directory.
if [ -n "$(git status --porcelain)" ]; then
    echo "
There are changes in the git working directory, so images cannot be built.
Please commit all changes then run again.
"
#exit 1
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

# Build the :latest version first so the image hash can be gotten
image_name="${IMAGE_NAME_PREFIX}${1}"
sudo docker build $target -f $dockerfile -t "$image_name:latest" .
short_image_id="$(
    sudo docker image ls | grep "$image_name\s*latest" | \
        awk '{print $3}' | head -c 8
)"

timestamp="$(date -u +"%Y%m%dT%H%M%S")"
git_hash="$(git log --oneline | head -n 1 | awk '{print $1}')"
unique_id="$timestamp-$git_hash-$short_image_id"
sudo docker build $target -f $dockerfile -t "$image_name:$unique_id" .
