"""Tests for logging-related functions in myaku.utils."""

import functools
import glob
import logging
import os
import re
from typing import Callable, NamedTuple

import pytest

import myaku
from myaku import utils

LOG_MESSAGE_TEMPLATE = '{0} LOG TEST'
DEBUG_LOG_MESSAGE = LOG_MESSAGE_TEMPLATE.format('DEBUG')
INFO_LOG_MESSAGE = LOG_MESSAGE_TEMPLATE.format('INFO')
WARNING_LOG_MESSAGE = LOG_MESSAGE_TEMPLATE.format('WARNING')
ERROR_LOG_MESSAGE = LOG_MESSAGE_TEMPLATE.format('ERROR')
CRITICAL_LOG_MESSAGE = LOG_MESSAGE_TEMPLATE.format('CRITICAL')

LOG_REGEX_TEMPLATE = (
    r'^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d,\d\d\d:myaku:p\d+:t\d+:{0}: '
    + LOG_MESSAGE_TEMPLATE + '$'
)
LOG_MESSAGE_REGEX_MAP = {
    'd': re.compile(LOG_REGEX_TEMPLATE.format('DEBUG')),
    'i': re.compile(LOG_REGEX_TEMPLATE.format('INFO')),
    'w': re.compile(LOG_REGEX_TEMPLATE.format('WARNING')),
    'e': re.compile(LOG_REGEX_TEMPLATE.format('ERROR')),
    'c': re.compile(LOG_REGEX_TEMPLATE.format('CRITICAL'))
}

DEBUG_MAX_LOG_SIZE_TEST_VALUE = '10000'
INFO_MAX_LOG_SIZE_TEST_VALUE = '10000'
LOG_FILE_NAME_TEST_VALUE = 'test'


class LogEnvironment(NamedTuple):
    """Named tuple for log-related environment variable values.

    Attributes:
        toggle_func: Function for toggling logging on and off. Either
            utils.toggle_myaku_package_log or a functools.partial of it.
        filepath_base: The directory + base file name to use for writing log
            files.
        debug_max_size: Maximum total allowable size of the debug log files.
        info_max_size: Maximum total allowable size of the info log files.
    """
    toggle_func: Callable
    filepath_base: str
    debug_max_size: int
    info_max_size: int


@pytest.fixture
def custom_log_environment(monkeypatch, tmpdir):
    """Pytest fixture for a log environment with all custom settings."""
    os.chdir(tmpdir)
    log_dir = os.path.join(os.getcwd(), 'log/sub/dir')
    os.makedirs(log_dir)
    monkeypatch.setenv(myaku.LOG_DIR_ENV_VAR, log_dir)

    monkeypatch.setenv(
        utils._DEBUG_LOG_MAX_SIZE_ENV_VAR, DEBUG_MAX_LOG_SIZE_TEST_VALUE
    )
    monkeypatch.setenv(
        utils._INFO_LOG_MAX_SIZE_ENV_VAR, INFO_MAX_LOG_SIZE_TEST_VALUE
    )

    return LogEnvironment(
        functools.partial(
            utils.toggle_myaku_package_log,
            filename_base=LOG_FILE_NAME_TEST_VALUE
        ),
        os.path.join(log_dir, LOG_FILE_NAME_TEST_VALUE),
        int(DEBUG_MAX_LOG_SIZE_TEST_VALUE), int(INFO_MAX_LOG_SIZE_TEST_VALUE)
    )


@pytest.fixture
def default_log_environment(monkeypatch, tmpdir):
    """Pytest fixture for a log environment with pure default settings."""
    os.chdir(tmpdir)
    monkeypatch.delenv(myaku.LOG_DIR_ENV_VAR, False)
    monkeypatch.delenv(utils._DEBUG_LOG_MAX_SIZE_ENV_VAR, False)
    monkeypatch.delenv(utils._INFO_LOG_MAX_SIZE_ENV_VAR, False)

    return LogEnvironment(
        utils.toggle_myaku_package_log, os.path.join(os.getcwd(), 'myaku'),
        None, None
    )


