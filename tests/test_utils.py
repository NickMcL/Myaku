"""Tests for non-logging-related function in reibun.utils."""

import copy
import pytest
import os
from dataclasses import dataclass
from typing import List, NamedTuple, TypeVar

import reibun.utils as utils
from reibun.errors import EnvironmentNotSetError

TEST_ENV_VAR = 'TEST_ENV_VAR'

T = TypeVar('T')


@dataclass
class UnhashableDataClass(object):
    """Explicitly unhashable dataclass for testing.

    Used for testing functions that must work with unhashable objects.
    """
    number: int
    string: str
    num_list: List[int]

    __hash__ = None


class BeforeAfterLists(NamedTuple):
    """Stores the before and after values for an operation."""
    before: List[T]
    after: List[T]


obj1 = UnhashableDataClass(1, 'cat', [1, 2])
obj1_same = obj1
obj1_eq = UnhashableDataClass(1, 'cat', [1, 2])
obj1_copy = copy.copy(obj1)
obj2 = UnhashableDataClass(1, 'dog', [1, 2])
obj3 = UnhashableDataClass(1, 'dog', [1, 5])
obj4 = UnhashableDataClass(1, 'dog', [1])

UNIQUE_BEFORE_AFTERS = [
    BeforeAfterLists([], []),
    BeforeAfterLists([obj1], [obj1]),
    BeforeAfterLists([obj1_eq, obj1], [obj1_eq]),
    BeforeAfterLists(
        [obj1, obj1_same, obj1_eq, obj1_copy, obj2, obj3, obj4, obj2],
        [obj1, obj2, obj3, obj4]
    ),
    BeforeAfterLists(
        [obj2, obj1, obj3, obj1, obj4, obj1_eq, obj4],
        [obj2, obj1, obj3, obj4]
    ),
    BeforeAfterLists(
        [obj2, obj3, obj3, obj1_same, obj1_copy],
        [obj2, obj3, obj1_same]
    ),
    BeforeAfterLists(
        [obj3, obj3, obj3, obj3, obj3, obj2, obj3, obj3, obj4],
        [obj3, obj2, obj4]
    ),
    BeforeAfterLists(
        [obj4, obj3, obj2, obj1] * 20,
        [obj4, obj3, obj2, obj1]
    ),
]


def test_unique_unhashable():
    """Tests utils.unique with various lists of an unhashable object."""
    for before_after in UNIQUE_BEFORE_AFTERS:
        after = utils.unique(before_after.before)
        assert len(after) == len(before_after.after)

        # Use id for comparison to ensure that the first occurrence of each
        # object with a given value is the unique object for that value in the
        # after list.
        for i, obj in enumerate(after):
            assert id(obj) == id(before_after.after[i])


def test_get_value_from_enviroment_variable_set(monkeypatch):
    """Test get_value_from_environment_variable with a set env var."""
    monkeypatch.setenv(TEST_ENV_VAR, 'TestString')
    value = utils.get_value_from_environment_variable(TEST_ENV_VAR, 'test')
    assert value == 'TestString'


def test_get_value_from_enviroment_variable_not_set(monkeypatch):
    """Test get_value_from_enviroment_variable with no set env var."""
    monkeypatch.delenv(TEST_ENV_VAR, False)
    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_variable(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'not set' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]


def test_get_value_from_enviroment_variable_empty(monkeypatch):
    """Test get_value_from_environment_variable with empty env var."""
    monkeypatch.setenv(TEST_ENV_VAR, "")
    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_variable(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'set but empty' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]


def test_get_value_from_environment_file_all_set(monkeypatch, tmpdir):
    """Test get_value_from_environment_file with set var and file."""
    test_file_path = os.path.join(tmpdir, 'test.txt')
    monkeypatch.setenv(TEST_ENV_VAR, test_file_path)
    with open(test_file_path, 'w') as f:
        f.write('TestString')

    value = utils.get_value_from_environment_file(TEST_ENV_VAR, 'test')
    assert value == 'TestString'


def test_get_value_from_enviroment_file_var_not_set(monkeypatch):
    """Test get_value_from_environment_file with no set env var."""
    monkeypatch.delenv(TEST_ENV_VAR, False)
    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_file(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'not set' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]


def test_get_value_from_enviroment_file_var_empty(monkeypatch):
    """Test get_value_from_environment_file with empty env var."""
    monkeypatch.setenv(TEST_ENV_VAR, "")
    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_file(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'set but empty' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]


def test_get_value_from_enviroment_file_no_file(monkeypatch, tmpdir):
    """Test get_value_from_environment_file with no file at the var path."""
    test_file_path = os.path.join(tmpdir, 'test.txt')
    monkeypatch.setenv(TEST_ENV_VAR, test_file_path)
    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_file(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'not exist' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]


def test_get_value_from_enviroment_file_file_empty(monkeypatch, tmpdir):
    """Test get_value_from_environment_file with empty file at the var path."""
    test_file_path = os.path.join(tmpdir, 'test.txt')
    monkeypatch.setenv(TEST_ENV_VAR, test_file_path)
    with open(test_file_path, 'w') as f:
        f.write('')

    with pytest.raises(EnvironmentNotSetError) as exc_info:
        utils.get_value_from_environment_file(TEST_ENV_VAR, 'test')
    assert exc_info.type is EnvironmentNotSetError
    assert 'is empty' in exc_info.value.args[0]
    assert 'test' in exc_info.value.args[0]
