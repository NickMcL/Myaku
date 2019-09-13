"""Functions for efficient serializing of Myaku search result data."""

import logging
import zlib
from datetime import datetime
from typing import Dict, List, NamedTuple, Tuple

from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import JpnArticleSearchResult, JpnArticleSearchResultPage
from myaku.datatypes import ArticleTextPosition, JpnArticle

_log = logging.getLogger(__name__)

# Gzip compression level to use when compressing the serialized byte strings.
_COMPRESS_LEVEL = 1


class SerializedSearchResultPage(NamedTuple):
    """Serialization of a page of search results.

    Attributes:
        query: Serialized byte string of the query for the page of search
            results.
        search_results: Serialized byte string of the search results for the
            page. Only includes the ObjectIds for each article for the results
            instead of the full article data which is in the articles attr.
        article_map: Dictionary mapping article database ID to the serialized
            byte string for the data for that article.
    """
    query: bytes
    search_results: bytes
    article_map: Dict[str, bytes]


def _serialize_text(
    text: str, size_bytes: int, encoding: str = 'utf-8'
) -> List[bytes]:
    """Serialize text using a specified encoding.

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


def serialize_query(page: JpnArticleSearchResultPage) -> bytes:
    """Serialize the query for a page of article search results.

    Serializes the query string and page number for the query.

    Args:
        page: Page of article search results for a query.

    Returns:
        Serialized byte string for the query for the page of search results.
    """
    bytes_list: List[bytes] = []
    bytes_list.append(page.page_num.to_bytes(1, 'little'))

    # Encode query string using utf-16 because it is more space efficient than
    # utf-8 for Japanese characters.
    query_str_bytes = _serialize_text(page.query, 1, 'utf-16')
    bytes_list.extend(query_str_bytes)

    return zlib.compress(b''.join(bytes_list), _COMPRESS_LEVEL)


def serialize_search_results(page: JpnArticleSearchResultPage) -> bytes:
    """Serialize search results for a page of article search results.

    Only serializes the total results, article IDs, and found positions data
    for the search results page.

    Does not serialize any of the data for the articles for the search results
    expect their IDs, so the article data should be serialized separately using
    serialize_article.

    Args:
        page: Page of article search results for a query.

    Returns:
        Serialized byte string for the search result data, not including the
        article data except IDs.
    """
    bytes_list = []
    bytes_list.append(page.total_results.to_bytes(3, 'little'))
    bytes_list.append(len(page.search_results).to_bytes(1, 'little'))
    for result in page.search_results:
        bytes_list.append(ObjectId(result.article.database_id).binary)
        bytes_list.append(len(result.found_positions).to_bytes(2, 'little'))
        for pos in result.found_positions:
            bytes_list.append(pos.start.to_bytes(2, 'little'))
            bytes_list.append(pos.len.to_bytes(1, 'little'))

    return zlib.compress(b''.join(bytes_list), _COMPRESS_LEVEL)


def serialize_article(article: JpnArticle) -> bytes:
    """Serialize a single article for a search result.

    Does not serialize all attributes of the article. Only serializes the
    attributes used in displaying search results.

    Args:
        article: Article from a search result to serialize.

    Returns:
        Serialized byte string for the article.
    """
    bytes_list: List[bytes] = []

    # Encode title and full text using utf-16 because it is more space
    # efficient than utf-8 for Japanese characters.
    title_bytes = _serialize_text(article.title, 3, 'utf-16')
    bytes_list.extend(title_bytes)
    full_text_bytes = _serialize_text(article.full_text, 3, 'utf-16')
    bytes_list.extend(full_text_bytes)

    # Encode source name and url using utf-8 because it is more space
    # efficeient than utf-16 for ascii characters.
    bytes_list.extend(_serialize_text(article.source_name, 1))
    bytes_list.extend(_serialize_text(article.source_url, 2))

    bytes_list.append(article.alnum_count.to_bytes(2, 'little'))
    bytes_list.append(int(article.has_video).to_bytes(1, 'little'))

    pub_dt_timestamp = int(article.publication_datetime.timestamp())
    bytes_list.append(pub_dt_timestamp.to_bytes(4, 'little'))
    up_dt_timestamp = int(article.last_updated_datetime.timestamp())
    bytes_list.append(up_dt_timestamp.to_bytes(4, 'little'))

    return zlib.compress(b''.join(bytes_list), _COMPRESS_LEVEL)


@utils.add_debug_logging
def serialize_search_result_page(
    page: JpnArticleSearchResultPage
) -> SerializedSearchResultPage:
    """Serialize a page of search results.

    Does not serialize all attributes of the articles for the search results.
    Only serializes the attributes used in displaying search results.

    This means that deserializing a page serialized with this function will
    result in some of the article data being lost.

    Args:
        page: Page of article search results to serialize.

    Returns:
        Named tuple with the serialized byte strings for the query, search
        results, and articles for the given page of search results.
    """
    query_bytes = serialize_query(page)
    search_results_bytes = serialize_search_results(page)

    article_bytes_map = {}
    for result in page.search_results:
        article_bytes = serialize_article(result.article)
        article_bytes_map[result.article.database_id] = article_bytes

    return SerializedSearchResultPage(
        query_bytes, search_results_bytes, article_bytes_map
    )


def _deserialize_text(
    buffer: bytes, start_offset: int, size_bytes: int, encoding: str = 'utf-8'
) -> Tuple[str, int]:
    """Deserialize text from a buffer of bytes.

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


