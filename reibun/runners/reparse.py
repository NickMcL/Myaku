import time

from reibun.utils import toggle_reibun_debug_log
from reibun.database import ReibunDb
from reibun.japanese_analysis import JapaneseTextAnalyzer

LOG_FILENAME = 'reparse_run.log'


def main() -> None:
    toggle_reibun_debug_log(filename=LOG_FILENAME)

    start_time = time.perf_counter()
    jta = JapaneseTextAnalyzer()
    with ReibunDb() as db:
        articles = db.read_articles()
        print('{} articles read from database'.format(len(articles)))

        for i, article in enumerate(articles):
            flis = jta.find_article_lexical_items(article)
            db.delete_article_found_lexical_items(article)
            db.write_found_lexical_items(flis, False)
            print('({} / {}): Wrote {} lexical items for {}'.format(
                i + 1, len(articles), len(flis), article
            ))

    end_time = time.perf_counter()
    print('\nReparse took {:.2f} minutes'.format((end_time - start_time) / 60))


if __name__ == '__main__':
    main()
