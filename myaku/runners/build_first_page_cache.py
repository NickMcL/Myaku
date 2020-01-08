"""Builds the full Myaku search result cache in Redis."""

import logging

from myaku import utils
from myaku.datastore import Query
from myaku.datastore.cache import FirstPageCache
from myaku.datastore.database import ArticleIndexDb
from myaku.datastore.index_search import ArticleIndexSearcher

_log = logging.getLogger(__name__)


def get_base_form_count(db: ArticleIndexDb) -> int:
    """Get the total found lexical item base form count for the index db."""
    cursor = db.found_lexical_item_collection.aggregate([
        {'$match': {'base_form': {'$gt': ''}}},
        {'$group': {'_id': '$base_form'}},
        {'$count': 'total'}
    ])
    docs = list(cursor)
    return docs[0]['total'] if len(docs) > 0 else 0


# Debug level logging can be extremely noisy (can be over 1gb) when enabled
# during this function, so switch to info level if logging.
@utils.set_package_log_level(logging.INFO)
def build_cache(db: ArticleIndexDb, searcher: ArticleIndexSearcher) -> None:
    """Build the first page cache for the Myaku article index."""
    first_page_cache = FirstPageCache()
    base_form_total = get_base_form_count(db)
    _log.info(
        f'Will build the first page cache for all {base_form_total:,} '
        f'base forms currently in db'
    )

    cursor = db.found_lexical_item_collection.aggregate([
        {'$match': {'base_form': {'$gt': ''}}},
        {'$group': {'_id': '$base_form'}}
    ])
    for i, doc in enumerate(cursor):
        base_form = doc['_id']
        search_result_page = searcher.search_articles_using_db(
            Query(base_form, 1)
        )
        first_page_cache.set(search_result_page)

        if (i + 1) % 1000 == 0 or (i + 1) == base_form_total:
            _log.info(
                f'Cached first page count: {i + 1:,} / {base_form_total:,}'
            )

    _log.info('First page cache built successfully')


def main() -> None:
    """Build the full search result first page cache."""
    utils.toggle_myaku_package_log(filename_base='build_cache')
    with ArticleIndexDb() as db, ArticleIndexSearcher() as searcher:
        build_cache(db, searcher)


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.build_cache')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
