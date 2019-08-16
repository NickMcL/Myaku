import logging
import math
import time
from dataclasses import dataclass
from typing import List

import myaku.utils as utils
from myaku.crawlers import KakuyomuCrawler
from myaku.database import MyakuCrawlDb
from myaku.datatypes import JpnArticle, FoundJpnLexicalItem
from myaku.japanese_analysis import JapaneseTextAnalyzer

LOG_NAME = 'crawl'

_log = logging.getLogger(__name__)


@dataclass
class CrawlCounts(object):
    """Counts related to a web crawl."""
    article_count: int = 0
    character_count: int = 0
    fli_count: int = 0

    def __iadd__(self, other) -> 'CrawlCounts':
        if not isinstance(other, CrawlCounts):
            raise TypeError(f'Can not add type {type(other)} to CrawlCounts')

        self.article_count += other.article_count
        self.character_count += other.character_count
        self.fli_count += other.fli_count
        return self

    @classmethod
    def from_article(
        cls, article: JpnArticle, flis: List[FoundJpnLexicalItem]
    ) -> 'CrawlCounts':
        """Creates counts for single article with given found lexical items."""
        return cls(1, article.alnum_count, len(flis))


class CrawlStats(object):
    """Keeps track of stats for web crawls."""

    def __init__(self, start_now: bool = True) -> None:
        """Inits stat tracking vars."""
        self._crawl_counts = {}
        self._crawl_start_times = {}
        self._overall_counts = CrawlCounts()
        self._overall_start_time = None

        if start_now:
            self.start_stat_tracking()

    def start_stat_tracking(self) -> None:
        """Starts stat tracking."""
        self._overall_start_time = time.perf_counter()

    def add_crawl(self, name: str) -> None:
        """Adds crawl whose stats to track."""
        _log.info('\nCrawling %s\n', name)
        self._crawl_counts[name] = CrawlCounts()
        self._crawl_start_times[name] = time.perf_counter()

    def update_crawl(
        self, name: str, article: JpnArticle, flis: List[FoundJpnLexicalItem]
    ) -> None:
        """Updates a crawl stats with given found article and lexical items."""
        _log.info('Found %s lexical items in %s', len(flis), article)
        counts = CrawlCounts.from_article(article, flis)
        self._crawl_counts[name] += counts
        self._overall_counts += counts

    def finish_crawl(self, name: str) -> None:
        """Mark crawl as finished and log its final stats."""
        run_secs = time.perf_counter() - self._crawl_start_times[name]
        counts = self._crawl_counts[name]
        self._log_stats(name + ' crawl', counts, run_secs)

    def finish_stat_tracking(self) -> None:
        """Finializes and prints overall stats."""
        run_secs = time.perf_counter() - self._overall_start_time
        self._log_stats('Overall', self._overall_counts, run_secs)

    def _log_stats(
        self, name: str, counts: CrawlCounts, run_secs: float
    ) -> None:
        """Logs the given stats in an easily readable format."""
        str_list = []
        str_list.append(f'{name} stats')
        str_list.append('-' * len(str_list[-1]))
        str_list.append(f'Articles crawled: {counts.article_count:,}')
        str_list.append(f'Characters analyzed: {counts.character_count:,}')
        str_list.append(f'Found lexical items: {counts.fli_count:,}')
        str_list.append(
            'Run time: {:,} minutes, {} seconds'.format(
                math.floor(run_secs / 60), round(run_secs % 60)
            )
        )
        _log.info('\n%s\n', '\n'.join(str_list))


def main() -> None:
    """Runs a full crawl of the top NHK News Web pages."""
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)

    stats = CrawlStats()
    jta = JapaneseTextAnalyzer()
    with MyakuCrawlDb() as db, KakuyomuCrawler() as crawler:
        crawls = crawler.get_crawls_for_most_recent()

        for crawl in crawls:
            stats.add_crawl(crawl.crawl_name)

            for article in crawl.crawl_gen:
                if db.is_article_stored(article):
                    _log.info('Article %s already stored!', article)
                    continue

                flis = jta.find_article_lexical_items(article)
                db.write_found_lexical_items(flis)
                stats.update_crawl(crawl.crawl_name, article, flis)

            stats.finish_crawl(crawl.crawl_name)
        stats.finish_stat_tracking()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.run_crawl')
    main()
