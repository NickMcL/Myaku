"""Crawler classes for scraping text articles for the web."""

import functools
import logging
import time
from datetime import datetime
from random import random
from typing import Generator, List, Optional
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
    MAX_MOST_RECENT_SHOW_MORE_CLICKS = 9
    MAX_DOUGA_SHOW_MORE_CLICKS = 9

    _SOURCE_NAME = 'NHK News Web'
    _SOURCE_BASE_URL = 'https://www3.nhk.or.jp'

    # If these article metadata fields are equivalent between two NHK News Web
    # article metadatas, the articles can be treated as equivalent
    _ARTICLE_METADATA_CMP_FIELDS = [
        'source_name',
        'title',
        'publication_datetime'
    ]

    _PAGE_LOAD_WAIT_TIME = 6  # in seconds

    _MOST_RECENT_PAGE_URL = 'https://www3.nhk.or.jp/news/catnew.html'
    _DOUGA_PAGE_URL = 'https://www3.nhk.or.jp/news/movie.html'
    _TOKUSHU_PAGE_URL = 'https://www3.nhk.or.jp/news/tokushu/'
    _NEWS_UP_PAGE_URL = 'https://www3.nhk.or.jp/news/netnewsup/'
    _PAGE_TITLES = {
        _MOST_RECENT_PAGE_URL: '速報・新着ニュース一覧｜NHK NEWS WEB',
        _DOUGA_PAGE_URL: '動画ニュース一覧｜NHK NEWS WEB',
        _TOKUSHU_PAGE_URL: '特集一覧｜NHK NEWS WEB',
        _NEWS_UP_PAGE_URL: 'News Up一覧｜NHK NEWS WEB',
    }

    _MAIN_ID = 'main'
    _TITLE_CLASS = 'title'
    _NEWS_VIDEO_ID = 'news_video'
    _EXCLUDE_ARTICLE_CLASSES = {
        'module--cameramanseye',
    }

    _SHOW_MORE_BUTTON_CLASS = 'button'
    _SHOW_MORE_BUTTON_FOOTER_CLASS = 'button-more'
    _LOADING_CLASS_NAME = 'loading'

    _SUMMARY_HEADER_DIV_CLASS = 'content--header'
    _SUMMARY_ARTICLE_LIST_CLASS = 'content--list'

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

    def _contains_news_video(self, tag: Tag) -> bool:
        """Returns True if an NHK news video is in the tag's descendants."""
        video_tag = tag.find(id=self._NEWS_VIDEO_ID)
        if video_tag is None:
            return False
        return True

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
        article_data.has_video = self._contains_news_video(article_tag)

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

    def _scrape_summary_page_article_metadatas(
        self, page_soup: BeautifulSoup, has_header_sections: bool = False
    ) -> List[JpnArticleMetadata]:
        """Scrapes all article metadata from a summary page soup.

        Args:
            page_soup: BeautifulSoup for the summary page.
            has_header_sections: If True, will look for header sections
                containing article metadatas on the summary page as well. If
                False, will only look for summary lists containing article
                metadatas on the summary page.

        Returns:
            A list of the metadatas for the articles linked to on the summary
            page.
        """
        article_metadata_tags = []
        main = self._parse_main(page_soup)
        article_uls = self._html_helper.parse_descendant_by_class(
            main, 'ul', self._SUMMARY_ARTICLE_LIST_CLASS, True
        )
        article_uls = self._filter_out_exclusions(article_uls)
        for ul in article_uls:
            article_metadata_tags.extend(ul.contents)
        _log.debug(
            'Found %s article metadata tags', len(article_metadata_tags)
        )

        if has_header_sections:
            header_divs = self._html_helper.parse_descendant_by_class(
                main, 'div', self._SUMMARY_HEADER_DIV_CLASS, True
            )
            header_divs = self._filter_out_exclusions(header_divs)
            _log.debug('Found %s header divs', len(header_divs))
            article_metadata_tags.extend(header_divs)

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

    def _filter_out_exclusions(self, tags: List[Tag]) -> List[Tag]:
        """Filters out tags that are known exclusions for parsing.

        Does not modify the given tags list.

        Args:
            tags: List of tags to check if known exlusion.

        Returns:
            A new list containing only the tags from the given list that were
            not known exclusions.
        """
        filtered_tags = []
        for tag in tags:
            parents = tag.find_parents(
                'article', class_=self._EXCLUDE_ARTICLE_CLASSES
            )
            if len(parents) != 0:
                _log.debug(
                    'Filtered out "%s" tag with excluded parent "article" tag '
                    'with classes %s', tag.name, parents[0].attrs['class']
                )
                continue

            if (tag.name is not None and tag.name == 'article'
                    and 'class' in tag.attrs
                    and (set(tag.attrs['class']) &
                         self._EXCLUDE_ARTICLE_CLASSES)):
                _log.debug(
                    'Filtered out excluded "%s" tag with classes %s',
                    tag.name, tag.attrs['class']
                )
                continue

            filtered_tags.append(tag)

        return filtered_tags

    def _crawl_uncrawled_metadatas(
        self, metadatas: List[JpnArticleMetadata]
    ) -> Generator[JpnArticle, None, None]:
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
            return

        crawl_urls = [m.source_url for m in uncrawled_metadatas]
        crawl_urls = self._make_rel_urls_absolute(crawl_urls)
        with ReibunDb() as db:
            for i, crawl_url in enumerate(crawl_urls):
                sleep_time = (random() * 4) + 3
                _log.debug(
                    'Sleeping for %s seconds, then scrape %s / %s',
                    sleep_time, i + 1, len(crawl_urls))
                time.sleep(sleep_time)

                article = self.scrape_article(crawl_url)
                db.write_crawled([article.metadata])

                yield article

    def _get_show_more_button(self) -> FirefoxWebElement:
        """Gets the show more button element from the page.

        Assumes the class web driver is already set to a page with a show more
        button.
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

    def _click_show_more(self, show_more_clicks: int) -> None:
        """Clicks the show more button in the page a number of times.

        Assumes the class web driver is already set to a page with a show more
        button to click.

        Args:
            show_more_clicks: Number of times to click the show more button on
                the page.

        Raises:
            NoSuchElementException: Web driver was unable to find an element
                while searching for the show more button.
        """
        if show_more_clicks < 1:
            return

        show_more_button = self._get_show_more_button()
        for i in reversed(range(show_more_clicks)):
            _log.debug('Clicking show more button. %s clicks remaining.', i)
            show_more_button.click()
            time.sleep(self._PAGE_LOAD_WAIT_TIME)

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

    def _web_driver_get_url(self, url: str) -> None:
        """Gets the url with class web driver."""
        self._web_driver.get(url)
        time.sleep(self._PAGE_LOAD_WAIT_TIME)
        if (self._web_driver.title != self._PAGE_TITLES[url]):
            utils.log_and_raise(
                _log, CannotAccessPageError,
                'Page title ({}) at url ({}) does not match expected title '
                '({})'.format(
                    self._web_driver.title, self._web_driver.current_url,
                    self._PAGE_TITLES[url]
                )
            )

    def _crawl_summary_page(
        self, page_url: str, show_more_clicks: int,
        has_header_sections: bool = False
    ) -> Generator[JpnArticle, None, None]:
        """Gets all not yet crawled articles from given summary page.

        Args:
            page_url: The url of the summary page.
            show_more_clicks: Number of times to click the button for showing
                more articles on the summary page before starting the crawl.
            has_header_sections: Whether or not the summary page has header
                sections for featured articles in addition to its article
                summary list.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            summary page.
        """
        self._web_driver_get_url(page_url)
        self._click_show_more(show_more_clicks)

        soup = BeautifulSoup(self._web_driver.page_source, 'html.parser')
        metadatas = self._scrape_summary_page_article_metadatas(
            soup, has_header_sections
        )
        _log.debug(
            'Found %s metadatas from %s page',
            len(metadatas), self._web_driver.title
        )

        yield from self._crawl_uncrawled_metadatas(metadatas)

    def crawl_most_recent(
        self, show_more_clicks: int = 0
    ) -> Generator[JpnArticle, None, None]:
        """Gets all not yet crawled articles from the 'Most Recent' page.

        Args:
            show_more_clicks: Number of times to click the button for showing
                more articles on the Most Recent page before starting the
                crawl.

                Can only be clicked a maximum of
                MAX_MOST_RECENT_SHOW_MORE_CLICKS times because the show more
                button is removed from the Most Recent page after that many
                clicks.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            Most Recent page.
        """
        if show_more_clicks > self.MAX_MOST_RECENT_SHOW_MORE_CLICKS:
            raise ValueError(
                'The Most Recent page show more button can only be clicked '
                'up to {} times, but show_more_clicks is {}'.format(
                    self.MAX_MOST_RECENT_SHOW_MORE_CLICKS, show_more_clicks
                )
            )

        yield from self._crawl_summary_page(
            self._MOST_RECENT_PAGE_URL, show_more_clicks
        )

    def crawl_douga(
        self, show_more_clicks: int = 0
    ) -> Generator[JpnArticle, None, None]:
        """Gets all not yet crawled articles from the 'Douga' page.

        Args:
            show_more_clicks: Number of times to click the button for showing
                more articles on the Douga page before starting the crawl.

                Can only be clicked a maximum of MAX_DOUGA_SHOW_MORE_CLICKS
                times because the show more button is removed from the Douga
                page after that many clicks.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            Douga page.
        """
        if show_more_clicks > self.MAX_DOUGA_SHOW_MORE_CLICKS:
            raise ValueError(
                'The Douga page show more button can only be clicked '
                'up to {} times, but show_more_clicks is {}'.format(
                    self.MAX_DOUGA_SHOW_MORE_CLICKS, show_more_clicks
                )
            )

        yield from self._crawl_summary_page(
            self._DOUGA_PAGE_URL, show_more_clicks
        )

    def crawl_news_up(
        self, show_more_clicks: int = 0
    ) -> Generator[JpnArticle, None, None]:
        """Gets all not yet crawled articles from the 'News Up' page.

        Args:
            show_more_clicks: Number of times to click the button for showing
                more articles on the News Up page before starting the crawl.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            News Up page.
        """
        yield from self._crawl_summary_page(
            self._NEWS_UP_PAGE_URL, show_more_clicks, True
        )

    def crawl_tokushu(
        self, show_more_clicks: int = 0
    ) -> Generator[JpnArticle, None, None]:
        """Gets all not yet crawled articles from the 'Tokushu' page.

        Args:
            show_more_clicks: Number of times to click the button for showing
                more articles on the Tokushu page before starting the crawl.

        Returns:
            A list of all of the not yet crawled articles linked to from the
            Tokushu page.
        """
        yield from self._crawl_summary_page(
            self._TOKUSHU_PAGE_URL, show_more_clicks, True
        )

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
