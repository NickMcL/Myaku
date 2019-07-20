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
usage: deloy_test_stack.sh [dev|prod] [-h|--help]

Deploys a Myaku docker stack for testing.

With the dev option or no option, uses the dev stack which automatically uses
the local images tagged :latest.

With the prod option, uses the prod stack which uses the uniquely tagged images
specified in the docker/docker-compose.yml file.

-h|--help: Outputs this message and exits.
EOF
}


if [ $# -gt 1 ] ; then
    usage
    exit 1
fi

if [ $# -eq 1 ] && [ "$1" != "dev" ] && [ "$1" != "prod" ]; then
    usage
    exit 1
fi

test_run_id="$(hexdump -n 4 -e '"%08x"' /dev/urandom)"
test_stack="myaku_test_$test_run_id"

if [ "$1" == "prod" ]; then
    echo "Deploying Myaku prod stack $test_stack..." >&2
    sudo docker stack deploy \
        -c "../docker/docker-compose.yml" \
        --resolve-image never $test_stack > /dev/null
else
    echo "Deploying Myaku dev stack $test_stack..." >&2
    sudo docker stack deploy \
        -c "../docker/docker-compose.yml" \
        -c "../docker/docker-compose.dev.yml" \
        --resolve-image never $test_stack > /dev/null
fi
echo -e "${BLUE}Deployment of stack $test_stack created${NC}" >&2

echo "$test_stack"
exit 0
