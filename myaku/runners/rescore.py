"""Script for rescoring all articles in the Myaku db."""

import logging
import time

import myaku.utils as utils
from myaku.database import MyakuCrawlDb
from myaku.scorer import MyakuArticleScorer

_log = logging.getLogger(__name__)

LOG_NAME = 'rescore'


def main() -> None:
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)

    start_time = time.perf_counter()
    scorer = MyakuArticleScorer()
    with MyakuCrawlDb() as db:
        current_article = 1
        article_count = db.get_article_count()
        article_gen = db.read_all_articles()

        _log.info('Starting rescore')
        for article in article_gen:
            scorer.score_article(article)
            db.update_article_score(article)

            # fli_gen = db.read_article_found_lexical_items(article)
            # for fli in fli_gen:
                # scorer.score_fli_modifier(fli)
                # db.update_found_lexical_item_scores(fli)

            if current_article % 10 == 0:
                _log.info(
                    'Rescored %s / %s articles', current_article, article_count
                )
            current_article += 1

    end_time = time.perf_counter()
    _log.info('\nRescore took {:.2f} minutes'.format(
        (end_time - start_time) / 60
    ))


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.rescore')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
