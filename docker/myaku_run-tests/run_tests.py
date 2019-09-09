"""Runs all of the test suites for the Myaku project."""

import argparse
import logging
import os
import random
import string
import subprocess
import sys
import time
from typing import Any, Dict, List, NamedTuple

import colorlog
import docker
from docker.models.containers import Container

_log = logging.getLogger(__name__)

# _LOGGING_FORMAT = '%(asctime)s:%(levelname)s: %(message)s'
_LOGGING_FORMAT = '%(log_color)s%(message)s'
RESULT = 25  # Test result log level

_MYAKU_PROJECT_DIR_ENV_VAR = 'MYAKU_PROJECT_DIR'

_TEST_STACK_NAME_PREFIX = 'myaku_test_'

# Docker objects that can be removed by getting them from a list() with the
# docker client and then calling remove().
# Containers is not on this list because list() must be called with the all
# option to get all containers.
_NORMAL_REMOVE_DOCKER_OBJECTS = [
    'volumes',
    'networks',
    'configs',
    'secrets',
    'services'
]

# Shell color codes
_RED = '\033[31m'
_GREEN = '\033[32m'
_ENDC = '\033[0m'

# Script arg parser setup
arg_parser = argparse.ArgumentParser(
    description='Runs all of the test suites for the Myaku project.'
)
arg_parser.add_argument(
    '-e', '--use-existing-images',
    action='store_true',
    help=(
        'Instead of building new prod images for the tests, use the existing '
        'images specified in the current base docker compose file '
        '(./docker/docker-compose.yml).'
    )
)
arg_parser.add_argument(
    '-c', '--clean-only',
    action='store_true',
    help=(
        'Removes all test docker objects including volumes and exits without '
        'running any tests.'
    )
)


def red_text(text: str) -> str:
    """Makes text green in console output."""
    return _RED + text + _ENDC


def green_text(text: str) -> str:
    """Makes text green in console output."""
    return _GREEN + text + _ENDC


class DockerImageBuildSpec(NamedTuple):
    """Specification for how to build a docker image.

    Attributes:
        image_name: Name to use for the image. Should not include the tag.
        dockerfile_path: Path to the dockerfile to build the image.
    """
    image_name: str
    dockerfile_path: str


