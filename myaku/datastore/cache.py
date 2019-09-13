"""Driver for the Mayku search results cache.

Currently implemented using Redis, but the public members of this module are
defined generically so that the implementation of the database can be changed
freely while keeping the access interface consistent.
"""

import logging
from datetime import datetime
from typing import Optional

import redis
from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import JpnArticleSearchResultPage, serialize
from myaku.datatypes import JpnArticle
from myaku.errors import DataAccessError

_log = logging.getLogger(__name__)

_CACHE_HOST_ENV_VAR = 'MYAKU_FIRST_PAGE_CACHE_HOST'
_CACHE_PORT = 6379
_CACHE_DB_NUMBER = 0

_CACHE_PASSWORD_FILE_ENV_VAR = 'MYAKU_FIRST_PAGE_CACHE_PASSWORD_FILE'


@utils.add_method_debug_logging
class FirstPageCache(object):
    """Cache for the first page of queries for articles crawled by Mayku."""

    # Gzip compress level to use when compressing serialized bytes to store in
    # the cache.
    _SERIALIZED_BYTES_COMPRESS_LEVEL = 1

    _CACHE_LAST_BUILT_DATETIME_KEY = 'cache_last_built_time'

    def __init__(self) -> None:
        """Init client connection to the cache."""
        self._redis_client = self._init_redis_client()

    def _init_redis_client(self) -> redis.Redis:
        """Init and return the client for connecting to the Redis cache.

        Returns:
            A client object connected and authenticated with the Redis cache.

        Raises:
            EnvironmentNotSetError: If a needed value from the environment to
                init the client is not set in the environment.
        """
        hostname = utils.get_value_from_env_variable(_CACHE_HOST_ENV_VAR)
        password = utils.get_value_from_env_file(_CACHE_PASSWORD_FILE_ENV_VAR)

        redis_client = redis.Redis(
            host=hostname, port=_CACHE_PORT, db=_CACHE_DB_NUMBER,
            password=password
        )
        _log.debug(
            'Connected to Redis at %s:%s using db %s',
            hostname, _CACHE_PORT, _CACHE_DB_NUMBER
        )
        return redis_client

    def set_built_marker(self) -> None:
        """Set the marker indicating the cache has been fully built."""
        self._redis_client.set(
            self._CACHE_LAST_BUILT_DATETIME_KEY, datetime.utcnow().isoformat()
        )

    def is_built(self) -> bool:
        """Return True if the cache has been fully built previously."""
        last_built_time = self._redis_client.get(
            self._CACHE_LAST_BUILT_DATETIME_KEY
        )
        return last_built_time is not None

    def flush_all(self) -> None:
        """Remove everything stored in the cache."""
        self._redis_client.flushall()

    def set(self, query: str, page: JpnArticleSearchResultPage) -> None:
        """Cache the first page of search results for the given query."""
        serialized_page = serialize.serialize_search_result_page(page)

        self._redis_client.set(
            f'query:{query}', serialized_page.search_results
        )
        for article_id, article_bytes in serialized_page.article_map.items():
            self._redis_client.set(f'article:{article_id}', article_bytes)

    def get_article(self, article_oid: ObjectId) -> JpnArticle:
        """Get an article cached in the first page cache.

        Args:
            article_oid: Database ID of the article to get from the first page
                cache.

        Returns:
            An article object populated with the article data stored for the
            given ID in the first page cache, or None if no data is stored in
            the first page cache for the given ID.
        """
        cached_article = self._redis_client.get(f'article:{article_oid!s}')
        if cached_article is None:
            return None

        article = JpnArticle(database_id=str(article_oid))
        serialize.deserialize_article(cached_article, article)
        return article

    def get(self, query: str) -> Optional[JpnArticleSearchResultPage]:
        """Get the cached first page of search results for the given query.

        Args:
            query: Query to get the cached first page of search results for.

        Returns:
            The cached first page of search results for the query, or None if
            the first page of search results is not in the cache for the query.
        """
        cached_results = self._redis_client.get(f'query:{query}')
        if cached_results is None:
            return None

        page = JpnArticleSearchResultPage(query=query, page_num=1)
        serialize.deserialize_search_results(cached_results, page)
        for result in page.search_results:
            article_id = result.article.database_id
            cached_article = self._redis_client.get(f'article:{article_id}')
            if cached_article is None:
                utils.log_and_raise(
                    _log, DataAccessError,
                    f'Article key for ID "{article_id}" not found in first '
                    f'cache'
                )
            serialize.deserialize_article(cached_article, result.article)

        return page
