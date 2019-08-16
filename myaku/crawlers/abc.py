"""Crawler abstract base class and its supporting classes."""

import logging
import os
import time
from abc import ABC, abstractmethod
from random import random
from typing import Generator, List, NamedTuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import firefox

import myaku
import myaku.utils as utils
from myaku.database import MyakuCrawlDb
from myaku.datatypes import JpnArticle, JpnArticleMetadata

_log = logging.getLogger(__name__)

# Generator type for progressing a crawl one article at a time
CrawlGenerator = Generator[JpnArticle, None, None]


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

    @property
    @abstractmethod
    def _ARTICLE_METADATA_CMP_FIELDS(self) -> List[str]:
        """The JpnArticleMetadata fields to use for equivalence comparisons."""
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

    @abstractmethod
    def __init__(self, init_web_driver: bool, timeout: int = 10) -> None:
        """Initializes the resources used by the crawler.

        This method is abstract to force child classes to specify whether the
        web driver should be initialized for them or not.

        The web driver is expensive to initialize, so a child crawler should
        not have it initialized if it is not needed by it.

        Args:
            init_web_driver: If True, will initialize the selenium web driver
                as self._web_driver.
            timeout: The timeout to use on all web requests.
        """
        self._timeout = timeout
        self._session = requests.Session()

        self._web_driver = None
        if init_web_driver:
            self._init_web_driver()

    @utils.add_debug_logging
    def _init_web_driver(self) -> None:
        """Inits the web driver used by the crawler."""
        log_dir = utils.get_value_from_environment_variable(
            myaku.LOG_DIR_ENV_VAR, 'Log directory'
        )
        log_path = os.path.join(log_dir, self._WEB_DRIVER_LOG_FILENAME)

        options = firefox.options.Options()
        options.headless = True
        self._web_driver = webdriver.Firefox(
            options=options, log_path=log_path
        )

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
    def _crawl_uncrawled_metadatas(
        self, metadatas: List[JpnArticleMetadata]
    ) -> CrawlGenerator:
        """Crawls all not yet crawled articles specified by the metadatas.

        Args:
            metadatas: List of metadatas whose articles to crawl if not
                previous crawled.
        Returns:
            A generator that will yield a previously uncrawled JpnArticle from
            the given metadatas each call.
        """
        with MyakuCrawlDb() as db:
            uncrawled_metadatas = db.filter_to_unstored_article_metadatas(
                metadatas, self._ARTICLE_METADATA_CMP_FIELDS
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
                sleep_time = (random() * 4) + 3
                _log.debug(
                    'Sleeping for %s seconds, then scrape %s / %s',
                    sleep_time, i + 1, len(uncrawled_metadatas))
                time.sleep(sleep_time)

                article = self.crawl_article(metadata.source_url, metadata)
                db.write_crawled([article.metadata])

                yield article
