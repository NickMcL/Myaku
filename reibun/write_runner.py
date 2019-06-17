import sys

import reibun.utils as utils
from reibun.crawler import NhkNewsWebCrawler
# from reibun.datatypes import JpnArticle
from reibun.database import ReibunDb
from reibun.japanese_analysis import JapaneseTextAnalyzer

# from datetime import datetime

# from reibun.sample_text import SAMPLE_TEXT

OTHER_TEXT = '鯖を読んで五歳ほど若くいう'

TEXT_SRC_URL = 'https://www.aozora.gr.jp/cards/001095/files/42618_21410.html'

if __name__ == '__main__':
    utils.toggle_reibun_debug_log()
    # article = JpnArticle(
    # title='桜の森の満開の下',
    # full_text=SAMPLE_TEXT,
    # source_url=TEXT_SRC_URL,
    # source_name='Aozora',
    # publication_datetime=datetime.utcnow(),
    # scraped_datetime=datetime.utcnow()
    # )

    with NhkNewsWebCrawler() as crawler:
        new_articles = crawler.crawl_most_recent()

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