class TestMyakuStack(object):
    """A Myaku docker stack for testing use."""

    # Number of characters to use in the randomly-generated portion of the test
    # stack name.
    _STACK_NAME_RAND_SECTION_LEN = 8

    # Seconds to wait for all of the containers for the stack to be running
    # before raising an error.
    _CONTAINER_STARTUP_TIMEOUT = 5

    # Paths are relative to the Myaku project root directory.
    _STACK_IMAGE_BUILD_SPECS = [
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_crawler',
            dockerfile_path='docker/myaku_crawler/Dockerfile.crawler'
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_rescore',
            dockerfile_path='docker/myaku_rescore/Dockerfile.rescore'
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_web',
            dockerfile_path='docker/myaku_web/Dockerfile.myakuweb'
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_redis.first-page-cache',
            dockerfile_path=(
                'docker/myaku_redis.first-page-cache/'
                'Dockerfile.redis.first-page-cache'
            )
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_nginx.reverseproxy',
            dockerfile_path=(
                'docker/myaku_nginx.reverseproxy/Dockerfile.nginx.reverseproxy'
            )
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/myaku_mongo.crawldb',
            dockerfile_path=(
                'docker/myaku_mongo.crawldb/Dockerfile.mongo.crawldb'
            )
        ),
        DockerImageBuildSpec(
            image_name='friedrice2/mongobackup',
            dockerfile_path='docker/mongobackup/Dockerfile.mongobackup'
        ),
    ]

    def __init__(self, use_existing_images: bool) -> None:
        """Deploys a new Myaku docker stack for testing.

        Args:
            use_existing_images: Instead of building new prod images for the
                tests, use the existing images specified in the current base
                docker compose file (./docker/docker-compose.yml).
        """
        self._use_existing_images = use_existing_images
        self._docker_client = docker.from_env()
        self._myaku_project_dir = os.environ[_MYAKU_PROJECT_DIR_ENV_VAR]

        rand_section = ''.join(random.choices(
            string.hexdigits.lower(),
            k=self._STACK_NAME_RAND_SECTION_LEN
        ))
        self.stack_name = f'myaku_test_{rand_section}'

        try:
            if use_existing_images:
                self._deploy_stack_using_existing_images()
            else:
                self._build_stack_images()
                self._deploy_stack_using_test_images()
        except BaseException:
            # Make sure we remove any part of stack that got deployed if there
            # was any error during the deployment process.
            self.teardown()
            raise

    def __enter__(self) -> 'TestMyakuStack':
        """Builds and deploys a Myaku test stack."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Tears down the deployed test stack."""
        self.teardown()

    def teardown(self) -> None:
        """Tears down the deployed test stack.

        Does NOT remove the volumes for the test stack.
        """
        _log.debug('Removing %s test stack...', self.stack_name)
        subprocess.run(
            ['docker', 'stack', 'rm', self.stack_name],
            capture_output=True, check=True
        )

    def _build_stack_images(self) -> None:
        """Builds the test prod images to use in the stack."""
        for image_spec in self._STACK_IMAGE_BUILD_SPECS:
            tagged_image_name = image_spec.image_name + ':test'
            abs_dockerfile_path = os.path.join(
                self._myaku_project_dir, image_spec.dockerfile_path
            )

            build_cmd = [
                'docker', 'build',
                '-f', abs_dockerfile_path,
                '-t', tagged_image_name,
                '--target', 'prod',
                self._myaku_project_dir
            ]

            _log.debug('Building %s image...', tagged_image_name)
            subprocess.run(
                build_cmd, capture_output=True, check=True, text=True
            )

    def _get_no_image_test_compose(self) -> str:
        """Gets the test docker compose file data without the image: lines.

        The file data can then be used with the base docker compose file to run
        the Myaku stack with the current prod images.
        """
        test_compose_filepath = os.path.join(
            self._myaku_project_dir, 'docker/docker-compose.test.yml'
        )
        with open(test_compose_filepath, 'r') as test_compose_file:
            test_compose_lines = test_compose_file.readlines()

        no_image_test_compose_lines = []
        for line in test_compose_lines:
            if 'image: ' not in line:
                no_image_test_compose_lines.append(line)

        return ''.join(no_image_test_compose_lines)

    def _deploy_stack_using_existing_images(self) -> None:
        """Deploys the Myaku test stack using existing images.

        The images specified in the current base docker compose file
        (./docker/docker-compose.yml) are used.
        """
        _log.debug(
            'Using existing images specified in docker/docker-compose.yml'
        )
        no_image_test_compose = self._get_no_image_test_compose()
        base_compose_filepath = os.path.join(
            self._myaku_project_dir, 'docker/docker-compose.yml'
        )

        deploy_cmd = [
            'docker', 'stack', 'deploy',
            '-c', base_compose_filepath, '-c', '-',
            self.stack_name
        ]

        _log.debug('Deploying Myaku test stack %s...', self.stack_name)
        subprocess.run(
            deploy_cmd, input=no_image_test_compose, capture_output=True,
            check=True, text=True
        )
        self._wait_for_all_containers_running()
        _log.info('Stack %s created', self.stack_name)

    def _deploy_stack_using_test_images(self) -> None:
        """Deploys the Myaku test stack using newly built test prod images."""
        _log.debug('Using newly built test images')
        test_compose_filepath = os.path.join(
            self._myaku_project_dir, 'docker/docker-compose.test.yml'
        )
        base_compose_filepath = os.path.join(
            self._myaku_project_dir, 'docker/docker-compose.yml'
        )

        deploy_cmd = [
            'docker', 'stack', 'deploy',
            '-c', base_compose_filepath,
            '-c', test_compose_filepath,
            self.stack_name
        ]

        _log.debug('Deploying Myaku test stack %s...', self.stack_name)
        subprocess.run(
            deploy_cmd, capture_output=True, check=True, text=True
        )
        self._wait_for_all_containers_running()
        _log.info('Stack %s created', self.stack_name)

    def _wait_for_all_containers_running(self) -> None:
        """Waits for all containers for the test stack to be running.

        Deploying a docker stack creates all the services for the stack, but it
        can still take some time after the services are created for all of
        their containers to be in a running state.

        This function will wait until all services for the stack have their
        containers in a running state.

        Will timeout and raise an error if _CONTAINER_STARTUP_TIMEOUT seconds
        have passed and not all of the containers are in the running state.
        """
        _log.debug(
            'Waiting for stack %s containers to start...', self.stack_name
        )
        waited_secs = 0
        while waited_secs < self._CONTAINER_STARTUP_TIMEOUT:
            services = self._docker_client.services.list(
                filters={'name': self.stack_name}
            )
            all_running = True
            for service in services:
                for task in service.tasks():
                    if ('Status' not in task
                            or 'State' not in task['Status']
                            or task['Status']['State'] != 'running'):
                        all_running = False
                        break
                if not all_running:
                    break

            if all_running:
                break
            time.sleep(1)
            waited_secs += 1

        if not all_running:
            raise RuntimeError(
                f'Test stack {self.stack_name} containers not all running '
                f'after timeout of {self._CONTAINER_STARTUP_TIMEOUT} seconds'
            )
        _log.debug('Stack %s containers all started', self.stack_name)

    def get_crawler_container(self) -> Container:
        """Gets the crawler service container for this test stack."""
        for container in self._docker_client.containers.list():
            if container.name.startswith(self.stack_name + '_crawler'):
                return container

        raise RuntimeError(
            f'Could not get crawler container for {self.stack_name} stack'
        )


