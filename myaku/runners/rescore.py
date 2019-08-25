"""Script for rescoring all articles and found lexical items in the db."""

import logging
import time
from typing import List

import myaku.utils as utils
from myaku.database import DbAccessMode, MyakuCrawlDb
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


def rescore_articles(
    db: MyakuCrawlDb, scorer: MyakuArticleScorer
) -> List[str]:
    """Rescores all articles in the Myaku db.

    Args:
        db: Database client to use to update the articles.
        scorer: Scorer to use the rescore the articles.

    Returns:
        A list of the database IDs for all of the articles whose article
        quality score in the database was changed by the update.
    """
    timer = Timer('article rescore')

    current_article = 1
    updated_article_ids = []
    article_count = db.get_article_count()
    article_gen = db.read_all_articles()
    for article in article_gen:
        scorer.score_article(article)
        updated = db.update_article_score(article)
        if updated:
            updated_article_ids.append(article.database_id)

        if current_article % 100 == 0:
            _log.info(
                'Rescored %s / %s articles', current_article, article_count
            )
        current_article += 1

    _log.info(
        '{} articles had their quality score updated'.format(
            len(updated_article_ids)
        )
    )
    timer.stop()
    return updated_article_ids


def recalculate_found_lexical_item_scores(
    db: MyakuCrawlDb, updated_article_ids: List[str]
) -> None:
    """Recalculate found lexical items scores if necessary.

    Found lexical items whose article quality score was updated will need to
    have their composite quality score updated.
    """
    timer = Timer('found lexical item recalculation')
    recalculated_count = db.recalculate_found_lexical_item_scores(
        updated_article_ids
    )
    _log.info(
        '{} found lexical items had their quality score recalculated'.format(
            recalculated_count
        )
    )
    timer.stop()


def main() -> None:
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)
    timer = Timer('rescore')

    scorer = MyakuArticleScorer()
    with MyakuCrawlDb(DbAccessMode.READ_UPDATE) as db:
        updated_article_ids = rescore_articles(db, scorer)
        if len(updated_article_ids) > 0:
            recalculate_found_lexical_item_scores(db, updated_article_ids)

    timer.stop()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.rescore')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
