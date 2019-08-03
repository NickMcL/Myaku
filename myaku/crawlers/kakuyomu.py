"""Crawler for the Kakuyomu website."""

import enum
import functools
import logging
from typing import Generator, List

from bs4 import BeautifulSoup
import requests

import myaku.utils as utils
from myaku.crawlers.abc import Crawl, CrawlABC
from myaku.datatypes import JpnArticle
from myaku.errors import CannotParsePageError
from myaku.htmlhelper import HtmlHelper

_log = logging.getLogger(__name__)


@enum.unique
class KakuyomuGenre(enum.Enum):
    """The genre categories used by Kakuyomu.

    Kakuyomu has several more genres available than those in this enum, but
    this enum only covers the categories crawled by the KakuyomuCrawler.

    Attributes:
        NONFICTION: Non-fiction articles about any topic.
        CRITICISM: Articles related to criticism of written works.
    """
    NONFICTION = 1
    CRITICISM = 2


@enum.unique
class KakuyomuSortOrder(enum.Enum):
    """The series sort orders available on Kakuyomu.

    Attributes:
        POPULAR: Sorts from most popular series to least popular.
        PUBLISHED_AT: Sorts from most recently started series to oldest started
            series.
        LAST_EPISODE_PUBLISHED_AT: Sorts from most recently updated series to
            least recently updated series.
    """
    POPULAR = 1
    PUBLISHED_AT = 2
    LAST_EPISODE_PUBLISHED_AT = 3


class KakuyomuCrawler(CrawlABC):
    """Crawls articles from the Kakuyomu website.

    Only crawls for articles in the non-fiction and essay sections of Kakuyomu.
    """

    _SOURCE_BASE_URL = 'https://kakuyomu.jp'
    _SEARCH_PAGE_URL_TEMPLATE = (
        _SOURCE_BASE_URL +
        'search?genre_name={genre}&order={sort_order}&page={page_num}'
    )

    _EMPTY_SEARCH_RESULTS_TAG_CLASS = 'widget-emptyMessage'

    @property
    def SOURCE_NAME(self) -> str:
        """Human-readable name for the source crawled."""
        return "Kakuyomu"

    def __init__(self, timeout: int = 10) -> None:
        """Initializes the resources used by the crawler."""
        self._session = requests.Session()
        self._timeout = timeout

        self._parsing_error_handler = functools.partial(
            utils.log_and_raise, _log, CannotParsePageError
        )
        self._html_helper = HtmlHelper(self._parsing_error_handler)

        self._init_web_driver()

    def close(self) -> None:
        """Closes the resources used by the crawler."""
        if self._session:
            self._session.close()

    def _create_search_url(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        page_num: int = 1
    ) -> str:
        """Creates a URL for making a search on the search page.

        Args:
            genre: Genere to search for.
            sort_order: Sort order to use for the search results.
            page_num: Page of the search results.
        """
        return self._SEARCH_PAGE_URL_TEMPLATE.format(
            genre=genre.name.lower(),
            sort_order=sort_order.name.lower(),
            page_num=page_num
        )

    def _is_empty_search_results_page(self, page_soup: BeautifulSoup) -> bool:
        """Returns True if the page is the empty search results page."""
        empty_search_results_tag = page_soup.find(
            class_=self._EMPTY_SEARCH_RESULTS_TAG_CLASS
        )
        if empty_search_results_tag is None:
            return False
        return True

    def crawl_search_page(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        pages_to_crawl: int = 1
    ) -> Generator[JpnArticle, None, None]:
        """Makes a search on the search page and then crawls the results.

        Args:
            genre: Genere to search for.
            sort_order: Sort order to use for the search results.
            pages_to_crawl: How many pages of the search results to crawl. Each
                page has 20 results.

                Will automatically stop the crawl if all search results have
                been crawled before crawling the specified number of pages.
        """
        for i in range(1, pages_to_crawl + 1):
            _log.debug(
                'Crawling page %s of search results of genere %s with sort '
                'order %s', i, genre.name, sort_order.name
            )
            search_url = self._create_search_url(genre, sort_order, i)

            _log.debug('Making GET request to url "%s"', search_url)
            response = self._session.get(search_url, timeout=self._timeout)
            _log.debug('Reponse received with code %s', response.status_code)
            response.raise_for_status()

            page_soup = BeautifulSoup(response.content, 'html.parser')
            if self._is_empty_search_results_page(page_soup):
                _log.debug('No search results found for url "%s"', search_url)
                return 'All search results crawled'

            series_links = self._parse_search_resuls(page_soup)
            for series_link in series_links:
                yield self._crawl_series_page(series_link)

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent Kakuyomu articles.

        Only crawls for articles in the non-fiction and essay sections of
        Kakuyomu.
        """
        return []
