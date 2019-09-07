#!/bin/bash

RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
NC='\e[0m'


usage()
{
    test_status="N/A"
    cat << EOF
usage: run_tests.sh [-e|--use-existing-images] [-n|--no-cleanup] [-h|--help]

Runs all tests in a deployed Myaku docker stack.

By default, builds new prod images tagged as "test" for each service with the
current code in the working directory to use for the tests.

-e|--use-existing-images: Instead of building new prod images for the tests,
use the existing images specified in the current prod docker compose file
(./docker/docker-compose.yml).

-n|--no-cleanup: By default, attempts to delete any docker objects from the
    test run or previous test runs to clean up, but if this option is set, will
    not attempt to delete any docker objects.

-h|--help: Outputs this message and exits.
EOF
}


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


test_status="NotStarted"
no_cleanup=0
use_existing_images_flag=""
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in 
        -e|--use-existing-images)
            use_existing_images_flag="-e"
            shift
            ;;

        -n|--no-cleanup)
            no_cleanup=1
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

cd "test_scripts"
# Try to clean up any docker objects from previous tests.
if [ $no_cleanup -eq 0 ]; then
    echo "Cleaning up any previous test docker objects..."
    ./teardown_test_stack.sh > /dev/null
else
    echo "Skipped clean up of previous test docker objects"
fi

stack=$(./deploy_test_stack.sh $use_existing_images_flag)
if [ $? -ne 0 ] || [ -z "$stack" ]; then
    error_handler ${LINENO} "${RED}Test stack deployment failed${NC}"
fi
crawler_service="${stack}_crawler"

container_id=$(./get_container_id.sh "$crawler_service")
if [ $? -ne 0 ] || [ -z "$container_id" ]; then
    error_handler ${LINENO} \
        "${RED}Crawler container ID could not be obtained${NC}"
fi

test_status="Started"
echo -e "\n${BLUE}Running unit pytests for crawler in" \
    "$crawler_service container...${NC}"
sudo docker exec -it $container_id /bin/bash -c \
    '$PYTHON_BIN -m pytest myaku/tests/unit'
if [ $? -ne 0 ]; then
    echo -e "Test result for crawler unit: ${RED}FAILURE${NC}"
    test_status="Failed"
    exit 1
else
    echo -e "Test result for crawler unit: ${GREEN}PASSED${NC}"
fi

echo -e "\n${BLUE}Running end-to-end pytest for crawler in" \
    "$crawler_service container...${NC}"
sudo docker exec -it $container_id /bin/bash -c \
    '$PYTHON_BIN -m pytest -vv myaku/tests/end_to_end'
if [ $? -ne 0 ]; then
    echo -e "Test result for crawler end-to-end: ${RED}FAILURE${NC}"
    test_status="Failed"
    exit 1
else
    echo -e "Test result for crawler end-to-end: ${GREEN}PASSED${NC}"
fi

echo
test_status="Passed"
exit 0
