"""Middleware for the search API for MyakuWeb."""

import logging
from pprint import pformat
from typing import Callable

from django.http import HttpResponse
from django.http.request import HttpRequest

from myaku import utils

_log = logging.getLogger(__name__)

utils.toggle_myaku_package_log(filename_base='myakuweb', package='search')


class ShortCacheMiddleware(object):
    """Set headers in all responses for brief client caching."""

    _CACHE_CONTROL_HEADER = 'Cache-Control'
    _CACHE_DURATION = 3600  # 1 hour

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """Set the get_response callable to use for the middleware."""
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Set headers in response for brief client caching.

        Uses the Cache-Control headers to request that the client caches the
        response for a brief duration.

        Will not modify the Cache-Control header if it is already set on the
        request.
        """
        response = self._get_response(request)

        if not response.has_header(self._CACHE_CONTROL_HEADER):
            response[self._CACHE_CONTROL_HEADER] = (
                f'public, max-age={self._CACHE_DURATION}'
            )

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
