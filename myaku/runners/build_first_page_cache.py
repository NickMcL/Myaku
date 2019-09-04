"""Builds the full Myaku search result cache in Redis."""

import logging

from myaku import utils
from myaku.datastore.database import CrawlDb


def main() -> None:
    with CrawlDb() as db:
        db.build_first_page_cache()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.build_cache')
    utils.toggle_myaku_package_log(filename_base='build_cache')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
