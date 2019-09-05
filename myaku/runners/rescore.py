"""Script for rescoring all articles and found lexical items in the db."""

import logging
import time

from myaku import utils
from myaku.datastore import DataAccessMode
from myaku.datastore.database import CrawlDb
from myaku.scorer import MyakuArticleScorer

_log = logging.getLogger(__name__)

LOG_NAME = 'rescore'


class Timer(object):
    """Measures and logs a time duration."""

    def __init__(self, task_name: str) -> None:
        """Starts the timer."""
        self._task_name = task_name

        _log.info('\nStarting {}\n'.format(task_name))
        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Stops the timer and logs the duration."""
        duration = time.perf_counter() - self._start_time
        _log.info(
            '\n{} took {:.2f} minutes\n'.format(
                self._task_name.capitalize(), duration / 60
            )
        )


def rescore_articles(db: CrawlDb, scorer: MyakuArticleScorer) -> None:
    """Rescores all articles in the Myaku db.

    Args:
        db: Database client to use to update the articles.
        scorer: Scorer to use the rescore the articles.

    Returns:
        A list of the database IDs for all of the articles whose article
        quality score in the database was changed by the update.
    """
    timer = Timer('article rescore')

    article_count = db.get_article_count()
    article_gen = db.read_all_articles()
    updated_count = 0
    for i, article in enumerate(article_gen):
        if i % 100 == 0:
            _log.info('Rescored %s / %s articles', i, article_count)

        scorer.score_article(article)
        updated = db.update_article_score(article)
        if updated:
            updated_count += 1

    _log.info('%s articles had their quality score updated', updated_count)
    timer.stop()


def main() -> None:
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)
    timer = Timer('rescore')

    scorer = MyakuArticleScorer()
    with CrawlDb(DataAccessMode.READ_UPDATE, True) as db:
        rescore_articles(db, scorer)

    timer.stop()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.rescore')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
