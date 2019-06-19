import time
import sys

import reibun.utils as utils
from reibun.crawler import NhkNewsWebCrawler
# from reibun.datatypes import JpnArticle
from reibun.database import ReibunDb
from reibun.japanese_analysis import JapaneseTextAnalyzer

LOG_FILEPATH = './reibun_write.log'

if __name__ == '__main__':
    utils.toggle_reibun_debug_log(filepath=LOG_FILEPATH)
    time.sleep(5)

    new_articles = []
    with NhkNewsWebCrawler() as crawler:
        print('\nCrawling Most Recent\n')
        new_articles.extend(crawler.crawl_most_recent())

        print('\nCrawling Tokushu\n')
        new_articles.extend(crawler.crawl_tokushu(2))

        print('\nCrawling News UP\n')
        new_articles.extend(crawler.crawl_news_up(0))

    if len(new_articles) == 0:
        print('\nNo uncrawled articles!\n')
        sys.exit()

    with ReibunDb() as db:
        new_articles = db.filter_to_unstored_articles(new_articles)
        if len(new_articles) == 0:
            print('\nNo unstored articles!\n')
            sys.exit()

        jta = JapaneseTextAnalyzer()
        lexical_items = []
        for new_article in new_articles:
            found = jta.find_article_lexical_items(new_article)
            print(f'\nFound {len(found)} lexical items in {new_article}\n')
            lexical_items.extend(found)
        print(f'\nFound {len(lexical_items)} overall\n')

        db.write_found_lexical_items(lexical_items)

    print('\nAll done!\n')