def test_log_rotate(custom_log_environment, caplog):
    """Test rotation of log files by doing lots of logging."""
    custom_log_environment.toggle_func()
    log = logging.getLogger('myaku')

    debug_file_path = custom_log_environment.filepath_base + '.debug.log'
    info_file_path = custom_log_environment.filepath_base + '.info.log'
    log_dir = os.path.dirname(debug_file_path)
    log_dir_all_files_selector = os.path.join(log_dir, '*')

    for _ in range(custom_log_environment.debug_max_size // 10):
        log.debug(DEBUG_LOG_MESSAGE)

    debug_file_count = len(glob.glob(debug_file_path + '*'))
    info_file_count = len(glob.glob(info_file_path + '*'))
    file_count = len(glob.glob(log_dir_all_files_selector))
    assert debug_file_count == (utils._LOG_ROTATING_BACKUP_COUNT + 1)
    assert info_file_count == 1
    assert file_count == (utils._LOG_ROTATING_BACKUP_COUNT + 2)
    assert get_dir_size(log_dir) <= custom_log_environment.debug_max_size

    for _ in range(custom_log_environment.info_max_size // 10):
        log.info(INFO_LOG_MESSAGE)

    debug_file_count = len(glob.glob(debug_file_path + '*'))
    info_file_count = len(glob.glob(info_file_path + '*'))
    file_count = len(glob.glob(log_dir_all_files_selector))
    assert debug_file_count == (utils._LOG_ROTATING_BACKUP_COUNT + 1)
    assert info_file_count == (utils._LOG_ROTATING_BACKUP_COUNT + 1)
    assert file_count == ((utils._LOG_ROTATING_BACKUP_COUNT + 1) * 2)
    assert get_dir_size(log_dir) <= (
        custom_log_environment.debug_max_size
        + custom_log_environment.info_max_size
    )


def get_dir_size(dir_path):
    """Return size in bytes of all files in a directory without sub dirs."""
    return sum(
        os.path.getsize(f) for f in os.listdir(dir_path) if os.path.isfile(f)
    )


def test_log_and_raise(caplog):
    """Test utils.log_and_raise to make sure it logs and raises as expected."""
    class TestError(Exception):
        pass

    log = logging.getLogger('test')
    with pytest.raises(TestError) as exc_info:
        utils.log_and_raise(log, TestError, ERROR_LOG_MESSAGE)

    assert exc_info.type is TestError
    assert exc_info.value.args[0] == ERROR_LOG_MESSAGE
    assert len(caplog.records) == 1
    assert (
        caplog.record_tuples[0] == ('test', logging.ERROR, ERROR_LOG_MESSAGE)
    )


def test_toggle_myaku_package_log_on_default(default_log_environment, capsys):
    """Test enabling the package log with default settings."""
    assert_toggle_myaku_package_log_on(default_log_environment, capsys)


def test_toggle_myaku_package_log_on_custom(custom_log_environment, capsys):
    """Test enabling the package log with custom settings."""
    assert_toggle_myaku_package_log_on(custom_log_environment, capsys)


def test_toggle_myaku_package_log_off_default(
        default_log_environment, capsys
):
    """Test disabling the package log with default settings."""
    assert_toggle_myaku_package_log_off(default_log_environment, capsys)


def test_toggle_myaku_package_log_off_custom(custom_log_environment, capsys):
    """Test disabling the package log with custom settings."""
    assert_toggle_myaku_package_log_off(custom_log_environment, capsys)


def test_toggle_myaku_package_log_on_on_default(
        default_log_environment, capsys
):
    """Test enabling the package log twice in a row with default settings."""
    assert_toggle_myaku_package_log_on_on(default_log_environment, capsys)


def test_toggle_myaku_package_log_on_on_custom(
        custom_log_environment, capsys
):
    """Test enabling the package log twice in a row with custom settings."""
    assert_toggle_myaku_package_log_on_on(
        custom_log_environment, capsys, True
    )


def test_toggle_myaku_package_log_off_off_default(
        default_log_environment, capsys
):
    """Test disabling the package log twice in a row with default settings."""
    assert_toggle_myaku_package_log_off_off(default_log_environment, capsys)


def test_toggle_myaku_package_log_off_off_custom(
        custom_log_environment, capsys
):
    """Test disabling the package log twice in a row with custom settings."""
    assert_toggle_myaku_package_log_off_off(custom_log_environment, capsys)


def test_toggle_myaku_package_log_on_off_default(
        default_log_environment, capsys
):
    """Test enabling then disabling the package log with default settings."""
    assert_toggle_myaku_package_log_on_off(default_log_environment, capsys)


def test_toggle_myaku_package_log_on_off_custom(
        custom_log_environment, capsys
):
    """Test enabling then disabling the package log with custom settings."""
    assert_toggle_myaku_package_log_on_off(custom_log_environment, capsys)


def test_toggle_myaku_package_log_off_on_default(
        default_log_environment, capsys
):
    """Test disabling then enabling the package log with default settings."""
    assert_toggle_myaku_package_log_off_on(default_log_environment, capsys)


def test_toggle_myaku_package_log_off_on_custom(
        custom_log_environment, capsys
):
    """Test disabling then enabling the package log with custom settings."""
    assert_toggle_myaku_package_log_off_on(custom_log_environment, capsys)


def test_toggle_myaku_package_log_on_off_on_default(
        default_log_environment, capsys
):
    """Test enabling, disabling, then re-enabling log - default settings."""
    assert_toggle_myaku_package_log_on_off_on(default_log_environment, capsys)


def test_toggle_myaku_package_log_on_off_on_custom(
        custom_log_environment, capsys
):
    """Test enabling, disabling, then re-enabling log - custom settings."""
    assert_toggle_myaku_package_log_on_off_on(
        custom_log_environment, capsys, True
    )


def test_toggle_myaku_package_log_off_on_off_default(
        default_log_environment, capsys
):
    """Test disabling, enabling, then re-disabling log - default settings."""
    assert_toggle_myaku_package_log_off_on_off(
        default_log_environment, capsys
    )


def test_toggle_myaku_package_log_off_on_off_custom(
        custom_log_environment, capsys
):
    """Test disabling, enabling, then re-disabling log - custom settings."""
    assert_toggle_myaku_package_log_off_on_off(custom_log_environment, capsys)


def assert_toggle_myaku_package_log_on(log_environment, capsys):
    """Test enabling the Myaku package log."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(True)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )


def assert_toggle_myaku_package_log_off(log_environment, capsys):
    """Test disabling the Myaku package log."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(False)
    log_all_levels_once(log)

    assert_no_logs(log_environment, capsys)


def assert_toggle_myaku_package_log_on_on(
        log_environment, capsys, enable_no_truncate=False
):
    """Test enabling the Myaku package log twice in a row.

    If enable_no_truncate is True, it is asserted that each enabling of the
    package log does not truncate the log files.
    """
    log = logging.getLogger('myaku')
    log_environment.toggle_func(True)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )

    log_environment.toggle_func(True)
    log_all_levels_once(log)

    if enable_no_truncate:
        assert_log_existence(
            ['d', 'i', 'w', 'e', 'c'] * 2, log_environment, capsys, True
        )
    else:
        assert_log_existence(
            ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
        )


def assert_toggle_myaku_package_log_off_off(log_environment, capsys):
    """Test disabling the Myaku package log twice in a row."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(False)
    log_all_levels_once(log)
    log_environment.toggle_func(False)
    log_all_levels_once(log)

    assert_no_logs(log_environment, capsys)


def assert_toggle_myaku_package_log_on_off(log_environment, capsys):
    """Test enabling then disabling the Myaku package log."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(True)
    log_all_levels_once(log)
    log_environment.toggle_func(False)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )


def assert_toggle_myaku_package_log_off_on(log_environment, capsys):
    """Test disabling then enabling the Myaku package log."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(False)
    log_all_levels_once(log)
    log_environment.toggle_func(True)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )


def assert_toggle_myaku_package_log_on_off_on(
    log_environment, capsys, enable_no_truncate=False
):
    """Test enabling, disabling, then re-enabling the Myaku package log.

    If enable_no_truncate is True, it is asserted that each enabling of the
    package log does not truncate the log files.
    """
    log = logging.getLogger('myaku')
    log_environment.toggle_func(True)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )

    log_environment.toggle_func(False)
    log_all_levels_once(log)
    log_environment.toggle_func(True)
    log_all_levels_once(log)

    if enable_no_truncate:
        assert_log_existence(
            ['d', 'i', 'w', 'e', 'c'] * 2, log_environment, capsys, True
        )
    else:
        assert_log_existence(
            ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
        )


def assert_toggle_myaku_package_log_off_on_off(log_environment, capsys):
    """Test disabling, enabling, then re-disabling the Myaku package log."""
    log = logging.getLogger('myaku')
    log_environment.toggle_func(False)
    log_all_levels_once(log)
    log_environment.toggle_func(True)
    log_all_levels_once(log)
    log_environment.toggle_func(False)
    log_all_levels_once(log)

    assert_log_existence(
        ['d', 'i', 'w', 'e', 'c'], log_environment, capsys
    )


def log_all_levels_once(log):
    """Log one debug, info, warning, error, and critical entry for the log."""
    log.debug(DEBUG_LOG_MESSAGE)
    log.info(INFO_LOG_MESSAGE)
    log.warning(WARNING_LOG_MESSAGE)
    log.error(ERROR_LOG_MESSAGE)
    log.critical(CRITICAL_LOG_MESSAGE)


def assert_log_existence(
    log_entries, log_environment, capsys, stderr_has_half=False
):
    """Assert that the given log entries exist in all expected locations.

    Args:
        log_entries: A list of some combination of the characters 'd', 'i',
            'w', 'e', or 'c' that represents an ordering of debug, info,
            warning, error, and critical log messages that should exist.
        log_environment: A LogEnvironment object with the current log
            environment values set.
        capsys: The system capture pytest fixture for the current test.
        stderr_has_half: If True, it will be asserted that stderr has only the
            frist half of the given log entry list.
    """
    info_log_filepath = log_environment.filepath_base + '.info.log'
    debug_log_filepath = log_environment.filepath_base + '.debug.log'
    assert os.path.exists(info_log_filepath)
    assert os.path.exists(debug_log_filepath)

    stderr_lines = capsys.readouterr().err.splitlines()
    with open(info_log_filepath) as info_file:
        info_file_lines = info_file.readlines()
    with open(debug_log_filepath) as debug_file:
        debug_file_lines = debug_file.readlines()

    nondebug_entries = [e for e in log_entries if e != 'd']
    if stderr_has_half:
        assert len(stderr_lines) == len(nondebug_entries) / 2
    else:
        assert len(stderr_lines) == len(nondebug_entries)
    assert len(info_file_lines) == len(nondebug_entries)
    assert len(debug_file_lines) == len(log_entries)

    for i, entry in enumerate(nondebug_entries):
        entry_regex = LOG_MESSAGE_REGEX_MAP[entry]
        assert re.match(entry_regex, info_file_lines[i]) is not None
        if not stderr_has_half or i < len(nondebug_entries) / 2:
            assert re.match(entry_regex, stderr_lines[i]) is not None

    for i, entry in enumerate(log_entries):
        entry_regex = LOG_MESSAGE_REGEX_MAP[entry]
        assert re.match(entry_regex, debug_file_lines[i]) is not None


def assert_no_logs(log_environment, capsys):
    """Assert that no logs were written in any log locations."""
    info_log_filepath = log_environment.filepath_base + '.info.log'
    debug_log_filepath = log_environment.filepath_base + '.debug.log'

    assert len(capsys.readouterr().err) == 0
    assert os.path.exists(info_log_filepath) is False
    assert os.path.exists(debug_log_filepath) is False
