"""Celery tasks for Myaku search."""

from celery import shared_task
from django.conf import settings

from myaku import utils
from myaku.datastore import Query
from myaku.datastore.cache import NextPageCache, NextPageDirection
from myaku.datastore.index_search import ArticleIndexSearcher


@shared_task
def cache_surrounding_pages(query: Query) -> None:
    """Cache the surrounding pages for the query for the user.

    Args:
        query: Query made by a user that should have its next page loaded into
            the next page cache.
    """
    utils.toggle_myaku_package_log(filename_base='web_worker')
    utils.toggle_myaku_package_log(
        filename_base='web_worker', package='search'
    )

    cache_client = NextPageCache()
    current_page_num = query.page_num
    if current_page_num < settings.MAX_SEARCH_RESULT_PAGE:
        query.page_num = current_page_num + 1
        with ArticleIndexSearcher() as searcher:
            forward_page = searcher.search_articles(query)
        cache_client.set(
            query.user_id, forward_page, NextPageDirection.FORWARD
        )

    # Don't cache the backward page unless it's > 1 because the page 1 is
    # always in the first page cache.
    if current_page_num > 2:
        query.page_num = current_page_num - 1
        with ArticleIndexSearcher() as searcher:
            backward_page = searcher.search_articles(query)
        cache_client.set(
            query.user_id, backward_page, NextPageDirection.BACKWARD
        )
