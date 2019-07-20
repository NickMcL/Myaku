#!/bin/bash
# Script for building, tagging, and labeling Myaku images.

RED='\e[31m'
NC='\e[0m'

IMAGE_NAME_PREFIX="friedrice2/"

function usage()
{
    cat << EOF
usage: build_and_label_image.sh <image_type> <tag>

Builds a docker image of the given type with the given tag and applies the
appropriate labels to the image such as git commit hash.

<image_type> must be one of:
    - crawler.dev
    - crawler.prod
    - mongo.myakudb
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

function generate_image_id()
{
    timestamp="$(date -u +"%Y%m%dT%H%M%S")"
    git_hash="$(git log --oneline | head -n 1 | cut -d " " -f 1)"
    rand_hex="$(hexdump -n 4 -e '"%08x"' /dev/urandom)"
    echo "${timestamp}-${git_hash}-${rand_hex}"
}


if [ $# -ne 2 ] ; then
    usage
    exit 1
fi

if [ "$1" == "mongobackup" ]; then
    match="$(echo "$2" | \
        grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+.[0-9]+$' | cat)"
elif [ "$1" == "ubuntu.cron" ]; then
    match="$(echo "$2" | grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+$' | cat)"
else
    match="$(echo "$2" | grep -E '^[0-9]+.[0-9]+.[0-9]+$' | cat)"
fi

if [ -z "$match" ]; then
    error_handler $LINENO \
        "Tag \"$2\" is not properly formatted for \"$1\" image type"
fi

# To make sure that the most recent git commit is representative of the current
# state of the working directory, do not build and label images unless there
# are currently no uncommitted changes in the working directory.
if [ -n "$(git status --porcelain)" ]; then
    error_handler $LINENO "$(echo \
        "There are changes in the git working directory, so images cannot" \
        "be built and labeled. Please commit all changes then run again.")"
fi
git_commit_hash="$(git log --format="%H" -n 1)"

case $1 in
    "crawler.dev")
        image_name="${IMAGE_NAME_PREFIX}myaku_$1"
        dockerfile="./docker/dockerfiles/Dockerfile.crawler"
        build_flags="--target dev"
        ;;

    "crawler.prod")
        image_name="${IMAGE_NAME_PREFIX}myaku_$1"
        dockerfile="./docker/dockerfiles/Dockerfile.crawler"
        build_flags="--target prod"
        ;;

    "mongo.myakudb")
        image_name="${IMAGE_NAME_PREFIX}myaku_$1"
        dockerfile="./docker/dockerfiles/Dockerfile.mongo.myakudb"
        build_flags=""
        ;;

    "mongobackup")
        image_name="${IMAGE_NAME_PREFIX}$1"
        dockerfile="./docker/dockerfiles/Dockerfile.mongobackup"
        build_flags="--label mongo_version=$(echo "$2" | cut -d '_' -f 2)"
        ;;

    "ubuntu.cron")
        image_name="${IMAGE_NAME_PREFIX}$1"
        dockerfile="./docker/dockerfiles/Dockerfile.ubuntu.cron"
        build_flags="--label ubuntu_version=$(echo "$2" | cut -d '_' -f 2)"
        ;;

    * )
        error_handler $LINENO "$(echo \
            "Image type \"$1\" is not a possible option. Run script with" \
            "no args to see possible options.")"
        ;;
esac

sudo docker build \
    --label "git_commit_hash=$git_commit_hash" $build_flags \
    -f "$dockerfile" -t "$image_name:$2" .
sudo docker build \
    --label "git_commit_hash=$git_commit_hash" $build_flags \
    -f "$dockerfile" -t "$image_name:latest" .