class TestRunner(object):
    """Runs the Myaku test suites and tracks their results."""

    def __init__(self, use_existing_images: bool) -> None:
        """Sets up the test runner to track test results.

        Args:
            use_existing_images: Instead of building new prod images for the
                tests, use the existing images specified in the current base
                docker compose file (./docker/docker-compose.yml).
        """
        self._use_existing_images = use_existing_images
        self._test_results: Dict[str, str] = {}

    def run_crawler_tests(self) -> None:
        """Runs all of the tests for the crawler service."""
        with TestMyakuStack(self._use_existing_images) as test_stack:
            crawler_container = test_stack.get_crawler_container()
            self._run_crawler_unit_tests(crawler_container)
            self._run_crawler_end_to_end_test(crawler_container)

    def _run_crawler_unit_tests(self, container: Container) -> None:
        """Runs the unit test suite for the crawler.

        Args:
            container: The crawler container to run the tests in.
        """
        _log.info(
            '\nRunning unit pytests for crawler in %s container...',
            container.name.split('.')[0]
        )
        exec_cmd = [
            'docker', 'exec', '-it', container.short_id,
            '/bin/bash', '-c', '$PYTHON_BIN -m pytest myaku/tests/unit'
        ]
        completed = subprocess.run(exec_cmd, text=True)

        if completed.returncode == 0:
            _log.log(
                RESULT, 'Test result for crawler unit: ' + green_text('PASSED')
            )
            self._test_results['Crawler unit'] = 'PASSED'
        else:
            _log.log(
                RESULT, 'Test result for crawler unit: ' + red_text('FAILED')
            )
            self._test_results['Crawler unit'] = 'FAILED'

    def _run_crawler_end_to_end_test(self, container: Container) -> None:
        """Runs the end to end test for the crawler.

        Args:
            container: The crawler container to run the tests in.
        """
        _log.info(
            '\nRunning end-to-end pytest for crawler in %s container...',
            container.name.split('.')[0]
        )
        exec_cmd = [
            'docker', 'exec', '-it', container.short_id,
            '/bin/bash', '-c', '$PYTHON_BIN -m pytest myaku/tests/end_to_end'
        ]
        completed = subprocess.run(exec_cmd, text=True)

        if completed.returncode == 0:
            _log.log(
                RESULT,
                'Test result for crawler end-to-end: ' + green_text('PASSED')
            )
            self._test_results['Crawler end-to-end'] = 'PASSED'
        else:
            _log.log(
                RESULT,
                'Test result for crawler end-to-end: ' + red_text('FAILED')
            )
            self._test_results['Crawler end-to-end'] = 'FAILED'

    def log_results(self) -> None:
        """Logs the overall test results."""
        failed_tests = []
        for test_name, result in self._test_results.items():
            if result == 'FAILED':
                failed_tests.append(test_name)

        if len(failed_tests) == 0:
            _log.log(
                RESULT,
                '\nOverall test results: ' + green_text('ALL TESTS PASSED')
            )
        else:
            _log.log(
                RESULT, '\nOverall test results: ' + red_text('TEST FAILURE')
            )


