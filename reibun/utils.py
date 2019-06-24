"""Generic utility variables and functions."""

import dataclasses
import functools
import inspect
import logging
import os
import time
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from operator import itemgetter
from typing import Any, Callable, List, Optional, Tuple, TypeVar

import jaconv
import pytz

from reibun.errors import EnvironmentNotSetError

LOG_DIR_ENV_VAR = 'REIBUN_LOG_DIR'
APP_DATA_DIR_ENV_VAR = 'REIBUN_APP_DATA_DIR'

_log = logging.getLogger(__name__)

_JAPAN_TIMEZONE = pytz.timezone('Japan')

_JPN_SENTENCE_ENDERS = [
    '。',
    '？',
    '！',
    '?',
    '!',
    '\n',
]

_DEBUG_LOG_MAX_SIZE_ENV_VAR = 'REIBUN_DEBUG_LOG_MAX_SIZE'
_DEBUG_LOG_MAX_SIZE = os.environ.get(_DEBUG_LOG_MAX_SIZE_ENV_VAR, 0)

_INFO_LOG_MAX_SIZE_ENV_VAR = 'REIBUN_INFO_LOG_MAX_SIZE'
_INFO_LOG_MAX_SIZE = os.environ.get(_INFO_LOG_MAX_SIZE_ENV_VAR, 0)

_LOG_ROTATING_BACKUP_COUNT = 10
_FILE_LOGGING_FORMAT = (
    '%(asctime)s:%(name)s:%(levelname)s: %(message)s'
)
_STREAM_LOGGING_FORMAT = '%(message)s'

T = TypeVar('T')


def toggle_reibun_package_log(
    enable: bool = True, filename_base: str = 'reibun'
) -> None:
    """Toggles the logger for the reibun package.

    Logs to three locations:
        - DEBUG level to <filename_base>.debug.log files using a rotating
            handler with a total max size across all files of
            _DEBUG_LOG_MAX_SIZE
        - INFO level to <filename_base>.info.log files using a rotating handler
            with a total max size across all files of _INFO_LOG_MAX_SIZE
        - INFO level to stderr

    The log files are written to the dir specified by LOG_DIR_ENV_VAR if it
    exists in the environment. Otherwise, the files are written to the current
    working directory instead.

    Args:
        enable: If True, enables the logger; if False, disables the logger.
        filename_base: A name to prepend to the files written by the logger.
    """
    # Use UTC time for all logging timestamps
    logging.Formatter.converter = time.gmtime

    log_dir = os.environ.get(LOG_DIR_ENV_VAR)
    if log_dir is None:
        log_dir = os.getcwd()
    filepath_base = os.path.join(log_dir, filename_base)

    package_log = logging.getLogger(__name__.split('.')[0])
    for handler in package_log.handlers[:]:
        package_log.removeHandler(handler)

    if not enable:
        return

    _add_logging_handlers(package_log, filepath_base)


