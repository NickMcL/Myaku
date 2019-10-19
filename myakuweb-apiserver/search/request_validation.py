"""Classes for validating requests and their parameters."""

import functools
import logging
from abc import ABC, abstractmethod
from typing import Callable, Generic, Iterable, List, Set, Type, TypeVar, Union

from django.http import JsonResponse
from django.http.request import HttpRequest

_log = logging.getLogger(__name__)

ValueType = Union[str, int]
V = TypeVar('V', str, int)

RESPONSE_ERRORS_KEY = 'errors'


class ValueValidator(ABC):
    """Validator for a value of a request parameter."""

    @abstractmethod
    def validate(self, param_key: str, value: ValueType) -> List[str]:
        """Validate the value of the parameter for the request.

        Args:
            param_key: Key for the parameter for the given value.
            value: Value to validate.

        Returns:
            If the value is fully valid, an empty list. If the value is
            invalid, a list of all of reasons the value is invalid.
        """
        return []


class StrLenValidator(ValueValidator):
    """Validator for length of string values."""

    def __init__(self, min_len: int = 0, max_len: int = None) -> None:
        """Set the min and max valid lengths for the validator."""
        self._min_len = min_len
        self._max_len = max_len

    def validate(self, param_key: str, value: ValueType) -> List[str]:
        """Validate the length of a string parameter value.

        See ValueValidator.validate for more info.
        """
        if not isinstance(value, str):
            raise ValueError(f'Non-string value "{value}" given to validate')

        if len(value) < self._min_len:
            return [
                f"Parameter '{param_key}' value '{value}' is shorter than the "
                f'minimum allowable length ({len(value)} < {self._min_len})'
            ]
        elif self._max_len is not None and len(value) > self._max_len:
            return [
                f"Parameter '{param_key}' value '{value}' is longer than the "
                f'maximum allowable length ({len(value)} > {self._max_len})'
            ]

        return []


class IntRangeValidator(ValueValidator):
    """Validator for range of integer values."""

    def __init__(self, min_val: int = 0, max_val: int = None) -> None:
        """Set the min and max valid values for the validator."""
        self._min_val = min_val
        self._max_val = max_val

    def validate(self, param_key: str, value: ValueType) -> List[str]:
        """Validate the range of an integer parameter value.

        See ValueValidator.validate for more info.
        """
        if not isinstance(value, int):
            raise ValueError(f'Non-integer value "{value}" given to validate')

        if value < self._min_val:
            return [
                f"Parameter '{param_key}' value '{value}' is less than the "
                f'minimum allowable value ({value} < {self._min_val})'
            ]
        elif self._max_val is not None and value > self._max_val:
            return [
                f"Parameter '{param_key}' value '{value}' is greater than the "
                f'maximum allowable value ({value} > {self._max_val})'
            ]

        return []


class AllowableValueValidator(ValueValidator, Generic[V]):
    """Validator for a limited set of valid values."""

    def __init__(self, allowable_values: Iterable[V]) -> None:
        """Set the allowable values for the validator."""
        self._allowable_values: Set[V] = set(allowable_values)

    def validate(self, param_key: str, value: ValueType) -> List[str]:
        """Validate a parameter value is an allowable value.

        See ValueValidator.validate for more info.
        """
        if value not in self._allowable_values:
            return [
                f"Parameter '{param_key}' value '{value}' is not an "
                f'allowable value for that parameter '
                f'(Allowable values: {self._allowable_values})'
            ]

        return []


class ParamValidator(object):
    """Validator for a single parameter for a request."""

    _TYPE_NAME_MAP = {
        str: 'string',
        int: 'integer',
    }

    def __init__(
        self, param_key: str, required: bool, value_type: Type[ValueType],
        validators: Iterable[ValueValidator]
    ) -> None:
        """Set the type and validators for the parameter.

        Args:
            param_key: Key used in the parameters for requests for this
                parameter.
            required: Whether the parameter must be always be present in
                request parameters or not.
            value_type: Type of the value for the parameter.
            validators: Iterable with all of the validators to run to validate
                the value for the paramater.
        """
        self._param_key = param_key
        self._required = required
        self._value_type = value_type
        self._validators = validators

    @property
    def param_key(self) -> str:
        """Return the parameter key for this validator."""
        return self._param_key

    def validate(self, request: HttpRequest) -> List[str]:
        """Validate the parameter for the given request.

        Returns:
            If the parameter is fully valid, an empty list. If the parameter is
            invalid, a list of all of reasons the parameter is invalid.
        """
        if self._param_key not in request.GET:
            if self._required:
                return [
                    f"Required parameter '{self._param_key}' not in request "
                    f'parameters'
                ]
            else:
                return []

        value = request.GET[self._param_key]
        try:
            converted_value = self._value_type(value)
        except ValueError:
            return [
                f"Parameter '{self._param_key}' value '{value}' is not type "
                f'{self._TYPE_NAME_MAP[self._value_type]}'
            ]

        invalidReasons: List[str] = []
        for validator in self._validators:
            invalidReasons.extend(
                validator.validate(self._param_key, converted_value)
            )

        return invalidReasons


class RequestValidator(object):
    """Validator for all parameters for a request."""

    def __init__(
        self, request: HttpRequest, param_validators: Iterable[ParamValidator]
    ) -> None:
        """Set the request and parameter validators to use.

        Args:
            request: Request to be validated by the validator.
            param_validators: Iterable with one paramater validator for each of
                the possible parameters for the request.
        """
        self._request = request
        self._param_validators = param_validators
        self._expected_param_keys = {
            v.param_key for v in self._param_validators
        }

    def validate(self) -> List[str]:
        """Validate the request set for the validator.

        In addition to running the parameter validators for each parameter,
        checks for:
            - No unexpected paramaters in the request
            - No paramaters specified more than once in the request

        Returns:
            If the request is fully valid, an empty list. If the request is
            invalid, a list of all of reasons the request is invalid.
        """
        invalidReasons: List[str] = []
        for param in self._request.GET:
            if param not in self._expected_param_keys:
                invalidReasons.append(
                    f"Unexpected parameter '{param}' in request parameters"
                )
                continue

            if len(self._request.GET.getlist(param)) > 1:
                invalidReasons.append(
                    f"Parameter '{param}' in request parameters multiple "
                    f'times'
                )

        for validator in self._param_validators:
            invalidReasons.extend(validator.validate(self._request))

        return invalidReasons


def validate_request_params(
    param_validators: Iterable[ParamValidator]
) -> Callable:
    """Determine if the parameters for a request are valid.

    Decorates a request handler that returns a JsonResponse.

    Checks the request parameters for validity before passing the request to
    the request handler, and if any of the parameters are invalid, immediately
    returns a JSON response containing the errors instead of calling the
    request handler.

    Args:
        param_validators: Validators for the expected parameters for the
            request.
    """
    def decorator_validate_request_params(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper_validate_request_params(
            request: HttpRequest, *args, **kwargs
        ) -> JsonResponse:
            request_validator = RequestValidator(request, param_validators)
            invalidReasons = request_validator.validate()
            if len(invalidReasons) > 0:
                return JsonResponse({RESPONSE_ERRORS_KEY: invalidReasons})

            return func(request, *args, **kwargs)

        return wrapper_validate_request_params
    return decorator_validate_request_params
