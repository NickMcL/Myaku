#!/bin/bash

MAX_GET_CONTAINER_RETIRES=5
RED='\e[31m'
BLUE='\e[34m'
NC='\e[0m'


usage()
{
    cat << EOF
usage: get_container_id.sh <service_name> [-h|--help]

Prints the container ID for the given one-container service to stdout.

-h|--help: Outputs this message and exits.
EOF
}


error_handler()
{
    lineno="$1"
    error_message="$2"
    if [ -n "$error_message" ]; then
        echo -e "${RED}get_container_id: Error around $lineno:" \
            "$error_message${NC}" >&2
    else
        echo -e "${RED}get_container_id: Error around $lineno${NC}" >&2
    fi
    exit 1
}


if [ $# -ne 1 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    usage
    exit 1
fi
service="$1"

# Sometimes a container takes a little bit of time to get started, so try to
# get its ID a number of times waiting 1 second between tries.
for i in $(seq 1 $MAX_GET_CONTAINER_RETIRES)
do
    echo "Attempting to get $service container ID after 5 seconds " \
        "(attempt $i/$MAX_GET_CONTAINER_RETIRES)..." >&2
    sleep 5
    container_id="$(
        sudo docker inspect -f "{{.Status.ContainerStatus.ContainerID}}" \
            $(sudo docker service ps -q "$service") \
    )"
    if [ -n "$container_id" ]; then
        break
    fi
done

if [ -z "$container_id" ]; then
    error_handler ${LINENO} "${RED}Failed to get $service container ID${NC}"
fi

# Use short ID for display to match how docker displays it in ps commands.
short_container_id="$(echo "$container_id" | head -c 12)"
echo -e "Obtained $service container ID $short_container_id" >&2

echo "$container_id"
exit 0
