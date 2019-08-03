"""Crawler abstract base class and its supporting classes."""

from abc import ABC, abstractmethod
from typing import Generator, List, NamedTuple

import myaku.utils as utils
from myaku.datatypes import JpnArticle


class Crawl(NamedTuple):
    """Data for a crawl run of a website for Japanese articles.

    Attributes:
        crawl_name: Name that should be displayed (etc. in logging) for the
            crawl.
        crawl_gen: Generator for progressing the crawl.
    """
    crawl_name: str
    crawl_gen: Generator[JpnArticle, None, None]


class CrawlerABC(ABC):
    """Base class for defining the components that make a Myaku crawler.

    A child class should handle the crawling for a single article source.
    """

    @property
    @abstractmethod
    def SOURCE_NAME(self) -> str:
        """The human-readable name of the source handled by the crawler."""
        return ""

    @abstractmethod
    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent articles from the source.

        The returned crawls should cover new articles from the source from the
        last 24 hours at minimum.
        """
        return []

    @abstractmethod
    def close(self) -> None:
        """Closes the resources used by the crawler."""
        pass

    @utils.add_debug_logging
    def __enter__(self) -> 'CrawlerABC':
        """Returns an initialized instance of the crawler."""
        return self

    @utils.add_debug_logging
    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Closes the resources used by the crawler."""
        self.close()
