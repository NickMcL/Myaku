"""Run a reparse and re-analysis of articles in the crawl db."""

import time

from myaku import utils
from myaku.datastore import DataAccessMode
from myaku.datastore.database import CrawlDb
from myaku.japanese_analysis import JapaneseTextAnalyzer

LOG_NAME = 'reparse'


def main() -> None:
    """Rerun the Japanese text analyzer for all articles in the crawl db."""
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)

    start_time = time.perf_counter()
    jta = JapaneseTextAnalyzer()
    with CrawlDb(DataAccessMode.READ_WRITE) as db:
        articles = db.read_all_articles()

        for i, article in enumerate(articles):
            flis = jta.find_article_lexical_items(article)
            db.delete_article_found_lexical_items(article)
            db.write_found_lexical_items(flis, False)
            print('({:,}): Wrote {:,} lexical items for {}'.format(
                i + 1, len(flis), article
            ))

    end_time = time.perf_counter()
    print('\nReparse took {:.2f} minutes'.format((end_time - start_time) / 60))


if __name__ == '__main__':
    main()
