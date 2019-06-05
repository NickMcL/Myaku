"""Generic utility variables and functions.

Attributes:
    HTML_TAG_REGEX (re.Pattern): Regex for matching any HTML tag.
"""

import functools
import logging
import re
import sys
from datetime import datetime
from typing import Callable, Optional

import pytz
from bs4.element import NavigableString, Tag

HTML_TAG_REGEX = re.compile(r'<.*?>')

_ALLOWABLE_HTML_TAGS_IN_TEXT = {
    'a', 'b', 'blockquote', 'br', 'em', 'strong', 'sup'
}

_JAPAN_TIMEZONE = pytz.timezone('Japan')


def log_debug_to_file(filepath: str = './debug.log') -> None:
    """Sets the root logger to write debug level or higher to a file."""
    f = open(filepath, 'w')
    f.close()

    fh = logging.FileHandler(filepath)
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)

    logging.getLogger().addHandler(fh)
    logging.getLogger().setLevel(logging.DEBUG)


def convert_jst_to_utc(dt: datetime) -> datetime:
    """Returns Japan Standard Time (JST) datetime converted to UTC.

    Args:
        dt: JST datetime to be converted. The tzinfo does not need to be set.

    Returns:
        New datetime with dt converted to UTC.
    """
    local_dt = _JAPAN_TIMEZONE.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc)


def parse_valid_child_text(tag: Tag) -> Optional[str]:
    """Parses the child text within an HTML tag if valid.

    The child text of an HTML tag is considered invalid and will not be
    parsed by this function if any of the descendants of the tag are
    structural HTML elements such as section, div, p, h1, etc.

    See _ALLOWABLE_HTML_TAGS_IN_TEXT for a set of HTML tags allowable as
    descendants for a tag with valid child text under this definition.

    Args:
        tag: HTML tag whose child text to attempt to parse.

    Returns:
        The child text of tag, or None if the tag contained no text elements OR
        if the child text was considered invalid for parsing.
    """
    contains_text = False
    for descendant in tag.descendants:
        if (descendant.name is not None and
                descendant.name not in _ALLOWABLE_HTML_TAGS_IN_TEXT):
            logging.debug(
                f'Child text contains invalid {descendant.name} '
                f'tag: {tag!s}',
            )
            return None

        if isinstance(descendant, NavigableString):
            contains_text = True

    if contains_text:
        return re.sub(HTML_TAG_REGEX, '', str(tag))
    else:
        return None


def add_debug_logging(func: Callable) -> Callable:
    """Logs params and return value on func entrance and exit.

    Also logs any exception if raised from func.

    Args:
        func: function to have this decorator applied to it.

    Returns:
        func with this decorator applied.
    """
    @functools.wraps(func)
    def wrapper_add_debug_logging(*args, **kwargs):
        args_repr = [repr(arg)[:100] for arg in args]
        kwargs_repr = [f'{k}={v!r}'[:100] for k, v in kwargs.items()]
        func_args = ', '.join(args_repr + kwargs_repr)
        logging.debug(f'Calling {func.__name__}({func_args})')
        try:
            value = func(*args, *kwargs)
        except BaseException:
            logging.debug(
                f'{func.__name__} raised exception: %s',
                sys.exc_info()[0]
            )
            raise

        logging.debug(f'{func.__name__} returned {value!r}')
        return value
    return wrapper_add_debug_logging


def add_method_debug_logging(cls: type) -> type:
    """Applies the add_debug_logging decorator to all methods in class.

    Does NOT apply decorator to inherited methods from parent classes.

    Args:
        cls: Class to have the logging decorator applied to its methods.

    Returns:
        cls with the logging decorator applied to its methods.
    """
    for attr_name in cls.__dict__:
        attr = getattr(cls, attr_name)
        if callable(attr) and not isinstance(attr, type):
            setattr(cls, attr_name, add_debug_logging(attr))
    return cls
