"""Builds the full Myaku search result cache in Redis."""

import logging

from myaku import utils
from myaku.datastore.database import CrawlDb

_log = logging.getLogger(__name__)


def main() -> None:
    """Build the full search result first page cache."""
    utils.toggle_myaku_package_log(filename_base='build_cache')
    with CrawlDb() as db:
        db.build_first_page_cache()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.build_cache')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
