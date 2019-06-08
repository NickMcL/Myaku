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
import requests
from bs4.element import NavigableString, Tag

_log = logging.getLogger(__name__)

HTML_TAG_REGEX = re.compile(r'<.*?>')

_ALLOWABLE_HTML_TAGS_IN_TEXT = {
    'a', 'b', 'blockquote', 'br', 'em', 'strong', 'sup'
}

_JAPAN_TIMEZONE = pytz.timezone('Japan')

_LOGGING_FORMAT = (
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def toggle_reibun_debug_log(enable: bool = True, filepath: str = None) -> None:
    """Toggles the debug logger for the reibun package.

    By default, logs to stdout. If filepath is given, logs to that file
    instead.

    Args:
        enable: If True, enables the logger; if False, disables the logger.
        filepath: If given, the file will be truncated, and the logger will be
            set to write to it.
    """
    package_log = logging.getLogger('reibun')
    for handler in package_log.handlers[:]:
        package_log.removeHandler(handler)

    if not enable:
        return

    reibun_handler = None
    if filepath is not None:
        f = open(filepath, 'w')
        f.close()
        reibun_handler = logging.FileHandler(filepath)
    else:
        reibun_handler = logging.StreamHandler(sys.stderr)

    reibun_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(_LOGGING_FORMAT)
    reibun_handler.setFormatter(formatter)

    package_log.addHandler(reibun_handler)
    package_log.setLevel(logging.DEBUG)


def log_and_raise(log: logging.Logger, exc: Exception, error_msg: str) -> None:
    """Logs and raises the exception with the given error message."""
    log.error(error_msg)
    raise exc(error_msg)


def get_request_raise_on_error(
    url: str, session: requests.sessions.Session = None, **kwargs
) -> requests.models.Response:
    """Makes a GET request to url, then raises if status code >= 400.

    Args:
        url: URL to make the GET request to.
        session: If provided, this Session will be used to make the GET
            request.
        kwargs: Will be passed to the requests.get function call.

    Returns:
        The reponse from the GET request.

    Raises:
        HTTPError: The GET request returned with a status code >= 400
    """
    _log.debug(f'Making GET request to {url}')
    if session:
        response = session.get(url, **kwargs)
    else:
        response = requests.get(url, **kwargs)
    _log.debug(f'Reponse received with code {response.status_code}')
    response.raise_for_status()

    return response


def convert_jst_to_utc(dt: datetime) -> datetime:
    """Returns Japan Standard Time (JST) datetime converted to UTC.

    Args:
        dt: JST datetime to be converted. The tzinfo does not need to be set.

    Returns:
        New datetime with dt converted to UTC.
    """
    local_dt = _JAPAN_TIMEZONE.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc)


def alnum_count(string: str) -> int:
    """Returns the number of alphanumeric characters in the string."""
    return sum(c.isalnum() for c in string)


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
            _log.debug(
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


def _get_full_name(func: Callable) -> str:
    """Gets the fully qualified name of the funcion."""
    if func.__module__:
        return f'{func.__module__}.{func.__qualname__}'
    return func.__qualname__


def shorten_str(string: str, max_chars: int = 100) -> str:
    """Shorten string to a max length.

    Adds an indicator to the end of the string if some of the string was
    removed by shortening it.
    """
    if len(string) <= max_chars:
        return string
    return string[:max_chars] + '...'


def add_debug_logging(func: Callable) -> Callable:
    """Logs params and return value on func entrance and exit.

    Also logs any exception if raised from func.
    """
    @functools.wraps(func)
    def wrapper_add_debug_logging(*args, **kwargs):
        func_name = _get_full_name(func)

        args_repr = [shorten_str(repr(arg)) for arg in args]
        kwargs_repr = [shorten_str(f'{k}={v!r}') for k, v in kwargs.items()]
        func_args = ', '.join(args_repr + kwargs_repr)
        _log.debug(f'Calling {func_name}({func_args})')
        try:
            value = func(*args, *kwargs)
        except BaseException:
            _log.exception(f'{func_name} raised an exception')
            raise

        short_value = shorten_str(repr(value))
        _log.debug(f'{func_name} returned {short_value}')
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
        if (callable(attr)
                and not isinstance(attr, type)
                and 'DEBUG_SKIP' not in attr.__dict__):
            setattr(cls, attr_name, add_debug_logging(attr))
    return cls


def skip_method_debug_logging(func: Callable) -> Callable:
    """Causes method not be logged when add_method_debug_logging is applied.

    If a method gets called a high number of times, it can be excluded from
    being logged with skip_method_debug_logging with this decorator.
    """
    func.__dict__['DEBUG_SKIP'] = None
    return func
