#!/bin/bash
# Script for building, tagging, and labeling Myaku images.

RED='\e[31m'
NC='\e[0m'

IMAGE_NAME_PREFIX="friedrice2/"

POSSIBLE_IMAGE_TYPES=(\
    "crawler" \
    "rescore" \
    "web" \
    "nginx.reverseproxy" \
    "redis.first-page-cache" \
    "mongo.crawldb" \
    "mongobackup" \
    "ubuntu.cron" \
    "run-tests" \
)

NO_DEV_TARGET_IMAGE_TYPES=(\
    "ubuntu.cron" \
)


function usage()
{
    cat << EOF
usage: build_image.sh [-n|--no-cache] [-h|--help] <image_type> <tag>

Builds a docker image of the given type with the given tag and applies the
appropriate labels to the image such as git commit hash for prod images.

If the given tag is "dev", the the image will be built with the dev target.
Otherwise, the image will be built with the prod target or no target if the
Dockerfile for the image doesn't use targets.

The tag must be either "dev" or a version number matching the verioning scheme
for the image, or the script will error.

<image_type> must be one of:
    - crawler
    - rescore
    - web
    - nginx.reverseproxy
    - redis.first-page-cache
    - mongo.crawldb
    - mongobackup
    - ubuntu.cron
    - run-tests

-n|--no-cache: Builds the image with the --no-cache option.
-h|--help: Outputs this message and exits.
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


no_cache_flag=""
image_type=""
tag=""
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -n|--no-cache)
            no_cache_flag="--no-cache"
            shift
            ;;

        -h|--help)
            usage
            exit 1
            ;;

        *)
            if [ -z "$image_type" ]; then
                image_type="$key"
            elif [ -z "$tag" ]; then
                tag="$key"
            else
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z $image_type ] || [ -z $tag ]; then
    usage
    exit 1
fi

# Check if image type is in the array of possible image types
if [[ ! " ${POSSIBLE_IMAGE_TYPES[@]} " =~ " $image_type " ]]; then
    error_handler $LINENO "$(echo \
        "Image type \"$image_type\" is not one of the possible image types:" \
        "${POSSIBLE_IMAGE_TYPES[@]}")"
fi

if [[ " ${NO_DEV_TARGET_IMAGE_TYPES[@]} " =~ " $image_type " ]] && \
        [[ "$tag" == "dev" ]]; then
    error_handler $LINENO \
        "Image type \"$image_type\" does not have a dev target for building"
fi

# Check if given tag matches versioning scheme for given image type
if [ "$image_type" == "mongobackup" ]; then
    match="$(echo "$tag" | \
        grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+.[0-9]+$' | cat)"
elif [ "$image_type" == "ubuntu.cron" ]; then
    match="$(echo "$tag" | \
        grep -E '^[0-9]+.[0-9]+.[0-9]+_[0-9]+.[0-9]+$' | cat)"
else
    match="$(echo "$tag" | grep -E '^[0-9]+.[0-9]+.[0-9]+$' | cat)"
fi

if [ -z "$match" ] && [ "$tag" != "dev" ]; then
    error_handler $LINENO \
        "Tag \"$tag\" is not properly formatted for \"$image_type\" image type"
fi

# To make sure that the most recent git commit is representative of the current
# state of the working directory, do not build and label prod images unless
# there are currently no uncommitted changes in the working directory.
if [ "$tag" != "dev" ] && [ -n "$(git status --porcelain)" ]; then
    error_handler $LINENO "$(echo \
        "There are changes in the git working directory, so prod images" \
        "cannot be built and labeled. Please commit all changes then run" \
        "again.")"
fi
git_commit_hash="$(git log --format="%H" -n 1)"

image_name="${IMAGE_NAME_PREFIX}myaku_$image_type"
if [ "$tag" == "dev" ]; then
    build_flags="--target dev"
else
    build_flags="$(echo "--target prod" \
        "--label git_commit_hash=$git_commit_hash")"
fi

case $image_type in
    "crawler")
        dockerfile="./docker/myaku_crawler/Dockerfile.crawler"
        ;;

    "rescore")
        dockerfile="./docker/myaku_rescore/Dockerfile.rescore"
        ;;

    "web")
        dockerfile="./docker/myaku_web/Dockerfile.myakuweb"
        ;;

    "redis.first-page-cache")
        dockerfile="./docker/myaku_redis.first-page-cache/Dockerfile.redis.first-page-cache"
        ;;

    "nginx.reverseproxy")
        dockerfile="./docker/myaku_nginx.reverseproxy/Dockerfile.nginx.reverseproxy"
        ;;

    "mongo.crawldb")
        dockerfile="./docker/myaku_mongo.crawldb/Dockerfile.mongo.crawldb"
        ;;

    "run-tests")
        dockerfile="./docker/myaku_run-tests/Dockerfile.run-tests"
        build_flags=""
        ;;

    "mongobackup")
        dockerfile="./docker/mongobackup/Dockerfile.mongobackup"
        image_name="${IMAGE_NAME_PREFIX}$image_type"
        build_flags="$(echo "$build_flags --label" \
            "mongo_version=$(echo "$tag" | cut -d '_' -f 2)")"
        ;;

    "ubuntu.cron")
        dockerfile="./docker/ubuntu.cron/Dockerfile.ubuntu.cron"
        image_name="${IMAGE_NAME_PREFIX}$image_type"
        build_flags="$(echo "--label git_commit_hash=$git_commit_hash" \
            "--label ubuntu_version=$(echo "$tag" | cut -d '_' -f 2)")"
        ;;

    * )
        error_handler $LINENO "$(echo \
            "Image name \"$image_type\" is not one of the possible image" \
            "types: ${POSSIBLE_IMAGE_NAMES[@]}")"
esac

sudo docker build $build_flags $no_cache_flag -f "$dockerfile" \
    -t "$image_name:$tag" .
if [ "$tag" != "dev" ]; then
    sudo docker build $build_flags -f "$dockerfile" -t "$image_name:latest" .
fi
