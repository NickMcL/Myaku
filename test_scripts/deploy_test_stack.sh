#!/bin/bash

RED='\e[31m'
BLUE='\e[34m'
NC='\e[0m'


usage()
{
    cat << EOF
usage: deloy_test_stack.sh [-e|--use-existing-images] [-h|--help]

Deploys a Myaku docker stack for testing.

By default, builds new prod images tagged as "test" for each service with the
current code in the working directory to use for the tests.

-e|--use-existing-images: Instead of building new prod images for the tests,
use the existing images specified in the current prod docker compose file
(./docker/docker-compose.yml).

-h|--help: Outputs this message and exits.
EOF
}


error_handler()
{
    lineno="$1"
    error_message="$2"
    if [ -n "$error_message" ]; then
        echo -e "${RED}deploy_test_stack: Error around $lineno:" \
            "$error_message${NC}" >&2
    else
        echo -e "${RED}deploy_test_stack: Error around $lineno" >&2
    fi

    if [ -z "$test_stack" ]; then
        ./teardown_test_stack.sh "$test_stack"
    fi
    exit 1
}
trap "error_handler ${LINENO}" ERR

use_existing_images=0
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in 
        -e|--use-existing-images)
            use_existing_images=1
            shift
            ;;

        -h|--help)
            usage
            exit 1
            ;;

        *)
            usage
            exit 1
            ;;
    esac
done

test_run_id="$(hexdump -n 4 -e '"%08x"' /dev/urandom)"
test_stack="myaku_test_$test_run_id"

if [ $use_existing_images -eq 0 ]; then
    echo "Building friedrice2/myaku_crawler:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/myaku_crawler/Dockerfile.crawler" \
        -t "friedrice2/myaku_crawler:test" .. > /dev/null

    echo "Building friedrice2/myaku_rescore:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/myaku_rescore/Dockerfile.rescore" \
        -t "friedrice2/myaku_rescore:test" .. > /dev/null

    echo "Building friedrice2/myaku_web:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/myaku_web/Dockerfile.myakuweb" \
        -t "friedrice2/myaku_web:test" .. > /dev/null

    echo "Building friedrice2/myaku_nginx.reverseproxy:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/myaku_nginx-reverseproxy/Dockerfile.nginx.reverseproxy" \
        -t "friedrice2/myaku_nginx.reverseproxy:test" .. > /dev/null

    echo "Building friedrice2/myaku_mongo.crawldb:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/myaku_mongo-crawldb/Dockerfile.mongo.crawldb" \
        -t "friedrice2/myaku_mongo.crawldb:test" .. > /dev/null

    echo "Building friedrice2/mongobackup:test image..." >&2
    sudo docker build --target prod \
        -f "../docker/mongobackup/Dockerfile.mongobackup" \
        -t "friedrice2/mongobackup:test" .. > /dev/null

    echo "Using newly built test images" >&2
    echo "Deploying Myaku test stack $test_stack" >&2
    sudo docker stack deploy \
        -c "../docker/docker-compose.yml" \
        -c "../docker/docker-compose.test.yml" \
        --resolve-image never $test_stack > /dev/null
else
    echo "Using existing images specified in docker/docker-compose.yml" >&2

    echo "Deploying Myaku test stack $test_stack" >&2
    cat "../docker/docker-compose.test.yml" | sed -e "/image:/d" | \
        sudo docker stack deploy \
            -c "../docker/docker-compose.yml" -c - \
            --resolve-image never $test_stack > /dev/null
fi

echo -e "${BLUE}Deployment of stack $test_stack created${NC}" >&2
echo "$test_stack"
exit 0
