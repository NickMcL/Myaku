"""Implementations for the Mayku search result caches using Redis."""

import enum
import logging
from datetime import datetime
from typing import Optional

import redis
from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import Query, SearchResultPage, serialize
from myaku.datatypes import JpnArticle
from myaku.errors import DataAccessError

_log = logging.getLogger(__name__)

_FIRST_PAGE_CACHE_HOST_ENV_VAR = 'MYAKU_FIRST_PAGE_CACHE_HOST'
_NEXT_PAGE_CACHE_HOST_ENV_VAR = 'MYAKU_NEXT_PAGE_CACHE_HOST'
_CACHE_PORT = 6379
_CACHE_DB_NUMBER = 0

_FIRST_PAGE_CACHE_PASSWORD_FILE_ENV_VAR = (
    'MYAKU_FIRST_PAGE_CACHE_PASSWORD_FILE'
)
_NEXT_PAGE_CACHE_PASSWORD_FILE_ENV_VAR = 'MYAKU_NEXT_PAGE_CACHE_PASSWORD_FILE'


def _init_redis_client(hostname: str, password: str) -> redis.Redis:
    """Init and return a Redis client.

    Args:
        host: Host of the Redis instance to connect to.
        password: Password to use to auth with the Redis instance.

    Returns:
        A client object connected and authenticated with the Redis instance at
        the given host.
    """
    redis_client = redis.Redis(
        host=hostname, port=_CACHE_PORT, db=_CACHE_DB_NUMBER,
        password=password
    )
    _log.debug(
        'Connected to Redis at %s:%s using db %s',
        hostname, _CACHE_PORT, _CACHE_DB_NUMBER
    )
    return redis_client


@enum.unique
class NextPageDirection(enum.Enum):
    """Direction of the next page of search results.

    Attributes:
        FORWARD: Next page in the forward direction.
        BACKWARD: Next page in the backward direction.
    """
    FORWARD = 1
    BACKWARD = -1


@utils.add_method_debug_logging
class FirstPageCache(object):
    """Cache for the first page for queries of Myaku articles.

    Result pages cached in the first page cache are not associated with users
    and are never removed once set.
    """

    _CACHE_LAST_BUILT_DATETIME_KEY = 'cache_last_built_time'

    def __init__(self) -> None:
        """Init client connection to the cache."""
        hostname = utils.get_value_from_env_variable(
            _FIRST_PAGE_CACHE_HOST_ENV_VAR
        )
        password = utils.get_value_from_env_file(
            _FIRST_PAGE_CACHE_PASSWORD_FILE_ENV_VAR
        )
        self._redis_client = _init_redis_client(hostname, password)

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

    def set(self, page: SearchResultPage) -> None:
        """Cache the first page of search results for the given query."""
        serialized_page = serialize.serialize_search_result_page(page)

        self._redis_client.set(
            f'query:{page.query.query_str}', serialized_page.search_results
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

    def get(self, query: Query) -> Optional[SearchResultPage]:
        """Get the cached first page of search results for the given query.

        Args:
            query: Query to get the cached first page of search results for.

        Returns:
            The cached first page of search results for the query, or None if
            the first page of search results is not in the cache for the query.
        """
        cached_results = self._redis_client.get(f'query:{query.query_str}')
        if cached_results is None:
            return None

        page = SearchResultPage(query=query)
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


@utils.add_method_debug_logging
class NextPageCache(object):
    """Cache for the anticipated next pages for queries of Myaku articles.

    The purpose of this cache is to hold the anticipated next page
    (page_num +/- 1) of search results a user will request so that the those
    results can be retrieved quickly if requested by that user.

    Result pages cached in the next page cache are associated with users
    and are removed as necessary using an LRU strategy.
    """

    _KEY_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 1 week

    def __init__(self) -> None:
        """Init client connection to the cache."""
        hostname = utils.get_value_from_env_variable(
            _NEXT_PAGE_CACHE_HOST_ENV_VAR
        )
        password = utils.get_value_from_env_file(
            _NEXT_PAGE_CACHE_PASSWORD_FILE_ENV_VAR
        )
        self._redis_client = _init_redis_client(hostname, password)

    def set(
        self, user_id: str, page: SearchResultPage,
        direction: NextPageDirection
    ) -> None:
        """Cache a page of search results for the user.

        Args:
            user_id: User to cache the page for.
            page: Page to cache.
            direction: Page direction of the given page relative to the user's
                last requested page.
        """
        serialized_page = serialize.serialize_search_result_page(page)

        next_page_hash = {
            'query': serialized_page.query,
            'search_results': serialized_page.search_results
        }
        for article_id, article_bytes in serialized_page.article_map.items():
            next_page_hash[article_id] = article_bytes

        redis_key = f'user:{user_id}:{direction.value}'
        self._redis_client.delete(redis_key)
        self._redis_client.hmset(redis_key, next_page_hash)
        self._redis_client.expire(redis_key, self._KEY_EXPIRE_SECONDS)

    def _query_match(self, query: Query, query_bytes: bytes) -> bool:
        """Return True if the serialized query bytes match the query."""
        out_query = Query(user_id=query.user_id)
        serialize.deserialize_query(query_bytes, out_query)
        if out_query != query:
            _log.debug(
                'Query (%s) page (%d) requested by user %s does not match '
                'query (%s) page (%d) of cached next page for the user',
                query.query_str, query.page_num, query.user_id,
                out_query.query_str, out_query.page_num
            )
            return False

        _log.debug(
            'Query (%s) page (%d) requested by user %s matches cached next '
            'page for the user', query.query_str, query.page_num, query.user_id
        )
        return True

    def _get_query_page_cache_key(self, query: Query) -> Optional[str]:
        """Get the key in the cache for the search results page for the query.

        Args:
            query: Query to get the key in the cache for.

        Returns:
            The key for the search results page in the cache for the query if
            the page is in the cache, or None if the page for the query is not
            in the cache.
        """
        user_id = query.user_id
        forward_key = f'user:{user_id}:{NextPageDirection.FORWARD.value}'
        forward_query_bytes = self._redis_client.hget(forward_key, 'query')
        if forward_query_bytes is None:
            _log.debug('Key %s not in next page cache', forward_key)
        elif self._query_match(query, forward_query_bytes):
            return forward_key

        backward_key = f'user:{user_id}:{NextPageDirection.BACKWARD.value}'
        backward_query_bytes = self._redis_client.hget(backward_key, 'query')
        if backward_query_bytes is None:
            _log.debug('Key %s not in next page cache', backward_key)
        elif self._query_match(query, backward_query_bytes):
            return backward_key

        return None

    def get(self, query: Query) -> Optional[SearchResultPage]:
        """Get a cached page of search results for the query.

        The cached next page will only be returned if it matches the query_str,
        page_num, and user_id of the query.

        Args:
            query: Query to get the cached next page of search results for.

        Returns:
            The cached page of search results matching the given query, or None
            if a page of search results matching the query is not in the next
            page cache.
        """
        cache_key = self._get_query_page_cache_key(query)
        if cache_key is None:
            return None

        cached_results = self._redis_client.hget(cache_key, 'search_results')
        page = SearchResultPage(query=query)
        serialize.deserialize_search_results(cached_results, page)
        for result in page.search_results:
            article_id = result.article.database_id
            cached_article = self._redis_client.hget(
                cache_key, str(article_id)
            )
            serialize.deserialize_article(cached_article, result.article)

        return page
