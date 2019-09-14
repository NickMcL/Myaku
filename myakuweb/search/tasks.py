"""Celery tasks for Myaku search."""

from celery import shared_task

from myaku import utils
from myaku.datastore import DataAccessMode, Query
from myaku.datastore.cache import NextPageCache
from myaku.datastore.database import CrawlDb


@shared_task
def cache_next_page_for_user(query: Query) -> None:
    """Cache the next page for the user of the query in the next page cache.

    Args:
        query: Query made by a user that should have its next page loaded into
            the next page cache.
    """
    utils.toggle_myaku_package_log(filename_base='web_worker')
    utils.toggle_myaku_package_log(
        filename_base='web_worker', package='search'
    )

    # Change the query into a query for the next page of results.
    query.page_num += 1
    with CrawlDb(DataAccessMode.READ) as db:
        next_page = db.search_articles(query)

    next_page_cache_client = NextPageCache()
    next_page_cache_client.set(query.user_id, next_page)
