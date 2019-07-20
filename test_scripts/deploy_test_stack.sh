#!/bin/bash

RED='\e[31m'
BLUE='\e[34m'
NC='\e[0m'

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


usage()
{
    cat << EOF
usage: deloy_test_stack.sh [<tag>] [-h|--help]

Deploys a Myaku docker stack for testing.

By default, builds a new crawler.prod:test image with the current code in the
working directory to deploy with the stack.

If a tag is passed as a parameter, will deploy the existing crawler.prod:<tag>
image with the stack instead.

-h|--help: Outputs this message and exits.
EOF
}


image_tag=""
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in 
        -h|--help)
            usage
            exit 1
            ;;

        *)
            if [ -z "$image_tag" ]; then
                image_tag="$1"
                shift
            else
                usage
                exit 1
            fi
            ;;
    esac
done

if [ -z "$image_tag" ]; then
    echo "Building and using friedrice2/myaku_crawler.prod:test image..." >&2
    sudo docker build --target "prod" \
        -f "../docker/dockerfiles/Dockerfile.crawler" \
        -t "friedrice2/myaku_crawler.prod:test" .. > /dev/null

    # Add a backslash before the forward slash so that the forward slash will
    # be esacped in the sed find replace.
    image_name="friedrice2\\/myaku_crawler.prod:test"
else
    echo "Using existing friedrice2/myaku_crawler.prod:$image_tag image" >&2
    image_name="friedrice2\\/myaku_crawler.prod:$image_tag"
fi

test_run_id="$(hexdump -n 4 -e '"%08x"' /dev/urandom)"
test_stack="myaku_test_$test_run_id"

echo "Deploying Myaku test stack $test_stack" >&2
cat "../docker/docker-compose.test.yml" | \
    sed -e "s/friedrice2\/myaku_crawler.prod:test/$image_name/g" | \
    sudo docker stack deploy \
        -c "../docker/docker-compose.yml" -c - \
        --resolve-image never $test_stack > /dev/null
echo -e "${BLUE}Deployment of stack $test_stack created${NC}" >&2

echo "$test_stack"
exit 0
