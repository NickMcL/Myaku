"""Crawler classes for scraping text articles for the web."""

import functools
import logging
import time
from datetime import datetime
from random import random
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import firefox
from selenium.webdriver.firefox.webelement import FirefoxWebElement

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

    _MAIN_ID = 'main'
    _TITLE_CLASS = 'title'

    _SHOW_MORE_BUTTON_CLASS = 'button'
    _SHOW_MORE_BUTTON_FOOTER_CLASS = 'button-more'
    _LOADING_CLASS_NAME = 'loading'

    _TOKUSHU_PAGE_TITLE = '特集一覧｜NHK NEWS WEB'
    _TOKUSHU_PAGE_URL = 'https://www3.nhk.or.jp/news/tokushu/'
    _TOKUSHU_HEADER_DIV_CLASS = 'content--header'
    _TOKUSHU_ARTICLE_LIST_CLASSES = [
        'content--list',
        'grid--col-operation'
    ]

    _MOST_RECENT_PAGE_TITLE = '速報・新着ニュース一覧｜NHK NEWS WEB'
    _MOST_RECENT_PAGE_URL = 'https://www3.nhk.or.jp/news/catnew.html'
    _MOST_RECENT_ARTICLE_LIST_CLASSES = [
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

    @utils.skip_method_debug_logging
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
        main = soup.find(id=self._MAIN_ID)
        if main is None:
            self._parsing_error_handler(
                'Could not find "main" tag in page "{}"'.format(soup)
            )

        return main

    def _scrape_most_recent_article_metadatas(
        self, page_soup: BeautifulSoup
    ) -> List[JpnArticleMetadata]:
        """Scrapes all article metadata from the 'Most Recent' page soup."""
        main = self._parse_main(page_soup)
        article_ul = self._html_helper.parse_descendant_by_class(
            main, 'ul', self._MOST_RECENT_ARTICLE_LIST_CLASSES
        )

        metadatas = []
        for list_item in article_ul.children:
            metadatas.append(JpnArticleMetadata(
                title=self._html_helper.parse_text_from_desendant(
                    list_item, 'em', self._TITLE_CLASS
                ),
                publication_datetime=(
                    self._html_helper.parse_jst_time_desendant(list_item)
                ),
                source_url=self._html_helper.parse_link_desendant(list_item),
                source_name=self._SOURCE_NAME,
            ))

        return metadatas

    def _scrape_tokushu_article_metadatas(
        self, page_soup: BeautifulSoup
    ) -> List[JpnArticleMetadata]:
        """Scrapes all article metadata from the 'Tokushu' page soup."""
        main = self._parse_main(page_soup)
        header_divs = self._html_helper.parse_descendant_by_class(
            main, 'div', self._TOKUSHU_HEADER_DIV_CLASS, True
        )
        _log.debug('Found %s header divs', len(header_divs))
        article_ul = self._html_helper.parse_descendant_by_class(
            main, 'ul', self._TOKUSHU_ARTICLE_LIST_CLASSES
        )
        article_metadata_tags = header_divs + article_ul.contents
        _log.debug(
            'Found %s article metadata tags', len(article_metadata_tags)
        )

        metadatas = []
        for tag in article_metadata_tags:
            metadatas.append(JpnArticleMetadata(
                title=self._html_helper.parse_text_from_desendant(
                    tag, 'em', self._TITLE_CLASS
                ),
                publication_datetime=(
                    self._html_helper.parse_jst_time_desendant(tag)
                ),
                source_url=self._html_helper.parse_link_desendant(tag, True),
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

    def _crawl_uncrawled_metadatas(
        self, metadatas: List[JpnArticleMetadata]
    ) -> List[JpnArticle]:
        """Crawls all not yet crawled articles specified by the metadatas."""
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
            for i, crawl_url in enumerate(crawl_urls):
                sleep_time = (random() * 4) + 3
                _log.debug(
                    'Sleeping for %s seconds, then scrape %s / %s',
                    sleep_time, i + 1, len(crawl_urls))
                time.sleep(sleep_time)

                articles.append(self.scrape_article(crawl_url))
                db.write_crawled([articles[-1].metadata])

        return articles

    def crawl_most_recent(self) -> List[JpnArticle]:
        """Gets all not yet crawled articles from the 'Most Recent' page."""
        self._web_driver.get(self._MOST_RECENT_PAGE_URL)
        if self._web_driver.title != self._MOST_RECENT_PAGE_TITLE:
            utils.log_and_raise(
                _log, CannotAccessPageError,
                'Most recent page title ({}) at url ({}) does not match '
                'expected title ({})'.format(
                    self._web_driver.title, self._web_driver.current_url,
                    self._MOST_RECENT_PAGE_TITLE
                )
            )

        soup = BeautifulSoup(self._web_driver.page_source, 'html.parser')
        metadatas = self._scrape_most_recent_article_metadatas(soup)
        _log.debug('Found %s metadatas from most recent page', len(metadatas))

        articles = self._crawl_uncrawled_metadatas(metadatas)
        return articles

    def _get_tokushu_show_more_button(self) -> FirefoxWebElement:
        """Gets the show more button element from the Tokushu page.

        Assumes the class web driver is already set to the Tokushu page.
        """
        main = self._web_driver.find_element_by_id(self._MAIN_ID)
        footers = main.find_elements_by_class_name(
            self._SHOW_MORE_BUTTON_FOOTER_CLASS
        )
        if len(footers) != 1:
            self._parsing_error_handler(
                'Found {} "footer" tags with class "{}" instead of 1 at page '
                '"{}"'.format(
                    len(footers), self._SHOW_MORE_BUTTON_FOOTER_CLASS,
                    self._web_driver.current_url
                )
            )

        buttons = footers[0].find_elements_by_class_name(
            self._SHOW_MORE_BUTTON_CLASS
        )
        if len(buttons) != 1:
            self._parsing_error_handler(
                'Found {} "button" tags with class "{}" instead of 1 at page '
                '{}'.format(
                    len(footers), self._SHOW_MORE_BUTTON_CLASS,
                    self._web_driver.current_url
                )
            )

        return buttons[0]

    def _click_tokushu_show_more(self, show_more_clicks: int) -> None:
        """Clicks the Tokushu page show more button a number of times.

        Assumes the class web driver is already set to the Tokushu page.

        Args:
            show_more_clicks: Number of times to click the show more button on
                the Tokushu page.

        Raises:
            NoSuchElementException: Web driver was unable to find an element
                while searching for the show more button.
        """
        if show_more_clicks < 1:
            return

        show_more_button = self._get_tokushu_show_more_button()
        for i in reversed(range(show_more_clicks)):
            _log.debug('Clicking show more button. %s clicks remaining.', i)
            show_more_button.click()
            time.sleep(4)

        wait_max = 60
        while wait_max > 0:
            try:
                self._web_driver.find_element_by_class_name(
                    self._LOADING_CLASS_NAME
                )
            except NoSuchElementException:
                break
            _log.debug(
                'Loading element found. Will wait %s more seconds', wait_max
            )
            time.sleep(1)
            wait_max -= 1

        if wait_max == 0:
            self._parsing_error_handler(
                'Elements still loading at page "{}" after timeout'.format(
                    self._web_driver.current_url
                )
            )

    def crawl_tokushu(self, show_more_clicks: int = 0) -> List[JpnArticle]:
        """Gets all not yet crawled articles from the 'Tokushu' page.

        Args:
            show_more_clicks: Number of times to click the button for showing
                more articles on the Tokushu page before starting the crawl.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            Tokushu page.
        """
        self._web_driver.get(self._TOKUSHU_PAGE_URL)
        if self._web_driver.title != self._TOKUSHU_PAGE_TITLE:
            utils.log_and_raise(
                _log, CannotAccessPageError,
                'Tokushu page title ({}) at url ({}) does not match '
                'expected title ({})'.format(
                    self._web_driver.title, self._web_driver.current_url,
                    self._TOKUSHU_PAGE_TITLE
                )
            )

        time.sleep(7)  # Wait for page to load
        self._click_tokushu_show_more(show_more_clicks)
        soup = BeautifulSoup(self._web_driver.page_source, 'html.parser')

        metadatas = self._scrape_tokushu_article_metadatas(soup)
        _log.debug('Found %s metadatas from Tokushu page', len(metadatas))

        articles = self._crawl_uncrawled_metadatas(metadatas)
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
        article_tag = self._html_helper.strip_ruby_tags(article_tags[0])

        return self._parse_article(article_tag, url)
