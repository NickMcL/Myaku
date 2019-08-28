"""Crawler abstract base class and its supporting classes."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generator, List, Tuple

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import firefox

import myaku
from myaku import utils
from myaku.database import DbAccessMode, MyakuCrawlDb
from myaku.datatypes import Crawlable, JpnArticle, JpnArticleBlog

_log = logging.getLogger(__name__)

# Generator type for progressing a crawl one article at a time
CrawlGenerator = Generator[JpnArticle, None, None]

# Constants related to making HTTP requests while crawling
_REQUEST_MIN_WAIT_TIME = 1.5
_REQUSET_MAX_WAIT_TIME = 3
_REQUEST_MAX_RETRIES = 8


@dataclass
class Crawl(object):
    """Data for a crawl run of a website for Japanese articles.

    Attributes:
        source_name: Name of the source being crawled.
        crawl_name: Name of what is being crawled from the source.
        crawl_gen: Generator for progressing the crawl.
    """
    source_name: str
    crawl_name: str
    crawl_gen: CrawlGenerator

    def get_id(self) -> Tuple[str, str]:
        """Gets the unique id tuple for this crawl."""
        return (self.source_name, self.crawl_name)


class CrawlerABC(ABC):
    """Base class for defining the components that make a Myaku crawler.

    A child class should handle the crawling for a single article source.
    """

    # Must be overriden by child classes with their human-readable source name.
    SOURCE_NAME = 'MUST_OVERRIDE'

    # Must be overriden by child classes to make it True if the child class
    # makes use of the web driver. It is False by default so that resources are
    # not wasted initializing the web driver if it is not needed.
    _REQUIRES_WEB_DRIVER = False

    _WEB_DRIVER_LOG_FILENAME = 'webdriver.log'

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
        self, article_url: str, article_meta: JpnArticle
    ) -> JpnArticle:
        """Crawls a the article page for a single article from the source.

        Args:
            article_url: Url for the article page.
            article_meta: Article object prepopulated with metadata for the
                article from outside the article page.

        Returns:
            A JpnArticle with the data from the article page + the given
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
        self._session = requests.Session()
        self._web_driver = self._init_web_driver()

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
    def _get_url_json(self, url: str) -> Dict[str, Any]:
        """Makes a GET request to get JSON from a url.

        Args:
            url: Url to get the JSON from.

        Returns:
            A dict with the contents of the JSON from the url.

        Raises:
            HTTPError: The response for the GET request had a code >= 400.
            JSONDecodeError: The content at the given url was not valid JSON.
        """
        response = self._make_get_request(url)
        return response.json()

    @utils.add_debug_logging
    def _get_url_html_soup(
        self, url: str, raise_on_404: bool = True
    ) -> BeautifulSoup:
        """Makes a GET request and returns a BeautifulSoup of the contents.

        Args:
            url: Url to make the GET request to.
            raise_on_404: If True, will raise an HTTPError on a 404 status code
                in addition to all other status code >= 400.

                If False, will not raise on a 404 and will return None instead,
                but will still raise on all other status codes >= 400.

        Returns:
            A BeautifulSoup initialized to the content of the reponse for the
            request, or None if the response was a 404 and raise_on_404 is
            False.

        Raises:
            HTTPError: The response for the GET request had a code >= 400.
        """
        response = self._make_get_request(url, raise_on_404)
        if response is None:
            return None
        return BeautifulSoup(response.content, 'html.parser')

    @utils.rate_limit(_REQUEST_MIN_WAIT_TIME, _REQUSET_MAX_WAIT_TIME)
    @utils.retry_on_exception(
        _REQUEST_MAX_RETRIES, utils.REQUEST_RETRY_EXCEPTIONS
    )
    def _make_get_request(
        self, url: str, raise_on_404: bool = True
    ) -> requests.Response:
        """Makes a GET request to given url and returns the response.

        Args:
            url: Url to make the GET request to.
            raise_on_404: If True, will raise an HTTPError on a 404 status code
                in addition to all other status code >= 400.

                If False, will not raise on a 404 and will return None instead,
                but will still raise on all other status codes >= 400.

        Returns:
            The reponse for the request, or None if the response was a 404 and
            raise_on_404 is False.

        Raises:
            HTTPError: The response for the GET request had a code >= 400.
        """
        _log.debug('Making GET request to url "%s"', url)
        response = self._session.get(url, timeout=self._timeout)

        if not raise_on_404 and response.status_code == 404:
            _log.warning(
                'Response received with code 404 for url "%s", but no error '
                'will be raised', url
            )
            return None

        _log.debug('Response received with code %s', response.status_code)
        response.raise_for_status()
        return response

    def _prep_uncrawled_items_for_crawl(
        self, crawlable_items: List[Crawlable]
    ) -> List[Crawlable]:
        """Gets uncrawled items from the list and preps them for crawling.

        Args:
            crawlable_items: List of crawlable items.

        Returns:
            A new list with only the items from the given list that have not
            previously been crawled.
            Also updates the source_url of the returned items from a relative
            url to a fully-qualified url.
        """
        if len(crawlable_items) == 0:
            return []

        for item in crawlable_items:
            item.source_url = utils.join_suffix_to_url_base(
                self._SOURCE_BASE_URL, item.source_url
            )

        with MyakuCrawlDb(DbAccessMode.READ) as db:
            uncrawled_items = db.filter_crawlable_to_updated(crawlable_items)
        _log.debug(
            '%s found crawlable items of type %s have not been crawled',
            len(uncrawled_items), type(crawlable_items[0])
        )

        return uncrawled_items

    @utils.add_debug_logging
    def _crawl_uncrawled_articles(
        self, article_metas: List[JpnArticle]
    ) -> CrawlGenerator:
        """Crawls not yet crawled articles specified by the article metas.

        Args:
            article_metas: List of article metadatas whose articles to crawl if
                not previous crawled. Must have at least the source_url attr
                set.

        Returns:
            A generator that will yield a previously uncrawled JpnArticle from
            the given list of article metadatas each call.
        """
        uncrawled_metas = self._prep_uncrawled_items_for_crawl(article_metas)
        if len(uncrawled_metas) == 0:
            return

        with MyakuCrawlDb(DbAccessMode.READ_WRITE) as db:
            for i, meta in enumerate(uncrawled_metas):
                _log.debug(
                    'Crawling uncrawled artcile %s / %s',
                    i + 1, len(uncrawled_metas)
                )
                last_crawled_datetime = datetime.utcnow()
                article = self.crawl_article(meta.source_url, meta)
                if article is not None:
                    yield article

                meta.last_crawled_datetime = last_crawled_datetime
                db.update_last_crawled(meta)

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
        updated_blogs = self._prep_uncrawled_items_for_crawl(blogs)
        if len(updated_blogs) == 0:
            return

        with MyakuCrawlDb(DbAccessMode.READ_WRITE) as db:
            for i, blog in enumerate(updated_blogs):
                _log.debug(
                    'Crawling updated blog %s / %s', i + 1, len(updated_blogs)
                )
                blog.last_crawled_datetime = datetime.utcnow()
                yield from self.crawl_blog(blog.source_url)
                db.update_last_crawled(blog)
