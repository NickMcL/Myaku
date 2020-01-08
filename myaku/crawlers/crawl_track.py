"""Objects for tracking web items crawled by Myaku crawlers."""

import logging
from datetime import datetime
from typing import Dict, List, Set

from myaku import utils
from myaku.datastore import DataAccessMode
from myaku.datastore.database import ArticleIndexDb
from myaku.datatypes import Crawlable, Crawlable_co

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class CrawlTracker(object):
    """Tracker for items crawled by Myaku crawlers."""

    def __init__(self):
        """Initialize the Myaku index database connection."""
        self._db = ArticleIndexDb(DataAccessMode.READ_UPDATE)

    def close(self) -> None:
        """Close the connection to the Myaku index database."""
        self._db.close()

    def __enter__(self) -> 'CrawlTracker':
        """Return self on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Invoke close() method of self on context exit."""
        self.close()

    @utils.skip_method_debug_logging
    def _get_last_crawled_map(
        self, crawlable_items: List[Crawlable_co]
    ) -> Dict[str, datetime]:
        """Get a mapping from Crawlable items to their last crawled datetime.

        Args:
            crawlable_items: List of crawlable items to look up the last
                crawled datetime for in the Myaku index database.

        Returns:
            A mapping from the source url of one of the given crawlable items
            to the last crawled datetime for that item.
            If the source url of one of the given crawlable items is not in the
            returned dictionary, it means that it has never been crawled
            before.
        """
        if len(crawlable_items) == 0:
            return {}

        cursor = self._db.crawlable_coll_map[type(crawlable_items[0])].find(
            {'source_url': {'$in': [i.source_url for i in crawlable_items]}},
            {'_id': -1, 'source_url': 1, 'last_crawled_datetime': 1}
        )
        last_crawled_map = {
            d['source_url']: d['last_crawled_datetime'] for d in cursor
        }

        return last_crawled_map

    @utils.skip_method_debug_logging
    def _get_skipped_crawlable_urls(
        self, crawlable_items: List[Crawlable_co]
    ) -> Set[str]:
        """Get the crawl skipped source urls from the given crawlable items.

        Args:
            crawlable_items: List of crawlable items whose source urls to look
                up in the Myaku index database to check which are marked as
                having been skipped during crawling.

        Returns:
            A set containing the source urls for the given crawlable items that
            are marked in the database as having been skipped during crawling.
        """
        if len(crawlable_items) == 0:
            return set()

        cursor = self._db.crawl_skip_collection.find(
            {'source_url': {'$in': [i.source_url for i in crawlable_items]}},
            {'_id': -1, 'source_url': 1}
        )
        return set(doc['source_url'] for doc in cursor)

    def filter_crawlable_to_updated(
        self, crawlable_items: List[Crawlable_co]
    ) -> List[Crawlable_co]:
        """Return new list with the items updated since last crawled.

        The new list includes items that have never been crawled as well.
        """
        total_items = len(crawlable_items)
        _log.debug('Will apply filter to %s crawlable items', total_items)
        if total_items == 0:
            return []
        last_crawled_map = self._get_last_crawled_map(crawlable_items)
        crawl_skip_urls = self._get_skipped_crawlable_urls(crawlable_items)

        updated_items = []
        unstored_count = 0
        partial_stored_count = 0
        updated_count = 0
        skipped_count = 0
        for item in crawlable_items:
            item_url = item.source_url
            if item_url in crawl_skip_urls:
                skipped_count += 1
            elif item_url not in last_crawled_map:
                unstored_count += 1
                updated_items.append(item)
            elif last_crawled_map[item_url] is None:
                partial_stored_count += 1
                updated_items.append(item)
            elif (item.last_updated_datetime is not None
                  and item.last_updated_datetime > last_crawled_map[item_url]):
                updated_count += 1
                updated_items.append(item)

        _log.debug(
            'Filtered to %s unstored, %s partially stored, and %s updated '
            'crawlable items of type %s (%s crawl skipped)',
            unstored_count, partial_stored_count, updated_count,
            type(crawlable_items[0]), skipped_count
        )
        return updated_items

    def update_last_crawled_datetime(self, item: Crawlable) -> None:
        """Update the last crawled datetime of the item in the Myaku database.

        If a crawlable item with the source url of the given item is not found
        in the database, marks the source url as having been skipped during
        crawling instead.
        """
        _log.debug(
            'Updating the last crawled datetime for item "%s" of type %s',
            item, type(item)
        )
        result = self._db.crawlable_coll_map[type(item)].update_one(
            {'source_url': item.source_url},
            {'$set': {'last_crawled_datetime': item.last_crawled_datetime}}
        )
        _log.debug('Update result: %s', result.raw_result)

        if result.matched_count == 0:
            _log.debug(
                'Source url "%s" for item was not found in the db, so marking '
                'as crawl skipped', item.source_url
            )
            self._db.crawl_skip_collection.insert_one({
                'source_url': item.source_url,
                'source_name': item.source_name,
                'last_crawled_datetime': item.last_crawled_datetime
            })
