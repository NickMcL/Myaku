#!/bin/bash
# Runs the test suites for the Myaku project.
# All this script does is launch the docker container that runs the tests.

cd "$(dirname "${BASH_SOURCE[0]}")"

sudo docker run -it --rm \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    -v "$(pwd):/test/myaku" \
    --name "test-runner" \
    --entrypoint "/test/start_test_runner.sh" \
    friedrice2/myaku_run-tests:dev "$@"