def _add_logging_handlers(logger: logging.Logger, filepath_base: str) -> None:
    """Adds a set of handlers to the given logger.

    Adds the handlers specified in the docstring of toggle_reibun_package_log.
    """
    logger.setLevel(logging.DEBUG)

    # Truncate previous log file if not rotating
    if _DEBUG_LOG_MAX_SIZE == 0:
        f = open(filepath_base + 'debug.log', 'w')
        f.close()

    file_log_formatter = logging.Formatter(_FILE_LOGGING_FORMAT)
    debug_file_handler = RotatingFileHandler(
        filepath_base + '.debug.log',
        maxBytes=_DEBUG_LOG_MAX_SIZE // _LOG_ROTATING_BACKUP_COUNT,
        backupCount=_LOG_ROTATING_BACKUP_COUNT
    )
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(file_log_formatter)
    logger.addHandler(debug_file_handler)

    if _INFO_LOG_MAX_SIZE == 0:
        f = open(filepath_base + 'info.log', 'w')
        f.close()

    info_file_handler = RotatingFileHandler(
        filepath_base + '.info.log',
        maxBytes=_INFO_LOG_MAX_SIZE // _LOG_ROTATING_BACKUP_COUNT,
        backupCount=_LOG_ROTATING_BACKUP_COUNT
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(file_log_formatter)
    logger.addHandler(info_file_handler)

    stream_log_formatter = logging.Formatter(_STREAM_LOGGING_FORMAT)
    info_stream_handler = logging.StreamHandler(sys.stderr)
    info_stream_handler.setLevel(logging.INFO)
    info_stream_handler.setFormatter(stream_log_formatter)
    logger.addHandler(info_stream_handler)


def log_and_raise(log: logging.Logger, exc: Exception, error_msg: str) -> None:
    """Logs and raises the exception with the given error message."""
    log.error(error_msg)
    raise exc(error_msg)


def get_value_from_environment_variable(env_var: str, value_name: str) -> str:
    """Gets a value from an environment variable.

    value_name is only used in error messages as a human-readable name for
    the value being retrieved.

    Raises:
        EnvironmentNotSetError: One of the following:
            - The environment variable is not set.
            - The environment variable is set but empty.
    """
    value = os.environ.get(env_var)
    if value is None:
        log_and_raise(
            _log, EnvironmentNotSetError,
            '{} environment variable "{}" is not set in the '
            'environment'.format(value_name, env_var)
        )

    if len(value) == 0:
        log_and_raise(
            _log, EnvironmentNotSetError,
            '{} environment variable "{}" is set but empty'.format(
                value_name, env_var
            )
        )

    return value


def get_value_from_environment_file(env_var: str, value_name: str) -> str:
    """Gets a value from a file specified by an environment variable.

    value_name is only used in error messages as a human-readable name for
    the value being retrieved.

    Raises:
        EnvironmentNotSetError: One of the following:
            - The environment variable is not set.
            - The environment variable is set but empty.
            - The file specified by the environment variable doesn't exist.
            - The file specified by the environment variable is empty.
    """
    filepath = get_value_from_environment_variable(
        env_var, value_name + ' file'
    )

    if not os.path.exists(filepath):
        log_and_raise(
            _log, EnvironmentNotSetError,
            '{} file specified by environment variable "{}" does not '
            'exist'.format(filepath, env_var)
        )

    with open(filepath, 'r') as value_file:
        value = value_file.read()
    if value == '':
        log_and_raise(
            _log, EnvironmentNotSetError,
            '{} file specified by environment variable "{}" is '
            'empty'.format(filepath, env_var)
        )

    return value


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


def find_jpn_sentene_start(text: str, pos: int) -> int:
    """Find the start index of the Japanese sentence in text containing pos."""
    sentence_ender_indexes = [
        text.rfind(char, 0, pos) for char in _JPN_SENTENCE_ENDERS
    ]
    previous_ender_index = max(sentence_ender_indexes)
    if previous_ender_index == -1:
        return 0
    return previous_ender_index + 1


def find_jpn_sentene_end(text: str, pos: int) -> int:
    """Finds one past the end index of the sentence in text containing pos."""
    sentence_ender_indexes = [
        text.find(char, pos) for char in _JPN_SENTENCE_ENDERS
    ]
    for i, index in enumerate(sentence_ender_indexes):
        if index == -1:
            sentence_ender_indexes[i] = len(text)

    next_ender_index = min(sentence_ender_indexes)
    return next_ender_index


def tuple_or_none(item: Any) -> Tuple:
    """Converts item to tuple, or returns None if item is None."""
    if item is None:
        return None
    return tuple(item)


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
        _log.debug('Calling %s(%s)', func_name, func_args)
        try:
            value = func(*args, *kwargs)
        except BaseException:
            _log.exception('%s raised an exception', func_name)
            raise

        short_value = shorten_str(repr(value))
        _log.debug('%s returned %s', func_name, short_value)
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
