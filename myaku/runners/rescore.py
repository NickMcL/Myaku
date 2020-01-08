"""Script for rescoring all articles and found lexical items in the db."""

import logging
import time

from myaku import utils
from myaku.datastore.index_rescore import rescore_article_index

_log = logging.getLogger(__name__)

LOG_NAME = 'rescore'


class Timer(object):
    """Timer for measuring and logging a duration."""

    def __init__(self, task_name: str) -> None:
        """Start the timer."""
        self._task_name = task_name

        _log.info('\nStarting {}\n'.format(task_name))
        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Stop the timer and log the duration."""
        duration = time.perf_counter() - self._start_time
        _log.info(
            '\n{} took {:.2f} minutes\n'.format(
                self._task_name.capitalize(), duration / 60
            )
        )


def main() -> None:
    """Update the scores of the articles in the crawl db."""
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)
    timer = Timer('rescore')
    rescore_article_index()
    timer.stop()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.rescore')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
