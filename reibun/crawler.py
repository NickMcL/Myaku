"""Crawler classes for scraping text articles for the web."""

import functools
import logging
import time
from datetime import datetime
from random import random
from typing import Callable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium import webdriver
from selenium.webdriver import firefox

import reibun.utils as utils
from reibun.database import ReibunDb
from reibun.datatypes import JpnArticle, JpnArticleMetadata
from reibun.htmlhelper import HtmlHelper

_log = logging.getLogger(__name__)


class CannotAccessPageError(Exception):
    """A page went to by the crawler could not be accessed.

    This could be due to an HTTP error, but it could also be due to a website's
    url structure unexpectedly changing among other possible issues.
    """
    pass


class CannotParsePageError(Exception):
    """The crawler was unable to parse any article from a page.

    For example, if an article page uses a completely different different
    structure than what was expected by the crawler.
    """
    pass


@utils.add_method_debug_logging
class NhkNewsWebCrawler(object):
    """Crawls and scrapes articles from the NHK News Web website."""
    _SOURCE_NAME = 'NHK News Web'
    _SOURCE_BASE_URL = 'https://www3.nhk.or.jp'

    # If these article metadata fields are equivalent between two NHK News Web
    # article metadatas, the articles can be treated as equivalent
    _ARTICLE_METADATA_CMP_FIELDS = [
        'source_name',
        'title',
        'publication_datetime'
    ]

    _MOST_RECENT_PAGE_TITLE = '速報・新着ニュース一覧｜NHK NEWS WEB'
    _MOST_RECENT_PAGE_URL = 'https://www3.nhk.or.jp/news/catnew.html'
    _MOST_RECENT_PAGE_TITLE_CLASS = 'title'
    _MOST_RECENT_PAGE_MAIN_ID = 'main'
    _MOST_RECENT_PAGE_ARTICLE_LIST_CLASSES = [
        'content--list',
        'grid--col-single'
    ]

    _ARTICLE_TAG_CLASS = 'detail-no-js'
    _ARTICLE_TITLE_CLASS = 'contentTitle'

    _ARTICLE_BODY_IDS = [
        'news_textbody',
        'news_textmore',
    ]
    _ARTICLE_BODY_CLASSES = [
        'news_add',
    ]

    def __init__(self, timeout: int = 10) -> None:
        """Initializes the resources used by the crawler."""
        self._web_driver = None
        self._session = requests.Session()
        self._timeout = timeout

        self._parsing_error_handler = functools.partial(
            utils.log_and_raise, _log, CannotParsePageError
        )
        self._html_helper = HtmlHelper(self._parsing_error_handler)

        self._init_web_driver()

    def _init_web_driver(self) -> None:
        """Inits the web driver used by the crawler."""
        options = firefox.options.Options()
        options.headless = True
        self._web_driver = webdriver.Firefox(options=options)

    def close(self) -> None:
        """Closes the resources used by the crawler."""
        if self._web_driver:
            self._web_driver.close()
        if self._session:
            self._session.close()

    def __enter__(self) -> 'NhkNewsWebCrawler':
        """Returns an initialized instance of the crawler."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Closes the resources used by the crawler."""
        self.close()

    def _parse_body_div(self, tag: Tag) -> Optional[str]:
        """Parses the body text from a division of an NHK article.

        Args:
            tag: Tag containing a division of an NHK article.

        Returns:
            The parsed body text from tag.

        Raises:
            CannotParsePageError: There was an error parsing the body text from
                tag.
        """
        section_text = self._html_helper.parse_valid_child_text(tag)
        if section_text is not None:
            return section_text

        text_sections = []
        for child in tag.children:
            # Skip text around child tags such as '\n'
            if child.name is None:
                continue

            child_text = self._html_helper.parse_valid_child_text(child)
            if child_text is None:
                _log.debug(
                    'Unable to determine body text from tag: "%s"', child
                )
                continue

            if len(child_text) > 0:
                text_sections.append(child_text)

        return '\n'.join(text_sections) if len(text_sections) > 0 else None

    def _parse_body_text(self, article_tag: Tag) -> Optional[str]:
        """Parses the body text from NHK article HTML.

        Args:
            article_tag: Tag containing NHK article HTML.

        Returns:
            The parsed body text from article_tag.

        Raises:
            CannotParsePageError: There was an error parsing the body text.
        """
        body_tags = []
        for id_ in self._ARTICLE_BODY_IDS:
            divs = article_tag.find_all('div', id=id_)
            _log.debug('Found %s with id "%s"', len(divs), id_)
            body_tags += divs

        for class_ in self._ARTICLE_BODY_CLASSES:
            divs = article_tag.find_all('div', class_=class_)
            _log.debug('Found %s with class "%s"', len(divs), class_)
            body_tags += divs

        body_text_sections = []
        for tag in body_tags:
            text = self._parse_body_div(tag)
            if text is not None and len(text) > 0:
                body_text_sections.append(text)

        if len(body_text_sections) == 0:
            self._parsing_error_handler(
                'No body text sections in: "{}"'.format(article_tag)
            )

        return '\n\n'.join(body_text_sections)

    def _parse_article(
        self, article_tag: Tag, url: str
    ) -> JpnArticle:
        """Parses data from NHK article HTML.

        Args:
            article_tag: Tag containing NHK article HTML.
            url: url where article_tag was found.

        Returns:
            Article object containing the parsed data from article_tag.
        """
        article_data = JpnArticle()
        article_data.metadata = JpnArticleMetadata(
            title=self._html_helper.parse_text_from_desendant(
                article_tag, 'span', self._ARTICLE_TITLE_CLASS
            ),
            source_url=url,
            source_name=self._SOURCE_NAME,
            scraped_datetime=datetime.utcnow(),
            publication_datetime=self._html_helper.parse_jst_time_desendant(
                article_tag
            ),
        )

        body_text = self._parse_body_text(article_tag)
        article_data.full_text = '{}\n\n{}'.format(
            article_data.metadata.title, body_text
        )

        return article_data

    def _parse_main(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Parses the main tag from the given BeautifulSoup html.

        Args:
            soup: BeautifulSoup object with parsed html.

        Returns:
            main tag if successfully parsed, None if otherwise.
        """
        main = soup.find(id=self._MOST_RECENT_PAGE_MAIN_ID)
        if main is None:
            self._parsing_error_handler(
                'Could not find "main" tag in most recent page ({})'.format(
                    self._MOST_RECENT_PAGE_URL
                )
            )

        return main

    def _parse_most_recent_article_list(self, main: Tag) -> Optional[Tag]:
        """Parses the most recent article list ul tag from the main tag.

        Args:
            main: A main tag that should contain a most recent article list.

        Returns:
            Most recent article list ul tag if successfully parsed, None if
            otherwise.
        """
        article_uls = main.find_all(
            'ul', class_=self._MOST_RECENT_PAGE_ARTICLE_LIST_CLASSES
        )
        if len(article_uls) != 1:
            self._parsing_error_handler(
                'Found {} article uls instead of 1 in most recent page '
                '({})'.format(
                    len(article_uls), self._MOST_RECENT_PAGE_URL
                )
            )

        return article_uls[0]

    def _scrape_most_recent_article_metadatas(
        self
    ) -> List[JpnArticleMetadata]:
        """Scrapes all article metadata from the 'Most Recent' page."""
        self._web_driver.get(self._MOST_RECENT_PAGE_URL)
        if self._web_driver.title != self._MOST_RECENT_PAGE_TITLE:
            utils.log_and_raise(
                _log, CannotAccessPageError,
                'Most recent page title ({}) at url ({}) does not match '
                'expected title ({})'.format(
                    self._web_driver.title, self._MOST_RECENT_PAGE_URL,
                    self._MOST_RECENT_PAGE_TITLE
                )
            )

        soup = BeautifulSoup(self._web_driver.page_source, 'html.parser')
        main = self._parse_main(soup)
        article_ul = self._parse_most_recent_article_list(main)

        metadatas = []
        for list_item in article_ul.children:
            metadatas.append(JpnArticleMetadata(
                title=self._html_helper.parse_text_from_desendant(
                    list_item, 'em', self._MOST_RECENT_PAGE_TITLE_CLASS
                ),
                publication_datetime=(
                    self._html_helper.parse_jst_time_desendant(list_item)
                ),
                source_url=self._html_helper.parse_link_desendant(list_item),
                source_name=self._SOURCE_NAME,
            ))

        return metadatas

    def _make_rel_urls_absolute(self, urls: List[str]) -> List[str]:
        """Makes metadata relative NHK News Web urls absolute urls."""
        absolute_urls = []
        for url in urls:
            absolute_urls.append(urljoin(
                self._SOURCE_BASE_URL, urlparse(url).path
            ))
        return absolute_urls

    def crawl_most_recent(self) -> List[JpnArticle]:
        """Gets all not yet crawled articles from the 'Most Recent' page."""
        metadatas = self._scrape_most_recent_article_metadatas()
        _log.debug('Found %s metadatas from most recent page', len(metadatas))

        with ReibunDb() as db:
            uncrawled_metadatas = db.filter_to_unstored_article_metadatas(
                metadatas, self._ARTICLE_METADATA_CMP_FIELDS
            )
        _log.debug(
            '%s found metadatas have not been crawled',
            len(uncrawled_metadatas)
        )
        if len(uncrawled_metadatas) == 0:
            return []

        crawl_urls = [m.source_url for m in uncrawled_metadatas]
        crawl_urls = self._make_rel_urls_absolute(crawl_urls)
        articles = []
        with ReibunDb() as db:
            for crawl_url in crawl_urls:
                sleep_time = (random() * 4) + 2
                _log.debug('Sleeping for %s seconds', sleep_time)
                time.sleep(sleep_time)

                articles.append(self.scrape_article(crawl_url))
                db.write_crawled([articles[-1].metadata])

        return articles

    def scrape_article(self, url: str) -> JpnArticle:
        """Scrapes and parses an NHK News Web article.

        Args:
            url: url to a page containing an NHK News Web article.

        Returns:
            Article object with the parsed data from the article.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            CannotParsePageError: An error occurred while parsing the article.
        """
        _log.debug('Making GET request to url "%s"', url)
        response = self._session.get(url, timeout=self._timeout)
        _log.debug('Reponse received with code %s', response.status_code)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        article_tags = soup.find_all(
            'section', class_=self._ARTICLE_TAG_CLASS
        )
        if len(article_tags) != 1:
            self._parsing_error_handler(
                'Found %s article sections instead of 1 for url "%s"',
                len(article_tags), url
            )

        # Ruby tags tend to mess up Japanese processing, so strip all of them
        # from the HTML document right away.
        article_tag = self._html_helper.remove_ruby_tags(article_tags[0])

        return self._parse_article(article_tag, url)
