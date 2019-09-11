"""Script to check if stored articles have been removed from their site.

If an article has bee removed from its site, the page_removed field is set to
True in the database for that article.

Usage: check_for_removed_articles.py <source_name> [<last_checked_id>]

<source_name>: The source name whose articles to check if removed. Mandatory.
<last_checked_id>: Article database ID last checked if removed on previous runs
    of this script. If given, the script will not recheck any of the IDs
    checked on the last run. Optional.
"""

import logging
import sys
from typing import Any, Dict, Optional, Tuple

import pymongo
import requests
from bson.objectid import ObjectId

from myaku import utils
from myaku.datastore import DataAccessMode
from myaku.datastore.database import CrawlDb
from myaku.errors import ScriptArgsError


class ArticleRemovedChecker(object):
    """Checker for if articles have been removed from their site."""

    def __init__(self, request_timeout: int = 30) -> None:
        """Init the requests session to use for 404 checks.

        Args:
            request_timeout: Timeout to use for web requests.
        """
        self._timeout = request_timeout
        self._session = requests.Session()

    @utils.rate_limit(1.5, 3)
    @utils.retry_on_exception(8, utils.REQUEST_RETRY_EXCEPTIONS)
    def check_if_404(self, url: str) -> bool:
        """Check if a request to the article url returns a 404 response."""
        _log.debug('Making GET request to url "%s"', url)
        response = self._session.get(url, timeout=self._timeout)
        _log.debug('Response received with code %s', response.status_code)
        if response.status_code != 404:
            response.raise_for_status()

        return response.status_code == 404


def parse_script_args() -> Tuple[str, Optional[ObjectId]]:
    """Parse the args given to this script.

    Returns:
        A 2-tuple with these elements:
            1. Source name whose articles to check if removed. Always given.
            2. Article database ID last checked if removed for the given source
                name. If not given, will be None.
    """
    if len(sys.argv) not in (2, 3):
        raise ScriptArgsError(
            'run_crawl.py script given {} args instead of 2 or 3: {}'.format(
                len(sys.argv), sys.argv
            )
        )

    if len(sys.argv) == 2:
        return (sys.argv[1], None)
    return (sys.argv[1], sys.argv[2])


def main() -> None:
    """Check if any articles in the crawl db are no longer reachable."""
    source_name, last_checked_id = parse_script_args()
    with CrawlDb(DataAccessMode.READ_UPDATE) as db:
        query: Dict[str, Any] = {'source_name': source_name}
        if last_checked_id:
            query['_id'] = {'$gt': ObjectId(last_checked_id)}
        cursor = db._article_collection.find(query, {'source_url': 1})
        cursor.sort('_id', pymongo.ASCENDING)

        removed_count = 0
        checker = ArticleRemovedChecker()
        for i, doc in enumerate(cursor):
            if i % 100 == 0:
                _log.info('Checked %s\tRemoved %s', i, removed_count)

            if checker.check_if_404(doc['source_url']):
                removed_count += 1
                result = db._article_collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': {'page_removed': True}}
                )
                _log.debug(
                    'Updated article with _id "%s" as removed: %s',
                    doc['_id'], result.raw_result
                )
            else:
                _log.debug(
                    'Article with _id "%s" has not been removed', doc['_id']
                )


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.check_for_removed_articles')
    utils.toggle_myaku_package_log(filename_base='check_for_removed_articles')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
