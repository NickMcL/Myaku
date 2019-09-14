"""Subpackage for data storage-related modules for Myaku.

Types used across all data storage-related modules are defined in file.
"""

import enum
import functools
import logging
from dataclasses import dataclass
from typing import Callable, List

from myaku import utils
from myaku.datatypes import ArticleTextPosition, JpnArticle
from myaku.errors import DataAccessPermissionError

_log = logging.getLogger(__name__)


@enum.unique
class QueryType(enum.Enum):
    """Match type for a Japanese lexical item query for articles.

    Currently, Myaku just uses the EXACT type for everything because the
    DEFINITE_ALT_FORMS and POSSIBLE_ALT_FORMS types have not been implemented
    yet.

    Attributes:
        EXACT: Only match articles containing a term whose base form matches
            the query exactly.

            For example, searching for "落ち込む" will not match
            "落ちこむ" because they do not match exactly even though they are
            definte alternate forms of the same lexical item.
        DEFINITE_ALT_FORMS: In addition to articles matched by EXACT, also
            match articles containing any term whose base form is a definite
            alternate form of a lexical item that has a form that exactly
            matches the query.

            For example, searching for "落ち込む" will also match "落ちこむ"
            because they are definite alternate forms of the same lexical item,
            but searching for "変える" will not match "かえる" even though
            "かえる" is an alternate form of it because it is not a definite
            alternate form. This is because "かえる" is also an alternate form
            for words like "帰る" which are completely different lexical items
            that do not have the searched "変える" as an alternate form.

        POSSIBLE_ALT_FORMS: In addition to the articles matched by
            DEFNITE_ALT_FORMS, also match articles containing any term whose
            base form is an alternate form of a lexical item that has a form
            that exactly matches the query, even if that base form is also an
            alternate form of other lexical items that do not have a form that
            exactly matches the query.

            For example, searching for "変える" will also match "かえる"
            because "かえる" is an alternate form of it even though "かえる" is
            also an alternate form for "帰る" which is a completely different
            lexical item that does not have the searched "変える" as an
            alternate form.
    """
    EXACT = 1
    DEFINITE_ALT_FORMS = 3
    POSSIBLE_ALT_FORMS = 2


@dataclass
class Query(object):
    """Lexical item query for articles in the Myaku crawl database.

    Attributes:
        query_str: The lexical item string being searched for by this query.
        page_num: The page number of the search results being queried.
        query_type: The type of matching to use when searching for articles
            that match the lexical item being queried.
        user_id: ID of the user making the query. Can be used to get search
            result pages that were pre-fetched into a cache for the user.
    """
    query_str: str = None
    page_num: int = None
    query_type: QueryType = QueryType.EXACT
    user_id: str = None

    def __str__(self) -> str:
        """Get a string representation of the query."""
        return '|'.join([
            str(self.query_str),
            str(self.page_num),
            str(self.query_type),
            str(self.user_id)
        ])


@dataclass
class SearchResult(object):
    """Article result of a Myaku crawl database lexical item query.

    Attributes:
        article: Article matching the found lexical item search query.
        found_positions: Positions of the found lexical items in the article
            that matched the search query.
        matched_base_forms: Lexical item base forms that matched the search
            query that were found in the article.
        quality_score: Quality score of this search result. See the scorers
            module for more info on how quality scoring is done.
    """
    article: JpnArticle
    found_positions: List[ArticleTextPosition]
    matched_base_forms: List[str] = None
    quality_score: int = None


@dataclass
class SearchResultPage(object):
    """Page of article results of a Myaku crawl database lexical item query.

    Attributes:
        query: Query that this is a page of serach results for.
        total_results: The overall total number of search results found in the
            database for the query. Note that this is NOT the number of results
            on just this page, but the total overall number of results.
        search_results: Article search results for the page in ranked order.
    """
    query: Query = None
    total_results: int = None
    search_results: List[SearchResult] = None


@enum.unique
class DataAccessMode(enum.Enum):
    """Database client access modes. Determine read-write permissions.

    Attributes:
        READ: Can only read data from database. Cannot make any modifications
            to the database.
        READ_UPDATE: Can read data and update existing objects in the database.
            Cannot write new objects to the database.
        READ_WRITE: Can read data and write data to the database. No
            restrictions on what modifications can be made to the database.
    """
    READ = 1
    READ_UPDATE = 2
    READ_WRITE = 3

    def has_update_permission(self) -> bool:
        """Return True if the access mode as update permission."""
        return (
            self is DataAccessMode.READ_UPDATE
            or self is DataAccessMode.READ_WRITE
        )

    def has_write_permission(self) -> bool:
        """Return True if the access mode as write permission."""
        return self is DataAccessMode.READ_WRITE


def require_write_permission(func: Callable) -> Callable:
    """Check that the client has db write permission before running func.

    Can only be used to wrap db class methods for a db class with a access_mode
    member variable.

    Raises:
        DbPermissionError: If the client does not have write permission.
    """
    @functools.wraps(func)
    def wrapper_require_write_permission(*args, **kwargs):
        if not args[0].access_mode.has_write_permission():
            utils.log_and_raise(
                _log, DataAccessPermissionError,
                'Write operation "{}" was attempted with only {} '
                'permission'.format(
                    utils.get_full_name(func), args[0].access_mode.name
                )
            )

        value = func(*args, **kwargs)
        return value
    return wrapper_require_write_permission


def require_update_permission(func: Callable) -> Callable:
    """Check that the client has db update permission before running func.

    Can only be used to wrap db class methods for a db class with a access_mode
    member variable.

    Raises:
        DbPermissionError: If the client does not have update permission.
    """
    @functools.wraps(func)
    def wrapper_require_write_permission(*args, **kwargs):
        if not args[0].access_mode.has_update_permission():
            utils.log_and_raise(
                _log, DataAccessPermissionError,
                'Update operation "{}" was attempted with only {} '
                'permission'.format(
                    utils.get_full_name(func), args[0].access_mode.name
                )
            )

        value = func(*args, **kwargs)
        return value
    return wrapper_require_write_permission
