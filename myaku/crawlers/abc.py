"""Crawler abstract base class and its supporting classes."""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generator, List, NamedTuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver import firefox

import myaku
import myaku.utils as utils
from myaku.database import MyakuCrawlDb
from myaku.datatypes import JpnArticle, JpnArticleBlog, JpnArticleMetadata

_log = logging.getLogger(__name__)

# Generator type for progressing a crawl one article at a time
CrawlGenerator = Generator[JpnArticle, None, None]

# Constants related to making HTTP requests while crawling
_REQUEST_MIN_WAIT_TIME = 1.5
_REQUSET_MAX_WAIT_TIME = 3
_REQUEST_MAX_RETRIES = 6
_REQUEST_RETRY_BACKOFF_FACTOR = 2
_REQUEST_RETRY_ERROR_CODES = (500, 502, 503, 504, 520, 522, 524)


class Crawl(NamedTuple):
    """Data for a crawl run of a website for Japanese articles.

    Attributes:
        crawl_name: Name that should be displayed (etc. in logging) for the
            crawl.
        crawl_gen: Generator for progressing the crawl.
    """
    crawl_name: str
    crawl_gen: CrawlGenerator


class CrawlerABC(ABC):
    """Base class for defining the components that make a Myaku crawler.

    A child class should handle the crawling for a single article source.
    """

    # This must be overriden by child classes to make it True if the child
    # class makes use of the web driver. It is False by default so that
    # resources are not wasted initializing the web driver if it is not needed.
    _REQUIRES_WEB_DRIVER = False

    _WEB_DRIVER_LOG_FILENAME = 'webdriver.log'

    @property
    @abstractmethod
    def SOURCE_NAME(self) -> str:
        """The human-readable name of the source handled by the crawler."""
        return ""

    @property
    @abstractmethod
    def _SOURCE_BASE_URL(self) -> List[str]:
        """The base url for accessing the source."""
        return []

    @abstractmethod
    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent articles from the source.

        The returned crawls should cover new articles from the source from the
        last 24 hours at minimum.
        """
        return []

    @abstractmethod
    def crawl_article(
        self, article_url: str, article_metadata: JpnArticleMetadata
    ) -> JpnArticle:
        """Crawls a single article from the source.

        Args:
            article_url: Url for the article.
            article_metadata: Metadata for the article from outside the article
                page.

        Returns:
            A JpnArticle with the data from the crawled article + the given
            metadata.
        """
        return JpnArticle()

    @utils.add_debug_logging
    def __init__(self, timeout: int = 30) -> None:
        """Initializes the resources used by the crawler.

        Args:
            timeout: The timeout to use on all web requests.
        """
        self._timeout = timeout
        self._session = self._init_requests_session()
        self._web_driver = self._init_web_driver()

    @utils.add_debug_logging
    def _init_requests_session(self) -> requests.Session:
        """Inits the requests session for the crawler."""
        session = requests.Session()
        retry = Retry(
            total=_REQUEST_MAX_RETRIES,
            backoff_factor=_REQUEST_RETRY_BACKOFF_FACTOR,
            status_forcelist=_REQUEST_RETRY_ERROR_CODES,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    @utils.add_debug_logging
    def _init_web_driver(self) -> webdriver.Firefox:
        """Inits the web driver for the crawler."""
        if not self._REQUIRES_WEB_DRIVER:
            return None

        log_dir = utils.get_value_from_env_variable(myaku.LOG_DIR_ENV_VAR)
        log_path = os.path.join(log_dir, self._WEB_DRIVER_LOG_FILENAME)

        options = firefox.options.Options()
        options.headless = True
        return webdriver.Firefox(options=options, log_path=log_path)

    @utils.add_debug_logging
    def close(self) -> None:
        """Closes the resources used by the crawler."""
        if self._session:
            self._session.close()
        if self._web_driver:
            self._web_driver.close()

    @utils.add_debug_logging
    def __enter__(self) -> 'CrawlerABC':
        """Returns an initialized instance of the crawler."""
        return self

    @utils.add_debug_logging
    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Closes the resources used by the crawler."""
        self.close()

    @utils.add_debug_logging
    @utils.rate_limit(_REQUEST_MIN_WAIT_TIME, _REQUSET_MAX_WAIT_TIME)
    def _get_url_html_soup(self, url: str) -> BeautifulSoup:
        """Makes a GET request and returns a BeautifulSoup of the contents.

        Args:
            url: Url to make the GET request to.

        Returns:
            A BeautifulSoup initialized to the content of the reponse for the
            request.

        Raises:
            HTTPError: The response for the GET request had a code >= 400.
        """
        _log.debug('Making GET request to url "%s"', url)
        response = self._session.get(url, timeout=self._timeout)
        _log.debug('Response received with code %s', response.status_code)
        response.raise_for_status()

        return BeautifulSoup(response.content, 'html.parser')

    @utils.add_debug_logging
    def _crawl_uncrawled_articles(
        self, metadatas: List[JpnArticleMetadata]
    ) -> CrawlGenerator:
        """Crawls not yet crawled articles specified by the metadatas.

        Args:
            metadatas: List of metadatas whose articles to crawl if not
                previous crawled.

        Returns:
            A generator that will yield a previously uncrawled JpnArticle from
            the given metadatas each call.
        """
        with MyakuCrawlDb() as db:
            uncrawled_metadatas = db.filter_to_uncrawled_article_metadatas(
                metadatas
            )

        _log.debug(
            '%s found metadatas have not been crawled',
            len(uncrawled_metadatas)
        )
        if len(uncrawled_metadatas) == 0:
            return

        for metadata in uncrawled_metadatas:
            metadata.source_url = (
                urljoin(self._SOURCE_BASE_URL, metadata.source_url)
            )

        with MyakuCrawlDb() as db:
            for i, metadata in enumerate(uncrawled_metadatas):
                _log.debug(
                    'Crawling uncrawled artcile %s / %s',
                    i + 1, len(uncrawled_metadatas)
                )
                article = self.crawl_article(metadata.source_url, metadata)
                db.write_crawled([article.metadata])

                yield article

    @utils.add_debug_logging
    def _crawl_updated_blogs(
        self, blogs: List[JpnArticleBlog]
    ) -> CrawlGenerator:
        """Crawls the blogs that have been updated since last crawled.

        Args:
            blogs: List of blogs to check. The blogs that have been updated
                since last crawled will be crawled.

        Returns:
            A generator that will yield a previously uncrawled JpnArticle from
            one of the updated blogs each call.
        """
        with MyakuCrawlDb() as db:
            updated_blogs = db.filter_to_updated_blogs(blogs)

        _log.debug(
            '%s found blogs have been updated since last crawled',
            len(updated_blogs)
        )
        if len(updated_blogs) == 0:
            return

        for blog in updated_blogs:
            blog.source_url = (
                urljoin(self._SOURCE_BASE_URL, blog.source_url)
            )

        with MyakuCrawlDb() as db:
            for i, blog in enumerate(updated_blogs):
                _log.debug(
                    'Crawling updated blog %s / %s',
                    i + 1, len(updated_blogs)
                )

                blog.last_crawled_datetime = datetime.utcnow()
                yield from self.crawl_blog(blog.source_url)
                db.update_blog_last_crawled(blog)
