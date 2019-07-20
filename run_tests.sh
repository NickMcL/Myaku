#!/bin/bash

RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
NC='\e[0m'


cleanup()
{
    if [ -n "$stack" ]; then
        echo "Removing stack $stack..."
        ./teardown_test_stack.sh --rm-stack-only > /dev/null
        echo -e "Removal of stack $stack completed"
    fi

    if [ "$test_status" == "Passed" ]; then
        echo -e "Overall test results: ${GREEN}ALL TESTS PASSED${NC}"
    elif [ "$test_status" == "Failed" ]; then
        echo -e "Overall test results: ${RED}TEST FAILURE${NC}"
    elif [ "$test_status" != "N/A" ]; then
        echo -e "Overall test results: ${YELLOW}TESTS DID NOT COMPLETE${NC}"
    fi
}
trap cleanup EXIT


error_handler()
{
    err_code=$?
    if [ "$test_status" == "Started" ]; then
        return $err_code
    fi

    lineno="$1"
    error_message="$2"
    if [ -n "$error_message" ]; then
        echo -e "${RED}run_tests: Error around $lineno:" \
            "$error_message${NC}" >&2
    else
        echo -e "${RED}run_tests: Error around $lineno${NC}" >&2
    fi
    exit 1
}
trap 'error_handler ${LINENO}' ERR


usage()
{
    test_status="N/A"
    cat << EOF
usage: run_tests.sh [<tag>] [-n|--no-cleanup] [-h|--help]

Runs all tests in a deployed Myaku docker stack.

By default, builds a new crawler.prod:test image with the current code in the
working directory to use for the tests.

If a tag is passed as a parameter, will use the existing crawler.prod:<tag>
image for the tests instead.

-n|--no-cleanup: By default, attempts to delete any docker objects from the
    test run or previous test runs to clean up, but if this option is set, will
    not attempt to delete any docker objects.

-h|--help: Outputs this message and exits.
EOF
}


test_status="NotStarted"
no_cleanup=0
image_tag=""
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in 
        -n|--no-cleanup)
            no_cleanup=1
            shift
            ;;

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

cd "test_scripts"
# Try to clean up any docker objects from previous tests.
if [ $no_cleanup -eq 0 ]; then
    echo "Cleaning up any previous test docker objects..."
    ./teardown_test_stack.sh > /dev/null
else
    echo "Skipped clean up of previous test docker objects"
fi

stack=$(./deploy_test_stack.sh "$image_tag")
if [ $? -ne 0 ] || [ -z "$stack" ]; then
    error_handler ${LINENO} "${RED}Test stack deployment failed${NC}"
fi
crawler_service="${stack}_crawler"

container_id=$(./get_container_id.sh "$crawler_service")
if [ $? -ne 0 ] || [ -z "$container_id" ]; then
    error_handler ${LINENO} \
        "${RED}Crawler container ID could not be obtained${NC}"
fi

echo -e "${BLUE}Running pytests for crawler in" \
    "$crawler_service container...${NC}"

test_status="Started"
sudo docker exec -t $container_id /bin/bash -c '$PYTHON_BIN -m pytest'
if [ $? -ne 0 ]; then
    echo -e "Test result for crawler: ${RED}FAILURE${NC}"
    test_status="Failed"
else
    echo -e "Test result for crawler: ${GREEN}PASSED${NC}"
    test_status="Passed"
fi

exit 0
