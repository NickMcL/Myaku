import time

import reibun.utils as utils
from reibun.crawler import NhkNewsWebCrawler
from reibun.database import ReibunDb
from reibun.japanese_analysis import JapaneseTextAnalyzer

LOG_FILEPATH = './reibun_write.log'

if __name__ == '__main__':
    utils.toggle_reibun_debug_log(filepath=LOG_FILEPATH)
    time.sleep(5)

    jta = JapaneseTextAnalyzer()
    overall_fli_count = 0
    overall_article_count = 0
    with ReibunDb() as db, NhkNewsWebCrawler() as crawler:
        crawls = []
        crawls.append(('Most Recent', crawler.crawl_most_recent(
        )))
        crawls.append(('Douga', crawler.crawl_douga(
        )))
        crawls.append(('News Up', crawler.crawl_news_up()))
        crawls.append(('Tokushu', crawler.crawl_tokushu()))

        for crawl in crawls:
            print('\nCrawling {}\n'.format(crawl[0]))

            crawl_fli_count = 0
            crawl_article_count = 0
            for article in crawl[1]:
                new_articles = db.filter_to_unstored_articles([article])
                if len(new_articles) == 0:
                    print('Article {} already stored!'.format(article))
                    continue
                new_article = new_articles[0]

                flis = jta.find_article_lexical_items(new_article)
                db.write_found_lexical_items(flis)

                print('Found {} lexical items in {}'.format(
                    len(flis), new_article
                ))
                crawl_fli_count += len(flis)
                crawl_article_count += 1

            print('\nFound {} lexical items during {} crawl\n'.format(
                crawl_fli_count, crawl[0]
            ))
            overall_fli_count += crawl_fli_count
            overall_article_count += crawl_article_count

    print(
        '\nFound {} new lexical items across {} articles overall\n'.format(
            overall_fli_count, overall_article_count
        )
    )
    print('All done!\n')