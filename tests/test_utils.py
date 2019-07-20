"""Tests for non-logging-related function in myaku.utils."""

import copy
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, NamedTuple, TypeVar

import pytest
import pytz

import myaku.utils as utils
from myaku.errors import EnvironmentNotSetError

TEST_ENV_VAR = 'TEST_ENV_VAR'

T = TypeVar('T')

# The spacing and new line placement for all of the following sample Japanese
# sentences strings looks weird, but it is all very intentional for testing.
SAMPLE_JPN_SENTENCES_CONSEC_PUNC = """???？
？?！！!。。
おいおい？？？
"""

SAMPLE_JPN_SENTENCES_CONSEC_PUNC_ENDS = [12, 20]

SAMPLE_JPN_SENTENCE_NO_PUNC = "こんにちは"
SAMPLE_JPN_SENTENCE_NO_PUNC_ENDS = [4]

SAMPLE_JPN_SENTENCES_SHORT = """
「オイラは神だぞ」
「それはないだろう」
"""

SAMPLE_JPN_SENTENCES_SHORT_ENDS = [0, 10, 21]

SAMPLE_JPN_SENTENCES_LONG = """今日も暑いな。このままずっと部屋に引きこもるか？？
それとも、新たな冒険を始めようか？まさかね！
「そういうことできないよ」
ここにネコがいるから、ここに残ります!それ以外の理由が必要ないよね?
まぁ、それはそれで。ちょっとお腹が空いてきました！！！ご飯は何にするかな？
それは一大事だね"""

SAMPLE_JPN_SENTENCES_LONG_ENDS = [
    6, 25, 42, 48, 62, 81, 97, 107, 124, 135, 143
]


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


def assert_sentence_start_ends(text, ends):
    """Asserts find_jpn_sentence_(start|end) works for all of the text.

    This is done by checking that the correct sentence start and end is given
    when the functions are run on every character in the text.

    Args:
        text: A string of text to use for the test.
        ends: The indexes of the ending character of every sentence in text in
            ascending order.
    """
    sentence_start = 0
    sentence_end = ends[0]
    end_index = 0

    for index, _ in enumerate(text):
        if index > sentence_end:
            end_index += 1
            sentence_start = index
            sentence_end = ends[end_index]

        assert utils.find_jpn_sentence_start(text, index) == sentence_start
        assert utils.find_jpn_sentence_end(text, index) == sentence_end


def test_find_jpn_setence_start_end_consec_punc():
    """Tests find_jpn_setence_(start|end) with consecutive punctuation."""
    assert_sentence_start_ends(
        SAMPLE_JPN_SENTENCES_CONSEC_PUNC, SAMPLE_JPN_SENTENCES_CONSEC_PUNC_ENDS
    )


def test_find_jpn_setence_start_end_no_punc():
    """Tests find_jpn_setence_(start|end) with no punctuation."""
    assert_sentence_start_ends(
        SAMPLE_JPN_SENTENCE_NO_PUNC, SAMPLE_JPN_SENTENCE_NO_PUNC_ENDS
    )


def test_find_jpn_setence_start_end_short():
    """Tests find_jpn_setence_(start|end) with short, simple text."""
    assert_sentence_start_ends(
        SAMPLE_JPN_SENTENCES_SHORT, SAMPLE_JPN_SENTENCES_SHORT_ENDS
    )


def test_find_jpn_setence_start_end_long():
    """Tests find_jpn_setence_(start|end) with long, complex text."""
    assert_sentence_start_ends(
        SAMPLE_JPN_SENTENCES_LONG, SAMPLE_JPN_SENTENCES_LONG_ENDS
    )


def test_tuple_or_none():
    """Tests that tuple_or_none handles tuple conversion and None."""
    tuple_from_list = utils.tuple_or_none([1, 2, 3])
    tuple_from_dict = utils.tuple_or_none({'a': 1, 'b': 2, 'c': 3}.items())
    tuple_from_none = utils.tuple_or_none(None)

    assert isinstance(tuple_from_list, tuple)
    assert tuple_from_list == (1, 2, 3)
    assert isinstance(tuple_from_dict, tuple)
    assert tuple_from_dict == (('a', 1), ('b', 2), ('c', 3))
    assert tuple_from_none is None


def test_convert_jst_to_utc():
    """Tests converting JST datetimes to UTC with convert_jst_to_utc.

    JST is always UTC+9:00. Japan does not do daylight savings time.
    """
    dt_no_minutes = datetime(2018, 5, 24, 20, 0, 0)
    dt_with_minutes = datetime(2019, 6, 24, 2, 22, 32, 145)
    dt_with_year_change = datetime(2019, 12, 31, 22, 47, 8)
    jst_to_utc_offset = timedelta(hours=-9)

    for dt in [dt_no_minutes, dt_with_minutes, dt_with_year_change]:
        converted_dt = utils.convert_jst_to_utc(dt)
        offset_dt = dt + jst_to_utc_offset
        assert offset_dt.year == converted_dt.year
        assert offset_dt.month == converted_dt.month
        assert offset_dt.hour == converted_dt.hour
        assert offset_dt.minute == converted_dt.minute
        assert offset_dt.second == converted_dt.second
        assert offset_dt.microsecond == converted_dt.microsecond

        assert converted_dt.tzinfo == pytz.utc


def test_get_alnum_count():
    """Tests get_alnum_count on various strings."""
    empty = ''
    assert utils.get_alnum_count(empty) == 0

    all_punc = '..！？？？、。!!@?&$*#)@(*&$@_(*(**()--+'
    assert utils.get_alnum_count(all_punc) == 0

    all_alnum = 'dsjaIWUEIRUEH213890suiayfdsiu88888AAAs'
    assert utils.get_alnum_count(all_alnum) == len(all_alnum)

    all_whitespace = '  \n\t  \n  '
    assert utils.get_alnum_count(all_whitespace) == 0

    mixed = 'Ads?!Oh,my not those!^\n'
    assert utils.get_alnum_count(mixed) == 15


def test_normalize_char_width():
    """Tests normalize_char_width with half and full width chars."""
    all_half_kata = 'ﾃｽﾄﾔｯﾀﾈｫｫ'
    assert utils.normalize_char_width(all_half_kata) == 'テストヤッタネォォ'

    all_full_latin = 'Ｔｅｓｔ０１２３４５６７８９！？'
    assert utils.normalize_char_width(all_full_latin) == 'Test0123456789!?'

    mixed = 'ｗｉｄｔｈname１45２３　あはは オオオ漢字ﾀﾀﾀ?？！!'
    assert utils.normalize_char_width(mixed) == (
        'widthname14523 あはは オオオ漢字タタタ??!!'
    )


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
