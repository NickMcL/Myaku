"""Crawler for the Kakuyomu website."""

import enum
import logging
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# import myaku.utils as utils
from myaku.crawlers.abc import Crawl, CrawlABC, CrawlGenerator
from myaku.datatypes import JpnArticle, JpnArticleBlog, JpnArticleMetadata

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

    _SOURCE_NAME = 'Kakuyomu'
    __SOURCE_BASE_URL = 'https://kakuyomu.jp'

    __ARTICLE_METADATA_CMP_FIELDS = []

    _SEARCH_PAGE_URL_TEMPLATE = (
        __SOURCE_BASE_URL +
        'search?genre_name={genre}&order={sort_order}&page={page_num}'
    )

    _EMPTY_SEARCH_RESULTS_CLASS = 'widget-emptyMessage'

    _SERIES_TITLE_LINK_CLASS = 'widget-workCard-titleLabel'

    @property
    def SOURCE_NAME(self) -> str:
        """Human-readable name for the source crawled."""
        return self._SOURCE_NAME

    @property
    def _SOURCE_BASE_URL(self) -> str:
        """The base url for accessing the source."""
        return self.__SOURCE_BASE_URL

    @property
    def _ARTICLE_METADATA_CMP_FIELDS(self) -> List[str]:
        """The JpnArticleMetadata fields to use for equivalence comparisons."""
        return self.__ARTICLE_METADATA_CMP_FIELDS

    def __init__(self, timeout: int = 10) -> None:
        """Initializes the resources used by the crawler."""
        super().__init__(False, timeout)

    def _create_search_url(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        page_num: int = 1
    ) -> str:
        """Creates a URL for making a search on the search page.

        Args:
            genre: Series genre to search for.
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
        return self._html_helper.descendant_with_class_exists(
            page_soup, '', self._EMPTY_SEARCH_RESULTS_CLASS
        )

    def _parse_search_results_page(
        self, page_soup: BeautifulSoup
    ) -> List[str]:
        """Parses the series links from a search results page soup.

        Args:
            page_soup: A BeautifulSoup initialized with the content from a
                search page.
        Returns:
            A list of the absolute urls for all of the series listed in the
            search results page.
        """
        series_link_tags = self._html_helper.parse_descendant_by_class(
            page_soup, '', self._SERIES_TITLE_LINK_CLASS, True
        )
        return [
            urljoin(self._SOURCE_BASE_URL, t['href']) for t in series_link_tags
        ]

    def _parse_series_blog_info(
        self, series_page_soup: BeautifulSoup, series_page_url: str
    ) -> JpnArticleBlog:
        """Parse the blog info for a series from its homepage.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_page_url: Url for the series page to parse.

        Returns:
            A JpnArticleBlog with the info from the given series homepage.
        """
        series_blog = JpnArticleBlog(
            title=self._html_helper.parse_text_from_desendant_by_id(
                series_page_soup, self._SERIES_TITLE_TAG_ID
            ),
            author=self._html_helper.parse_text_from_desendant_by_id(
                series_page_soup, self._SERIES_AUTHOR_TAG_ID
            ),
            source_name=self.SOURCE_NAME,
            source_url=series_page_url,
        )

        return series_blog

    def _parse_series_episode_metadatas(
        self, series_page_soup: BeautifulSoup, series_page_url: str
    ) -> List[JpnArticleMetadata]:
        """Parse the episode metadatas for a series from its homepage.

        Args:
            series_page_soup: A BeautifulSoup initialized with the content from
                a series homepage.
            series_page_url: Url for the series page to parse.

        Returns:
            A list of the metadatas for all episodes listed on the series
            homepage.
        """
        series_blog = self._parse_series_blog_info(
            series_page_soup, series_page_url
        )
        return series_blog

    def _crawl_series_page(self, page_url: str) -> CrawlGenerator:
        """Crawls a series homepage.

        Args:
            page_url: Url of the series homepage.

        Returns:
            A generator that will yield a JpnArticle for an episode of the
            series each call.
        """
        page_soup = self._get_url_html_soup(page_url)
        metadatas = self._parse_series_episode_metadatas(page_soup)
        yield from self._crawl_uncrawled_metadatas(metadatas)

    def _crawl_search_results_page(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        page_num: int = 1
    ) -> CrawlGenerator:
        """Crawls a single page of series search results.

        Args:
            genre: Series genre to search for.
            sort_order: Sort order to use for the search results.
            page_num: Page of the search results to crawl.
        Returns:
            A generator that will yield a JpnArticle for an episode of a series
            from the page of search results each call.
        """
        search_url = self._create_search_url(genre, sort_order, page_num)

        page_soup = self._get_url_html_soup(search_url)
        if self._is_empty_search_results_page(page_soup):
            _log.debug('No search results found for url "%s"', search_url)
            return

        series_links = self._parse_search_resuls_page(page_soup)
        for series_link in series_links:
            yield from self._crawl_series_page(series_link)

    def crawl_search_results(
        self, genre: KakuyomuGenre, sort_order: KakuyomuSortOrder,
        pages_to_crawl: int = 1, start_page: int = 1
    ) -> CrawlGenerator:
        """Makes a series search on Kakuyomu and then crawls the results.

        Args:
            genre: Series genre to search for.
            sort_order: Sort order to use for the search results.
            pages_to_crawl: How many pages of the search results to crawl. Each
                page has 20 results.

                Will automatically stop the crawl if a page with no search
                results is reached before crawling the specified number of
                pages.
            start_page: What page of the search results to start the crawl on.
        Returns:
            A generator that will yield a JpnArticle for an episode of a series
            from the search results each call.
        """
        for i in range(start_page, start_page + pages_to_crawl):
            _log.debug(
                'Crawling page %s of search results of genre %s with sort '
                'order %s', i, genre.name, sort_order.name
            )
            yield from self._crawl_search_results_page(genre, sort_order, i)

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent Kakuyomu articles.

        Only crawls for articles in the non-fiction and essay sections of
        Kakuyomu.
        """
        return []

    def crawl_article(self, article_url: str) -> JpnArticle:
        """Scrapes and parses an NHK News Web article.

        Args:
            url: url to a page containing an NHK News Web article.

        Returns:
            Article object with the parsed data from the article.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            CannotParsePageError: An error occurred while parsing the article.
        """
        pass
