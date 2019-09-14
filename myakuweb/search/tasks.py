"""Celery tasks for Myaku search."""

from celery import shared_task

from myaku import utils
from myaku.datastore import DataAccessMode, JpnArticleQueryType
from myaku.datastore.cache import NextPageCache
from myaku.datastore.database import CrawlDb


@shared_task
def cache_next_page_for_user(
    user_id: str, query: str, match_type_int: int, page_num: int
) -> None:
    """Cache the next page for the user in the next page cache.

    Args:
        user_id: User ID to cache the next page for in the next page cache.
        query: Lexical item base form value to use to search for articles.
        match_type_int: Type of matching to use when searching for articles
            whose text contains terms matching the query. The int will be
            converted to a JpnArticleQueryType enum value.
        page_num: Current page of the search results requested by the user. The
            next page from this page number will be one the cached. Page
            indexing starts from 1.
    """
    utils.toggle_myaku_package_log(filename_base='web_worker')
    utils.toggle_myaku_package_log(
        filename_base='web_worker', package='search'
    )

    match_type = JpnArticleQueryType(match_type_int)
    with CrawlDb(DataAccessMode.READ) as db:
        next_page = db.search_articles(
            query, match_type, page_num + 1, user_id
        )
    next_page_cache_client = NextPageCache()
    next_page_cache_client.set(user_id, next_page)
