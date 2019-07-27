#!/bin/bash
# Script for building, tagging, and labeling Myaku images.

RED='\e[31m'
NC='\e[0m'

IMAGE_NAME_PREFIX="friedrice2/"

POSSIBLE_IMAGE_NAMES=(\
    "crawler" \
    "web" \
    "nginx.reverseproxy" \
    "mongo.crawldb" \
    "mongobackup" \
    "ubuntu.cron" \
)

NO_DEV_TARGET_IMAGE_NAMES=(\
    "ubuntu.cron" \
)


function usage()
{
    cat << EOF
usage: build_image.sh <image_type> <tag>

Builds a docker image of the given type with the given tag and applies the
appropriate labels to the image such as git commit hash for prod images.

If the given tag is "dev", the the image will be built with the dev target.
Otherwise, the image will be built with the prod target or no target if the
Dockerfile for the image doesn't use targets.

The tag must be either "dev" or a version number matching the verioning scheme
for the image, or the script will error.

<image_type> must be one of:
    - crawler
    - web
    - nginx.reverseproxy
    - mongo.crawldb
    - mongobackup
    - ubuntu.cron
EOF
}


error_handler()
{
    lineno="$1"
    error_message="$2"
    if [ -n "$error_message" ]; then
        echo -e "${RED}build_and_label_image: Error around $lineno:" \
            "$error_message${NC}" >&2
    else
        echo -e "${RED}build_and_label_image: Error around $lineno${NC}" >&2
    fi
    exit 1
}
trap 'error_handler ${LINENO}' ERR


if [ $# -ne 2 ] ; then
    usage
    exit 1
fi

# Check if $1 is in the array of possible image names
if [[ ! " ${POSSIBLE_IMAGE_NAMES[@]} " =~ " $1 " ]]; then
    error_handler $LINENO "$(echo \
        "Image name \"$1\" is not one of the possible image names:" \
        "${POSSIBLE_IMAGE_NAMES[@]}")"
fi

if [[ " ${NO_DEV_TARGET_IMAGE_NAMES[@]} " =~ " $1 " ]] && \
        [[ "$2" == "dev" ]]; then
    error_handler $LINENO \
        "Image type \"$1\" does not have a dev target for building"
fi

# Check if given tag matches versioning scheme for given image type
if [ "$1" == "mongobackup" ]; then
    match="$(echo "$2" | \
        grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+.[0-9]+$' | cat)"
elif [ "$1" == "ubuntu.cron" ]; then
    match="$(echo "$2" | grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+$' | cat)"
else
    match="$(echo "$2" | grep -E '^[0-9]+.[0-9]+.[0-9]+$' | cat)"
fi

if [ -z "$match" ] && [ "$2" != "dev" ]; then
    error_handler $LINENO \
        "Tag \"$2\" is not properly formatted for \"$1\" image type"
fi

# To make sure that the most recent git commit is representative of the current
# state of the working directory, do not build and label prod images unless
# there are currently no uncommitted changes in the working directory.
if [ "$2" != "dev" ] && [ -n "$(git status --porcelain)" ]; then
    error_handler $LINENO "$(echo \
        "There are changes in the git working directory, so prod images" \
        "cannot be built and labeled. Please commit all changes then run" \
        "again.")"
fi
git_commit_hash="$(git log --format="%H" -n 1)"

image_name="${IMAGE_NAME_PREFIX}myaku_$1"
if [ "$2" == "dev" ]; then
    build_flags="--target dev"
else
    build_flags="$(echo "--target prod" \
        "--label git_commit_hash=$git_commit_hash")"
fi

case $1 in
    "crawler")
        dockerfile="./docker/myaku_crawler/Dockerfile.crawler"
        ;;

    "web")
        dockerfile="./docker/myaku_web/Dockerfile.myakuweb"
        ;;

    "nginx.reverseproxy")
        dockerfile="./docker/myaku_nginx-reverseproxy/Dockerfile.nginx.reverseproxy"
        ;;

    "mongo.crawldb")
        dockerfile="./docker/myaku_mongo-crawldb/Dockerfile.mongo.crawldb"
        ;;

    "mongobackup")
        dockerfile="./docker/mongobackup/Dockerfile.mongobackup"
        image_name="${IMAGE_NAME_PREFIX}$1"
        build_flags="$(echo "$build_flags --label" \
            "mongo_version=$(echo "$2" | cut -d '_' -f 2)")"
        ;;

    "ubuntu.cron")
        dockerfile="./docker/ubuntu-cron/Dockerfile.ubuntu.cron"
        image_name="${IMAGE_NAME_PREFIX}$1"
        build_flags="$(echo "--label git_commit_hash=$git_commit_hash" \
            "--label ubuntu_version=$(echo "$2" | cut -d '_' -f 2)")"
        ;;

    * )
        error_handler $LINENO "$(echo \
            "Image name \"$1\" is not one of the possible image names:" \
            "${POSSIBLE_IMAGE_NAMES[@]}")"
esac

sudo docker build $build_flags -f "$dockerfile" -t "$image_name:$2" .
if [ "$2" != "dev" ]; then
    sudo docker build $build_flags -f "$dockerfile" -t "$image_name:latest" .
fi