def setup_logger() -> logging.Logger:
    """Sets up the logger for the script.

    Writes the log to both stderr.

    Returns:
        The setup logger to use for the script.
    """
    logger = logging.getLogger('run_tests')
    logger.setLevel(logging.DEBUG)
    logging.addLevelName(RESULT, 'RESULT')

    stream_handler = colorlog.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(colorlog.ColoredFormatter(
        _LOGGING_FORMAT,
        reset=True,
        log_colors={
            'DEBUG': '',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',

            # Leave uncolored so only the PASSED/FAILED text inside the result
            # message can be colored.
            'RESULT': '',
        }
    ))
    logger.addHandler(stream_handler)

    return logger


def get_test_stacks() -> List[str]:
    """Gets a list of all of the currently live test stacks.

    A stack is considered a test stack if its name begins with
    _TEST_STACK_NAME_PREFIX.
    """
    completed = subprocess.run(
        ['docker', 'stack', 'ls'], capture_output=True, check=True, text=True
    )

    # First line of stdout is the column headers, so skip first line
    test_stacks = []
    for line in completed.stdout.splitlines()[1:]:
        stack_name = line.split()[0]
        if stack_name.startswith(_TEST_STACK_NAME_PREFIX):
            test_stacks.append(stack_name)

    return test_stacks


def attempt_remove_docker_obj(docker_obj: Any) -> None:
    """Attempts to remove the given docker object.

    Can remove any docker object as long as it has a remove() method.

    If the attempt to remove was unsuccessful, logs the reason as a warning and
    takes no other action.
    """
    try:
        docker_obj.remove()
    except docker.errors.APIError as e:
        _log.warning(
            'Unable to remove docker object %s due to error: %s', docker_obj, e
        )


def teardown_test_stacks() -> None:
    """Attempts to removes any docker objects created by test stacks.

    Attempts to remove all stacks, services, containers, secrets, configs,
    networks, and volumes created by test stacks.

    If a test stack object is unable to be removed, logs a warning and
    continues.
    """
    test_stacks = get_test_stacks()
    for test_stack in test_stacks:
        _log.debug('Removing %s test stack...', test_stack)
        subprocess.run(
            ['docker', 'stack', 'rm', test_stack],
            capture_output=True, check=True
        )

    docker_client = docker.from_env()
    for container in docker_client.containers.list(all=True):
        if container.name.startswith(_TEST_STACK_NAME_PREFIX):
            attempt_remove_docker_obj(container)

    for obj_type in _NORMAL_REMOVE_DOCKER_OBJECTS:
        for obj in getattr(docker_client, obj_type).list():
            if obj.name.startswith(_TEST_STACK_NAME_PREFIX):
                attempt_remove_docker_obj(obj)


def main() -> None:
    script_args = arg_parser.parse_args()

    _log.debug('Cleaning up any previous test docker objects...')
    teardown_test_stacks()
    if script_args.clean_only:
        sys.exit(0)

    test_runner = TestRunner(script_args.use_existing_images)
    test_runner.run_crawler_tests()

    test_runner.log_results()


if __name__ == '__main__':
    _log = setup_logger()
    try:
        main()
    except Exception:
        _log.exception('Unhandled exception in main')
        raise
