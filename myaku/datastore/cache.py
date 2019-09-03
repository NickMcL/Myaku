"""Driver for the Mayku search results cache.

Currently implemented using Redis, but the public members of this module are
defined generically so that the implementation of the database can be changed
freely while keeping the access interface consistent.
"""

import logging
import zlib
from datetime import datetime
from typing import List, Optional, Tuple

import redis
from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import JpnArticleSearchResult
from myaku.datatypes import ArticleTextPosition, JpnArticle
from myaku.errors import DataAccessError

_log = logging.getLogger(__name__)

_CACHE_HOST_ENV_VAR = 'MYAKU_FIRST_PAGE_CACHE_HOST'
_CACHE_PORT = 6379
_CACHE_DB_NUMBER = 0

_CACHE_PASSWORD_FILE_ENV_VAR = 'MYAKU_FIRST_PAGE_CACHE_PASSWORD_FILE'


@utils.add_method_debug_logging
class FirstPageCache(object):
    """Caches the first page of queries for articles crawled by Mayku."""

    # Gzip compress level to use when compressing serialized bytes to store in
    # the cache.
    _SERIALIZED_BYTES_COMPRESS_LEVEL = 1

    _CACHE_LAST_BUILT_DATETIME_KEY = 'cache_last_built_time'

    def __init__(self) -> None:
        """Init client connection to the cache."""
        self._redis_client = self._init_redis_client()

    def _init_redis_client(self) -> redis.Redis:
        """Inits and returns the client for connecting to the Redis cache.

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
        """Returns True if the cache has been fully built previously."""
        last_built_time = self._redis_client.get(
            self._CACHE_LAST_BUILT_DATETIME_KEY
        )
        return last_built_time is not None

    @utils.skip_method_debug_logging
    def _serialize_search_result(
        self, search_result: JpnArticleSearchResult
    ) -> List[bytes]:
        """Serializes a single search result.

        Does not serialize the full article for the search result. Only
        serializes the ID for the article.

        Args:
            search_result: Search result to serialize.

        Returns:
            List of bytes that can be joined to get the full serialization of
            the search result.
        """
        bytes_list = []
        bytes_list.append(ObjectId(search_result.article.database_id).binary)
        bytes_list.append(
            len(search_result.found_positions).to_bytes(2, 'little')
        )
        for pos in search_result.found_positions:
            bytes_list.append(pos.index.to_bytes(2, 'little'))
            bytes_list.append(pos.len.to_bytes(1, 'little'))

        return bytes_list

    @utils.skip_method_debug_logging
    def _serialize_text(
        self, text: str, size_bytes: int, encoding: str = 'utf-8'
    ) -> List[bytes]:
        """Serializes text.

        Args:
            text: Text to serialize.
            size_bytes: Number of bytes to use to store the size of the encoded
                text.
            encoding: Encoding to use to encode the text to bytes.

        Returns:
            List of bytes that can be joined to get the full serialization of
            the text.
        """
        text_bytes = []
        encoded_text = text.encode(encoding)
        text_bytes.append(len(encoded_text).to_bytes(size_bytes, 'little'))
        text_bytes.append(encoded_text)

        return text_bytes

    @utils.skip_method_debug_logging
    def _serialize_article(self, article: JpnArticle) -> List[bytes]:
        """Serializes a single article for a search result.

        Does not serialize all attributes of the article. Only serializes the
        attributes used in displaying search results.

        Args:
            article: Article from a search result to serialize.

        Returns:
            List of bytes that can be joined to get the full serialization of
            the article.
        """
        article_bytes = []

        # Encode title and full text using utf-16 because it is more space
        # efficient than utf-8 for Japanese characters.
        title_bytes = self._serialize_text(article.title, 3, 'utf-16')
        article_bytes.extend(title_bytes)
        full_text_bytes = self._serialize_text(article.full_text, 3, 'utf-16')
        article_bytes.extend(full_text_bytes)

        # Encode source name and url using utf-8 because it is more space
        # efficeient than utf-16 for ascii characters.
        article_bytes.extend(self._serialize_text(article.source_name, 1))
        article_bytes.extend(self._serialize_text(article.source_url, 2))

        article_bytes.append(article.alnum_count.to_bytes(2, 'little'))
        article_bytes.append(int(article.has_video).to_bytes(1, 'little'))

        pub_dt_timestamp = int(article.publication_datetime.timestamp())
        article_bytes.append(pub_dt_timestamp.to_bytes(4, 'little'))
        up_dt_timestamp = int(article.last_updated_datetime.timestamp())
        article_bytes.append(up_dt_timestamp.to_bytes(4, 'little'))

        return article_bytes

    def _cache_serialized_search_results(
        self, query: str, search_results: List[JpnArticleSearchResult],
        compress_level: int
    ) -> None:
        """Serializes query search results and caches them.

        Args:
            query: Query to cache the search results for.
            search_results: Search results for the given query.
            compress_level: Level to use for the gzip compression of the
                serialized cache values. -1 is system default level, 0 is no
                compression, 1-9 is increasingly slow compression in exchange
                for higher compression ratio.
        """
        results_bytes = []
        results_bytes.append(len(search_results).to_bytes(1, 'little'))
        for result in search_results:
            results_bytes.extend(self._serialize_search_result(result))

            # Don't waste time serializing and caching articles already
            # available in the cache.
            article_key = f'article:{result.article.database_id}'
            if self._redis_client.exists(article_key):
                continue

            article_bytes = self._serialize_article(result.article)
            self._redis_client.set(
                article_key,
                zlib.compress(b''.join(article_bytes), compress_level)
            )

        self._redis_client.set(
            f'query:{query}',
            zlib.compress(b''.join(results_bytes), compress_level)
        )

    def set(
        self, query: str,
        first_page_search_results: List[JpnArticleSearchResult]
    ) -> None:
        """Caches the first page of search results for the given query."""
        self._cache_serialized_search_results(
            query, first_page_search_results,
            self._SERIALIZED_BYTES_COMPRESS_LEVEL
        )

    @utils.skip_method_debug_logging
    def _deserialize_text_positions(
        self, buffer: bytes, start_offset: int,
        out_list: List[ArticleTextPosition]
    ) -> int:
        """Deserializes text positions from a buffer of bytes.

        Args:
            buffer: Buffer of bytes containing the text positions to
                deserialize.
            start_offset: Offset in the buffer of the start of the section
                containing the serialized text positions to deserialize.
            out_list: List to append the deserialized text positions to.

        Returns:
            The number of bytes read from the buffer to deserialize the text
            positions.
        """
        offset = start_offset
        text_pos_count = int.from_bytes(buffer[offset:offset + 2], 'little')
        offset += 2
        for _ in range(text_pos_count):
            text_pos = ArticleTextPosition(
                index=int.from_bytes(buffer[offset:offset + 2], 'little'),
                len=int.from_bytes([buffer[offset + 2]], 'little')
            )
            out_list.append(text_pos)
            offset += 3

        return offset - start_offset

    @utils.skip_method_debug_logging
    def _deserialize_text(
        self, buffer: bytes, start_offset: int, size_bytes: int,
        encoding: str = 'utf-8'
    ) -> Tuple[str, int]:
        """Deserializes text from a buffer of bytes.

        Args:
            buffer: Buffer of bytes containing the text to deserialize.
            start_offset: Offset in the buffer of the start of the section
                containing the serialized text to deserialize.
            size_bytes: Number of bytes used to store the size of the text in
                the serialization of the text.
            encoding: Encoding used for the text in the serialization.

        Returns:
            A 2-tuple containing:
                - The deserialized text.
                - The number of bytes read from the buffer to deserialize the
                    text.
        """
        offset = start_offset
        text_size = int.from_bytes(
            buffer[offset:offset + size_bytes], 'little'
        )
        offset += size_bytes

        text = buffer[offset:offset + text_size].decode(encoding)
        offset += text_size

        return (text, offset - start_offset)

    @utils.skip_method_debug_logging
    def _deserialize_article(
        self, buffer: bytes, out_article: JpnArticle
    ) -> None:
        """Deserializes an article from a buffer of bytes.

        Args:
            buffer: Buffer of bytes containing the full serialization of an
                article to deserialize.
            out_article: Article object to write the deserialized article data
                to.
        """
        offset = 0
        out_article.title, read_bytes = self._deserialize_text(
            buffer, offset, 3, 'utf-16'
        )
        offset += read_bytes
        out_article.full_text, read_bytes = self._deserialize_text(
            buffer, offset, 3, 'utf-16'
        )
        offset += read_bytes

        out_article.source_name, read_bytes = self._deserialize_text(
            buffer, offset, 1, 'utf-8'
        )
        offset += read_bytes
        out_article.source_url, read_bytes = self._deserialize_text(
            buffer, offset, 2, 'utf-8'
        )
        offset += read_bytes

        out_article.alnum_count = int.from_bytes(
            buffer[offset:offset + 2], 'little'
        )
        out_article.has_video = bool(int.from_bytes(
            [buffer[offset + 2]], 'little'
        ))
        offset += 3

        out_article.publication_datetime = datetime.fromtimestamp(
            int.from_bytes(buffer[offset:offset + 4], 'little')
        )
        offset += 4
        out_article.last_updated_datetime = datetime.fromtimestamp(
            int.from_bytes(buffer[offset:offset + 4], 'little')
        )

    def _deserialize_search_results(
        self, serialized_search_results: bytes
    ) -> List[JpnArticleSearchResult]:
        """Deserializes search results.

        Args:
            serialized_search_results: Decompressed serialization of a list of
                search results to deserialize.

        Returns:
            A list of deserialized search results.
        """
        search_results = []

        results_bytes = serialized_search_results
        search_result_count = int.from_bytes([results_bytes[0]], 'little')
        offset = 1
        for _ in range(search_result_count):
            search_result = JpnArticleSearchResult(JpnArticle(), [])

            article_oid = ObjectId(results_bytes[offset:offset + 12])
            offset += 12
            cached_article = self._redis_client.get(
                f'article:{str(article_oid)}'
            )
            if cached_article is None:
                utils.log_and_raise(
                    _log, DataAccessError,
                    'Article key for ID "{}" not found in Redis'.format(
                        article_oid
                    )
                )

            article_bytes = zlib.decompress(cached_article)
            self._deserialize_article(article_bytes, search_result.article)

            offset += self._deserialize_text_positions(
                results_bytes, offset, search_result.found_positions
            )
            search_results.append(search_result)

        return search_results

    def get(
        self, query: str
    ) -> Optional[List[JpnArticleSearchResult]]:
        """Gets the cached first page of search results for the given query.

        Args:
            query: Query to get the cached first page of search results for.

        Returns:
            A list of the cached first page search results if they exist in the
            cache, or None if no search results exist in the cache for query.
        """
        cached_results = self._redis_client.get(f'query:{query}')
        if cached_results is None:
            return None

        serialized_results = zlib.decompress(cached_results)
        return self._deserialize_search_results(serialized_results)
