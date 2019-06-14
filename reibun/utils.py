"""Generic utility variables and functions.

Attributes:
    HTML_TAG_REGEX (re.Pattern): Regex for matching any HTML tag.
"""

import dataclasses
import functools
import inspect
import logging
import re
import sys
from datetime import datetime
from operator import itemgetter
from typing import Any, Callable, List, Optional, TypeVar

import jaconv
import pytz
import requests
from bs4.element import NavigableString, Tag

_log = logging.getLogger(__name__)

T = TypeVar('T')

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


def unique(items: List[T]) -> List[T]:
    """Returns a list with only the unique elements of items.

    Preserves order of items, and does not require T to be hashable.

    If T is a hashable type, use sets to dedupe instead of this function since
    the set method is much faster than method used in this function.
    """
    unique_items = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
    return unique_items


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
    _log.debug(f'Making GET request to url "{url}"')
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


def get_alnum_count(string: str) -> int:
    """Returns the number of alphanumeric characters in the string."""
    return sum(c.isalnum() for c in string)


def normalize_char_width(string: str) -> str:
    """Normalizes character widths in string to a set standard.

    Converts all katakana to full-width, and converts all latin alphabet and
    numeric characters to half-width
    """
    out_str = jaconv.h2z(string, kana=True, ascii=False, digit=False)
    out_str = jaconv.z2h(out_str, kana=False, ascii=True, digit=True)
    return out_str


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
                f'tag: "{tag}"',
            )
            return None

        if isinstance(descendant, NavigableString):
            contains_text = True

    if contains_text:
        return re.sub(HTML_TAG_REGEX, '', str(tag))
    else:
        return None


def get_full_name(obj: Any) -> str:
    """Gets the fully qualified name of the object."""
    if obj.__module__:
        return f'{obj.__module__}.{obj.__qualname__}'
    return obj.__qualname__


def shorten_str(string: str, max_chars: int = 100) -> str:
    """Shorten string to a max length + a shortened indicator.

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
        func_name = get_full_name(func)

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


def _dataclass_setter_with_default_wrapper(
        func: Callable, field: Optional[dataclasses.field] = None
) -> Callable:
    """Handles init properly for a property with default value in a dataclass.

    If a property has a setter and a default value is given for it in a
    dataclass, the dataclass will try to set the property to the property
    object itself on init instead of the default value. This wrapper properly
    handles the default init case for the setter so that it is passed its
    default value.

    Args:
        func: Setter of a property in a dataclass.
        field: This fields default or default_factory is used to get the
            default value for the property. None will be used as the default
            value if not given.
    """
    @functools.wraps(func)
    def wrapper(self, set_value: Any) -> None:
        if (isinstance(set_value, property)
                and hasattr(set_value, 'fset')
                and get_full_name(set_value.fset) == get_full_name(func)):
            # This is the dataclass init without a user passed value to init,
            # so set the proper default value
            if (field is None
                    or field.default is dataclasses.MISSING
                    and field.default_factory is dataclasses.MISSING):
                func(self, None)
            elif field.default is not dataclasses.MISSING:
                func(self, field.default)
            else:
                func(self, field.default_factory())
        else:
            func(self, set_value)

    return wrapper


def _dataclass_setter_with_readonly(
    self, set_value: Any, readonly_prop: property
) -> None:
    """Can be used as setter for readonly property in a dataclass.

    If a property is read-only in a dataclass, it will cause an AttributeError
    on init because the dataclass will always try to set it on init. This
    function can be set as the setter for a read-only property in this case to
    avoid errors on dataclass init while still raising an AttributeError if the
    property is ever set outside of the dataclass init case.

    Args:
        self: Placeholder to capture the self param passed to setters. Not used
            in the function.
        set_value: Set value passed to the setter. Only used to check if the
            setter is being called from the dataclass init or not. This value
            does not actually get set to anything.
        readonly_prop: The read-only property that this setter is being used
            for.
    """
    if (isinstance(set_value, property)
            and hasattr(set_value, 'fget')
            and set_value.fget is readonly_prop.fget):
        # This is the dataclass init, so don't raise an error.
        return

    raise AttributeError("can't set attribute")


def make_properties_work_in_dataclass(cls: T = None, **kwargs) -> T:
    """Makes the properties in cls compatible with dataclasses.

    As of Python 3.7, properties with default values and read-only properties
    will not init properly with dataclasses because the dataclass init will try
    to set the property with the property object itself during init. This
    decorator will do some magic to fix this so that properties in the
    dataclass with default values and read-only properties will init properly.

    Args:
        kwargs: The default value for a property can be specified by giving a
            kwarg using the property name set to a dataclasses.field object
            that sepecifies the default value or default factory for the
            property. If a kwarg is not given for a property with a setter, a
            default value of None will be used.
    """
    if cls is None:
        return functools.partial(
            make_properties_work_in_dataclass, **kwargs
        )

    prop_names = []
    for name in dir(cls):
        # Avoid changing anything for dunder attrs
        if name.startswith('__') and name.endswith('__'):
            continue
        if isinstance(getattr(cls, name), property):
            prop_names.append(name)

    if len(prop_names) == 0:
        return cls

    for prop_name in prop_names:
        prop = getattr(cls, prop_name)
        if prop.fset is None:
            readonly_setter = functools.partial(
                _dataclass_setter_with_readonly, readonly_prop=prop
            )
            setattr(cls, prop_name, prop.setter(readonly_setter))
        else:
            default_setter = _dataclass_setter_with_default_wrapper(
                prop.fset, kwargs.get(prop_name)
            )
            setattr(cls, prop_name, prop.setter(default_setter))

    return cls


def singleton_per_config(cls: T) -> T:
    """Makes the decorated class only have one instance per init config.

    This will cause there to only ever be one object in existence for each
    combination of init parameters for the class. If a second object is
    attempted to be created with the same init parameters as an existing
    object, the class constructor will just give the reference of the existing
    object with those init parameters without creating a new object and without
    calling the __new__ or __init__ methods again of the existing object.

    This decorator should only be used on a class whose possible __init__
    parameters are all hashable.
    """
    if not hasattr(singleton_per_config, '_singleton_map'):
        singleton_per_config._singleton_map = {}

    @functools.wraps(cls)
    def singleton_per_config_wrapper(*args, **kwargs):
        init_sig = inspect.signature(cls.__init__)

        # The 0 used for the first arg is just a placeholder to fill the self
        # arg of the __init__ signature.
        bound_args = init_sig.bind(0, *args, **kwargs)
        bound_args.apply_defaults()
        sorted_kwargs = tuple(
            sorted(bound_args.kwargs.items(), key=itemgetter(0))
        )

        # Skip the first arg of args so that the 0 we used earlier as a
        # placeholder for the self arg isn't included.
        init_sig_key = bound_args.args[1:] + sorted_kwargs

        cls_name = get_full_name(cls)
        if cls_name not in singleton_per_config._singleton_map:
            singleton_per_config._singleton_map[cls_name] = {}
        cls_singleton_map = singleton_per_config._singleton_map[cls_name]

        if init_sig_key not in cls_singleton_map:
            cls_singleton_map[init_sig_key] = cls(*args, **kwargs)
        return cls_singleton_map[init_sig_key]

    return singleton_per_config_wrapper
