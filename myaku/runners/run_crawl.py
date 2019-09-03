"""Scripts for running Myaku crawls.

Usage: run_crawl.py <crawler_list>

<crawler_list>: A comma-separated list of the crawlers whose most recent crawls
    to run. Possible values are listed in VALID_CRAWLER_NAMES.
"""

import abc
import logging
import math
import sys
import time
from dataclasses import dataclass
from typing import List

import myaku.crawlers
from myaku import utils
from myaku.crawlers.abc import Crawl
from myaku.datastore import DataAccessMode
from myaku.datastore.database import CrawlDb
from myaku.datatypes import JpnArticle, FoundJpnLexicalItem
from myaku.errors import ScriptArgsError
from myaku.japanese_analysis import JapaneseTextAnalyzer
from myaku.scorer import MyakuArticleScorer

_log = logging.getLogger(__name__)

LOG_NAME = 'crawl'

# Valid crawlers for the list of crawlers given to this script
VALID_CRAWLER_NAMES = {
    'Asahi',
    'Kakuyomu',
    'NhkNewsWeb',
}

CRAWLER_ARG_LIST_SPLITTER = ','


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
        self._source_counts = {}
        self._source_start_times = {}
        self._overall_counts = CrawlCounts()
        self._overall_start_time = None

        if start_now:
            self.start_stat_tracking()

    def start_stat_tracking(self) -> None:
        """Starts stat tracking."""
        self._overall_start_time = time.perf_counter()

    def add_crawl_source(self, source_name: str) -> None:
        """Adds crawl source whose stats to track."""
        _log.info('\nCrawling %s\n', source_name)
        self._source_counts[source_name] = CrawlCounts()
        self._source_start_times[source_name] = time.perf_counter()

    def add_crawl(self, crawl: Crawl) -> None:
        """Adds crawl whose stats to track."""
        _log.info(
            '\nCrawling %s from %s\n', crawl.crawl_name, crawl.source_name
        )
        self._crawl_counts[crawl.get_id()] = CrawlCounts()
        self._crawl_start_times[crawl.get_id()] = time.perf_counter()

    def update_crawl(
        self, crawl: Crawl, article: JpnArticle,
        flis: List[FoundJpnLexicalItem]
    ) -> None:
        """Updates a crawl stats with given found article and lexical items."""
        _log.info('Found %s lexical items in %s', len(flis), article)
        counts = CrawlCounts.from_article(article, flis)
        self._crawl_counts[crawl.get_id()] += counts
        self._source_counts[crawl.source_name] += counts
        self._overall_counts += counts

    def finish_crawl(self, crawl: Crawl) -> None:
        """Mark crawl as finished and log its final stats."""
        run_secs = (
            time.perf_counter() - self._crawl_start_times[crawl.get_id()]
        )
        counts = self._crawl_counts[crawl.get_id()]
        self._log_stats(
            '{} from {} crawl'.format(crawl.crawl_name, crawl.source_name),
            counts, run_secs
        )

    def finish_crawl_source(self, source_name: str) -> None:
        """Mark crawl source as finished and log its final stats."""
        run_secs = time.perf_counter() - self._source_start_times[source_name]
        counts = self._source_counts[source_name]
        self._log_stats('{} crawl'.format(source_name), counts, run_secs)

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


def parse_crawler_types_arg() -> List[abc.ABCMeta]:
    """Parses the crawler types from the argument given to this script."""
    if len(sys.argv) != 2:
        raise ScriptArgsError(
            'run_crawl.py script given {} args instead of 2: {}'.format(
                len(sys.argv), sys.argv
            )
        )

    crawler_types = []
    crawler_args = sys.argv[1].split(CRAWLER_ARG_LIST_SPLITTER)
    for crawler_arg in crawler_args:
        crawler_name = crawler_arg.strip()
        if crawler_name not in VALID_CRAWLER_NAMES:
            raise ScriptArgsError(
                '"{}" is not a valid crawler name. Valid crawler names are: '
                '{}'.format(crawler_name, VALID_CRAWLER_NAMES)
            )
        crawler_types.append(getattr(myaku.crawlers, crawler_name + 'Crawler'))

    return crawler_types


def crawl_most_recent(
    crawler_type: abc.ABCMeta, jta: JapaneseTextAnalyzer,
    scorer: MyakuArticleScorer, stats: CrawlStats
) -> None:
    """Runs the most recent articles crawl for the given crawler type."""
    read_write_access = DataAccessMode.READ_WRITE
    with CrawlDb(read_write_access, True) as db, crawler_type() as crawler:
        stats.add_crawl_source(crawler.SOURCE_NAME)
        crawls = crawler.get_crawls_for_most_recent()
        for crawl in crawls:
            stats.add_crawl(crawl)

            for article in crawl.crawl_gen:
                # Don't waste time running Japanese analysis on articles that
                # can't be stored in the crawl db anyway.
                if not db.can_store_article(article):
                    continue

                flis = jta.find_article_lexical_items(article)
                scorer.score_article(article)
                for fli in flis:
                    scorer.score_fli_modifier(fli)

                db.write_found_lexical_items(flis)
                stats.update_crawl(crawl, article, flis)

            stats.finish_crawl(crawl)
        stats.finish_crawl_source(crawler.SOURCE_NAME)


def main() -> None:
    """Runs a full crawl of the top NHK News Web pages."""
    utils.toggle_myaku_package_log(filename_base=LOG_NAME)
    stats = CrawlStats()
    jta = JapaneseTextAnalyzer()
    scorer = MyakuArticleScorer()

    crawler_types = parse_crawler_types_arg()
    for crawler_type in crawler_types:
        crawl_most_recent(crawler_type, jta, scorer, stats)
    stats.finish_stat_tracking()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.run_crawl')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
