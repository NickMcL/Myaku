#!/bin/bash

TEST_STACK_PREFIX="myaku_test_"
RED='\e[31m'
BLUE='\e[34m'
NC='\e[0m'


error_handler()
{
    lineno="$1"
    error_message="$2"
    if [ -n "$error_message" ]; then
        echo -e "${RED}teardown_test_stack: Error around $lineno:" \
            "$error_message${NC}" >&2
    else
        echo -e "${RED}teardown_test_stack: Error around $lineno${NC}" >&2
    fi
    exit 1
}
trap 'error_handler ${LINENO}' ERR



usage()
{
    cat << EOF
usage: teardown_test_stack.sh [stack_name] [-s|--rm-stack-only] [-h|--help]

Attempts to tear down the given test stack by removing it and all of its
component parts (i.e. services, containers, secrets, networks, volumes).

If no arguments are given, tears down all stacks that have a name starting with
"$TEST_STACK_PREFIX".

-s|--rm-stack-only: Attempts to remove the docker stack object, but does not
    directly attempt to remove any of the stack components.

-h|--help: Outputs this message and exits.
EOF
}


# $1 is one of stack, service, container, volume, network, or secret.
# $2 is the prefix to match against to find objects to remove.
rm_docker_objects()
{
    if [ -z "$1" ] || [ -z "$2" ]; then
        error_handler ${LINENO} "rm_docker_objects args not properly set"
    fi

    if [ "$1" == "volume" ]; then
        objects=$(sudo docker $1 ls | grep "$2" | awk '{print $2}')
    elif [ "$1" == "container" ]; then
        objects=$(sudo docker $1 ls -a | grep "$2" | awk '{print $1}')
    else
        objects=$(sudo docker $1 ls | grep "$2" | awk '{print $1}')
    fi

    if [ -z "$objects" ] ; then
        echo "No test ${1}s found for removal"
        return 0
    fi

    for object in $objects
    do
        echo "Removing $1 $object..."
        if [ "$1" == "volume" ] || [ "$1" == "container" ]; then
            sudo docker $1 rm --force $object
        else
            sudo docker $1 rm $object
        fi
        echo -e "${BLUE}Removal of $1 $object completed${NC}"
    done
}


stack_to_rm=""
rm_stack_only=0
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in 
        -s|--rm-stack-only)
            rm_stack_only=1
            shift
            ;;

        -h|--help)
            usage
            exit 1
            ;;

        *)
            if [ -z "$stack_to_rm" ]; then
                stack_to_rm="$1"
            else
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -n "$stack_to_rm" ]; then
    match_prefix="$stack_to_rm"
else
    match_prefix="$TEST_STACK_PREFIX"
fi

rm_docker_objects "stack" "$match_prefix"
if [ $rm_stack_only -eq 1 ]; then
    exit 0
fi

rm_docker_objects "service" "$match_prefix"
rm_docker_objects "container" "$match_prefix"
rm_docker_objects "secret" "$match_prefix"
rm_docker_objects "network" "$match_prefix"
rm_docker_objects "volume" "$match_prefix"

exit 0
