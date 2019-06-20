import time
import sys

from reibun.utils import toggle_reibun_debug_log
from reibun.database import ReibunDb
from reibun.japanese_analysis import JapaneseTextAnalyzer

LOG_FILEPATH = './reibun_reparse.log'

if __name__ == '__main__':
    toggle_reibun_debug_log(filepath=LOG_FILEPATH)

    start_time = time.perf_counter()
    jta = JapaneseTextAnalyzer()
    with ReibunDb() as db:
        if not db.is_found_lexical_items_db_empty():
            print('Found lexical items db is not empty')
            sys.exit()

        articles = db.read_articles()
        print('{} articles read from database'.format(len(articles)))

        for i, article in enumerate(articles):
            flis = jta.find_article_lexical_items(article)
            db.write_found_lexical_items(flis, False)
            print('({} / {}): Wrote {} lexical items for {}'.format(
                i + 1, len(articles), len(flis), article
            ))

    end_time = time.perf_counter()
    print('\nReparse took {:.2f} minutes'.format((end_time - start_time) / 60))
