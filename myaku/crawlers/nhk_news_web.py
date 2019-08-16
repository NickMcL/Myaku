"""Crawler for the NHK News Web website."""

import logging
import time
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.webelement import FirefoxWebElement

import myaku.utils as utils
from myaku.crawlers.abc import Crawl, CrawlerABC, CrawlGenerator
from myaku.datatypes import JpnArticle, JpnArticleMetadata
from myaku.errors import CannotAccessPageError, HtmlParsingError

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class NhkNewsWebCrawler(CrawlerABC):
    """Crawls articles from the NHK News Web website."""
    MAX_MOST_RECENT_SHOW_MORE_CLICKS = 9
    MAX_DOUGA_SHOW_MORE_CLICKS = 8

    _SOURCE_NAME = 'NHK News Web'
    __SOURCE_BASE_URL = 'https://www3.nhk.or.jp'

    # If these article metadata fields are equivalent between two NHK News Web
    # article metadatas, the articles can be treated as equivalent
    __ARTICLE_METADATA_CMP_FIELDS = [
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

    _TIME_TAG_DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

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
        super().__init__(True, timeout)

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
        section_text = utils.html.parse_valid_child_text(tag, False)
        if section_text is not None:
            return section_text

        text_sections = []
        for child in tag.children:
            # Skip text around child tags such as '\n'
            if child.name is None:
                continue

            child_text = utils.html.parse_valid_child_text(child, False)
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
            utils.log_and_raise(
                _log, HtmlParsingError,
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
        self, article_tag: Tag, article_metadata: JpnArticleMetadata
    ) -> JpnArticle:
        """Parses data from NHK article HTML.

        Args:
            article_tag: Tag containing NHK article HTML.
            article_metadata: Metadata for the article listed on the top level
                summary pages.

        Returns:
            Article object containing the parsed data from article_tag.
        """
        article_data = JpnArticle()
        article_data.metadata = JpnArticleMetadata(
            title=utils.html.parse_text_from_desendant_by_class(
                article_tag, self._ARTICLE_TITLE_CLASS, 'span'
            ),
            source_url=article_metadata.source_url,
            source_name=self.SOURCE_NAME,
            scraped_datetime=datetime.utcnow(),
            publication_datetime=utils.html.parse_time_desendant(
                article_tag, self._TIME_TAG_DATETIME_FORMAT, True
            ),
        )

        body_text = self._parse_body_text(article_tag)
        article_data.full_text = '{}\n\n{}'.format(
            article_data.metadata.title, body_text
        )
        article_data.alnum_count = utils.get_alnum_count(
            article_data.full_text
        )
        article_data.has_video = self._contains_news_video(article_tag)

        return article_data

    def _select_main(self, soup: BeautifulSoup) -> Tag:
        """Selects the main tag from the given BeautifulSoup html.

        Args:
            soup: BeautifulSoup object with parsed html.

        Returns:
            The selected main tag.
        """
        main = soup.find(id=self._MAIN_ID)
        if main is None:
            utils.log_and_raise(
                _log, HtmlParsingError,
                'Could not find "main" tag in page "{}"'.format(soup)
            )

        return main

    def _scrape_summary_page_list_articles(
        self, page_soup: BeautifulSoup
    ) -> List[JpnArticleMetadata]:
        """Scrapes metadata from the article list of a summary page soup.

        Does not scrape the metadata from articles in header sections at the
        top of the summary page.

        Args:
            page_soup: BeautifulSoup for the summary page.

        Returns:
            A list of the article metadatas for the articles linked to in the
            article list on the summary page.
        """
        list_article_tags = []
        main = self._select_main(page_soup)
        article_uls = utils.html.select_desendants_by_class(
            main, self._SUMMARY_ARTICLE_LIST_CLASS, 'ul'
        )
        article_uls = self._filter_out_exclusions(article_uls)
        for ul in article_uls:
            list_article_tags.extend(ul.contents)
        _log.debug('Found %s list article tags', len(list_article_tags))

        metadatas = []
        for tag in list_article_tags:
            metadatas.append(
                JpnArticleMetadata(
                    title=utils.html.parse_text_from_desendant_by_class(
                        tag, self._TITLE_CLASS, 'em'
                    ),
                    publication_datetime=utils.html.parse_time_desendant(
                        tag, self._TIME_TAG_DATETIME_FORMAT, True
                    ),
                    source_url=utils.html.parse_link_desendant(tag),
                    source_name=self.SOURCE_NAME,
                )
            )

        return metadatas

    def _scrape_summary_page_header_articles(
        self, page_soup: BeautifulSoup
    ) -> List[JpnArticleMetadata]:
        """Scrapes metadata from the header articles of a summary page soup.

        Does not scrape the metadata from articles outside of the header
        sections of the summary page.

        Args:
            page_soup: BeautifulSoup for the summary page.

        Returns:
            A list of the article metadatas for the articles linked to in the
            header sections of the summary page.
        """
        main = self._select_main(page_soup)
        header_article_tags = utils.html.parse_descendant_by_class(
            main, self._SUMMARY_HEADER_DIV_CLASS, 'div', True
        )
        header_article_tags = self._filter_out_exclusions(header_article_tags)
        _log.debug('Found %s header article divs', len(header_article_tags))

        metadatas = []
        for tag in header_article_tags:
            metadatas.append(
                JpnArticleMetadata(
                    title=utils.html.parse_text_from_desendant_by_class(
                        tag, self._TITLE_CLASS, 'em'
                    ),
                    publication_datetime=utils.html.parse_time_desendant(
                        tag, self._TIME_TAG_DATETIME_FORMAT, True
                    ),
                    source_url=utils.html.parse_link_desendant(tag, 0, 2),
                    source_name=self.SOURCE_NAME,
                )
            )

        return metadatas

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
        metadatas = self._scrape_summary_page_list_articles(page_soup)
        if has_header_sections:
            metadatas.extend(
                self._scrape_summary_page_header_articles(page_soup)
            )

        return metadatas

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
            utils.log_and_raise(
                _log, HtmlParsingError,
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
            utils.log_and_raise(
                _log, HtmlParsingError,
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
            utils.log_and_raise(
                _log, HtmlParsingError,
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
    ) -> CrawlGenerator:
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

    def crawl_most_recent(self, show_more_clicks: int = 0) -> CrawlGenerator:
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

    def crawl_douga(self, show_more_clicks: int = 0) -> CrawlGenerator:
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

    def crawl_news_up(self, show_more_clicks: int = 0) -> CrawlGenerator:
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

    def crawl_tokushu(self, show_more_clicks: int = 0) -> CrawlGenerator:
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

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent NHK News Web articles.

        The crawls cover the latest 200 articles posted to the site. NHK News
        Web typically posts that many articles in 36-48 hours.

        Additionally, the latest 100 video articles, 20 News Up articles, and
        20 Tokushu articles are also covered by the crawls.

        An article will not be crawled again if it has been previously crawled
        during any previous crawl recorded in the MyakuDb.
        """
        crawls = []
        crawls.append(
            Crawl(
                name='Most Recent',
                crawl_gen=self.crawl_most_recent(
                    self.MAX_MOST_RECENT_SHOW_MORE_CLICKS
                )
            )
        )
        crawls.append(
            Crawl(
                name='Douga',
                crawl_gen=self.crawl_douga(4)
            )
        )
        crawls.append(
            Crawl(
                name='News Up',
                crawl_gen=self.crawl_news_up()
            )
        )
        crawls.append(
            Crawl(
                name='Tokushu',
                crawl_gen=self.crawl_tokushu()
            )
        )

        return crawls

    def crawl_article(
        self, article_url: str, article_metadata: JpnArticleMetadata
    ) -> JpnArticle:
        """Crawls an NHK News Web article.

        Args:
            article_url: Url to a page containing an NHK News Web article.
            article_metadata: Metadata for the article listed on the top level
                summary pages.

        Returns:
            Article object with the parsed data from the article + the given
            metadata.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            HtmlParsingError: An error occurred while parsing the article.
        """
        soup = self._get_url_html_soup(article_url)
        article_tags = soup.find_all(
            'section', class_=self._ARTICLE_TAG_CLASS
        )
        if len(article_tags) != 1:
            utils.log_and_raise(
                _log, HtmlParsingError,
                'Found %s article sections instead of 1 for url "%s"',
                len(article_tags), article_url
            )

        # Ruby tags tend to mess up Japanese processing, so strip all of them
        # from the HTML document right away.
        article_tag = utils.html.strip_ruby_tags(article_tags[0])

        return self._parse_article(article_tag, article_metadata)