@utils.add_debug_logging
def deserialize_query(
    buffer: bytes, out_page: JpnArticleSearchResultPage
) -> None:
    """Deserialize a query from a buffer of bytes.

    A serialized query contains the query string and page number for query, so
    that data will be populated in the out_page.

    Args:
        buffer: Buffer of bytes containing the serialization of a query to
            deserialize.
        out_page: Search results page object to write the deserialized query
            data to.
    """
    buffer = zlib.decompress(buffer)
    offset = 0

    out_page.page_num = int.from_bytes([buffer[offset]], 'little')
    offset += 1

    out_page.query, read_bytes = _deserialize_text(
        buffer, offset, 1, 'utf-16'
    )


@utils.add_debug_logging
def deserialize_search_results(
    buffer: bytes, out_page: JpnArticleSearchResultPage
) -> None:
    """Deserialize search results from a buffer of bytes.

    Serialized search results only contain the total results, article
    IDs, and found positions of a page of search results, so only that data
    will be populated in the out_page.

    Args:
        buffer: Buffer of bytes containing the serialization of search results
            to deserialize.
        out_page: Search results page object to write the deserialized search
            result data to.
    """
    buffer = zlib.decompress(buffer)
    offset = 0

    out_page.total_results = int.from_bytes(
        buffer[offset:offset + 3], 'little'
    )
    result_count = int.from_bytes([buffer[offset + 3]], 'little')
    offset += 4

    out_page.search_results = []
    for _ in range(result_count):
        search_result = JpnArticleSearchResult(JpnArticle(), [])

        article_oid = ObjectId(buffer[offset:offset + 12])
        search_result.article.database_id = str(article_oid)
        offset += 12

        found_pos_count = int.from_bytes(buffer[offset:offset + 2], 'little')
        offset += 2
        for _ in range(found_pos_count):
            found_pos = ArticleTextPosition(
                start=int.from_bytes(buffer[offset:offset + 2], 'little'),
                len=int.from_bytes([buffer[offset + 2]], 'little')
            )
            search_result.found_positions.append(found_pos)
            offset += 3

        out_page.search_results.append(search_result)


def deserialize_article(buffer: bytes, out_article: JpnArticle) -> None:
    """Deserialize an article from a buffer of bytes.

    Args:
        buffer: Buffer of bytes containing the serialization of an article to
            deserialize.
        out_article: Article object to write the deserialized article data to.
    """
    buffer = zlib.decompress(buffer)
    offset = 0

    out_article.title, read_bytes = _deserialize_text(
        buffer, offset, 3, 'utf-16'
    )
    offset += read_bytes
    out_article.full_text, read_bytes = _deserialize_text(
        buffer, offset, 3, 'utf-16'
    )
    offset += read_bytes

    out_article.source_name, read_bytes = _deserialize_text(
        buffer, offset, 1, 'utf-8'
    )
    offset += read_bytes
    out_article.source_url, read_bytes = _deserialize_text(
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
