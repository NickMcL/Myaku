"""Middleware for the search API for MyakuWeb."""

import logging
from pprint import pformat
from typing import Callable

from django.http import HttpResponse
from django.http.request import HttpRequest

from myaku import utils

_log = logging.getLogger(__name__)

utils.toggle_myaku_package_log(filename_base='myakuweb', package='search')


class NoCacheMiddleware(object):
    """Set headers in all responses to prevent client caching."""

    _CACHE_CONTROL_HEADER = 'Cache-Control'

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """Set the get_response callable to use for the middleware."""
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Set headers in response to prevent client caching.

        Uses the Cache-Control headers to enforce that the client always checks
        with the server for changes when a resource is requested instead of
        directly using a cached response.

        Will not modify the Cache-Control header if it is already set on the
        request.
        """
        response = self._get_response(request)

        if not response.has_header(self._CACHE_CONTROL_HEADER):
            response[self._CACHE_CONTROL_HEADER] = 'no-cache'

        return response


class LogRequestMiddleware(object):
    """Log the full metadata all requests."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """Set the get_response callable to use for the middleware."""
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Log the full metadata for the request.

        Logs using the INFO log level.
        """
        _log.info('Handling request: %s', request)
        if request.method == 'GET':
            _log.info('GET parameters: %s', request.GET)
        _log.info('Request meta:\n%s', pformat(request.META))
        response = self._get_response(request)

        _log.info('Returning response: %s', response)
        return response
