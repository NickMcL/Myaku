"""Crawler for the NHK News Web website."""

import logging
import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from myaku import utils
from myaku.crawlers.abc import Crawl, CrawlerABC, CrawlGenerator
from myaku.datatypes import JpnArticle
from myaku.errors import HtmlParsingError
from myaku.utils import html

_log = logging.getLogger(__name__)


@utils.add_method_debug_logging
class NhkNewsWebCrawler(CrawlerABC):
    """Crawls articles from the NHK News Web website."""
    # Nhk News Web only makes these max numbers of pages of history available
    # for the Most Recent and Douga pages.
    MAX_MOST_RECENT_PAGES = 10
    MAX_DOUGA_PAGES = 10

    SOURCE_NAME = 'NHK News Web'
    __SOURCE_BASE_URL = 'https://www3.nhk.or.jp/news/'

    _REQUIRES_WEB_DRIVER = False

    _MOST_RECENT_JSON_URL_PREFIX = 'https://www3.nhk.or.jp/news/json16/new'
    _DOUGA_JSON_URL_PREFIX = 'https://www3.nhk.or.jp/news/json16/newmovie'
    _NEWS_UP_JSON_URL_PREFIX = 'https://www3.nhk.or.jp/news/json16/arch_newsup'
    _TOKUSHU_JSON_URL_PREFIX = (
        'https://www3.nhk.or.jp/news/json16/tokushu/new_tokushu'
    )

    _JSON_PREFIX_FIRST_PAGE_MAP = {
        _NEWS_UP_JSON_URL_PREFIX:
            'https://www3.nhk.or.jp/news/json16/newsup.json',
    }

    _NHK_JSON_DATETIME_FORMAT = '%a, %d %b %Y %H:%M:%S %z'

    _HAS_VIDEO_REGEX = re.compile(r"^\s*video\s*:\s*'.+',?\s*$", re.M)

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
    def _SOURCE_BASE_URL(self) -> str:
        """The base url for accessing the source."""
        return self.__SOURCE_BASE_URL

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
        section_text = html.parse_valid_child_text(tag, False)
        if section_text is not None:
            return section_text

        text_sections = []
        for child in tag.children:
            # Skip text around child tags such as '\n'
            if child.name is None:
                continue

            child_text = html.parse_valid_child_text(child, False)
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

    def _has_news_video(self, article_page_soup: BeautifulSoup) -> bool:
        """Returns True if there is a news video on the article page."""
        main_tag = html.select_descendants_by_tag(
            article_page_soup, 'main', 1
        )
        article_json_tag = html.select_descendants_by_tag(
            main_tag, 'script', 1
        )

        article_json_text = article_json_tag.string
        if article_json_text is None:
            utils.log_and_raise(
                _log, HtmlParsingError,
                'No text in article JSON script tag in: "{}"'.format(main_tag)
            )

        return re.search(self._HAS_VIDEO_REGEX, article_json_text) is not None

    def _parse_article(
        self, article_tag: Tag, article_meta: JpnArticle
    ) -> JpnArticle:
        """Parses data from NHK article HTML.

        Args:
            article_tag: Tag containing NHK article HTML.
            article_meta: Metadata for the article listed on the top level
                summary pages.

        Returns:
            Article object containing the parsed data from article_tag.
        """
        article = article_meta
        article.title = html.parse_text_from_descendant_by_class(
            article_tag, self._ARTICLE_TITLE_CLASS, 'span'
        )
        body_text = self._parse_body_text(article_tag)
        article.full_text = '{}\n\n{}'.format(article.title, body_text)
        article.alnum_count = utils.get_alnum_count(article.full_text)

        return article

    @utils.skip_method_debug_logging
    def _get_summary_json_url(self, url_prefix: str, page_num: int) -> str:
        """Gets the url for a page of the JSON for a summary page."""
        if page_num == 1 and url_prefix in self._JSON_PREFIX_FIRST_PAGE_MAP:
            return self._JSON_PREFIX_FIRST_PAGE_MAP[url_prefix]
        return '{}_{}.json'.format(url_prefix, str(page_num).zfill(3))

    @utils.skip_method_debug_logging
    def _parse_json_datetime_str(self, dt_str: str) -> datetime:
        """Parses a datetime string from NHK article metadata json.

        The datetime strings in NHK article metadata json are stored as JST, so
        this function also converts the datetime to UTC.
        """
        try:
            dt = datetime.strptime(dt_str, self._NHK_JSON_DATETIME_FORMAT)
        except ValueError:
            utils.log_and_raise(
                _log, ValueError,
                'Failed to parse NHK json datetime "{}" using format '
                '"{}"'.format(
                    dt_str, self._NHK_JSON_DATETIME_FORMAT
                )
            )

        return utils.convert_jst_to_utc(dt)

    def _crawl_summary_page_json(
        self, json_url_prefix: str, max_pages_to_crawl
    ) -> List[JpnArticle]:
        """Crawls summary page JSON to get the article metadata for the page.

        Args:
            json_url_prefix: Url prefix for the summary page JSON urls to
                crawl. Will append a page number suffix to this url to make the
                full urls to crawl.
            max_pages_to_crawl: Max number of pages of the JSON for the summary
                page to crawl. If the total available pages is less than this
                number, will crawl all available pages.

        Returns:
            A list of all of the article metadata in the JSON at the urls with
            the given prefix.
        """
        page_num = 1
        metadatas = []
        while True:
            json_url = self._get_summary_json_url(json_url_prefix, page_num)
            json = self._get_url_json(json_url)
            for i, article in enumerate(json['channel']['item']):
                pub_datetime_str = article['pubDate']
                pub_datetime = self._parse_json_datetime_str(pub_datetime_str)
                metadata = JpnArticle(
                    title=article['title'],
                    publication_datetime=pub_datetime,
                    last_updated_datetime=pub_datetime,
                    source_url=article['link'],
                    source_name=self.SOURCE_NAME,
                )
                metadatas.append(metadata)

            _log.debug(
                'Found %s metadatas from JSON url "%s"', i + 1, json_url
            )
            if page_num >= max_pages_to_crawl:
                return metadatas

            # Some summary pages like News Up do not have the hasNext field for
            # their first page, but they actually do always have a next page
            # after the first in that case.
            hasNext = json['channel'].get('hasNext')
            if not (page_num == 1 and hasNext is None) and not hasNext:
                _log.debug(
                    'Only %s pages of JSON were available for url prefix '
                    '"%s", so max of %s pages was not reached',
                    page_num, json_url_prefix, max_pages_to_crawl
                )
                return metadatas

            page_num += 1

    def _crawl_summary_page(
        self, json_url_prefix: str, max_pages_to_crawl: int
    ) -> CrawlGenerator:
        """Crawls all not yet crawled articles for a summary page.

        Args:
            json_url_prefix: Url prefix for the summary page JSON urls to
                crawl. Will append a page number suffix to this url to make the
                full urls to crawl.
            max_pages_to_crawl: Max number of pages of the JSON for the summary
                page to crawl. If the total available pages is less than this
                number, will crawl all available pages.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the summary page each call.
        """
        metadatas = self._crawl_summary_page_json(
            json_url_prefix, max_pages_to_crawl
        )
        _log.debug(
            'Found %s metadatas from "%s" JSON urls',
            len(metadatas), json_url_prefix
        )

        yield from self._crawl_uncrawled_articles(metadatas)

    def crawl_most_recent(self, pages_to_crawl: int = 1) -> CrawlGenerator:
        """Gets all not yet crawled articles from the 'Most Recent' page.

        Args:
            pages_to_crawl: Number of pages to crawl of the Most Recent
                page. Each page is usually 20 articles.

                If this number is higher than the total number of pages
                available to crawl, will crawl all available pages instead.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the Most Recent page each call.
        """
        yield from self._crawl_summary_page(
            self._MOST_RECENT_JSON_URL_PREFIX, pages_to_crawl
        )

    def crawl_douga(self, pages_to_crawl: int = 1) -> CrawlGenerator:
        """Gets all not yet crawled articles from the 'Douga' page.

        Args:
            pages_to_crawl: Number of pages to crawl of the Douga page. Each
                page is usually 20 articles.

                If this number is higher than the total number of pages
                available to crawl, will crawl all available pages instead.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the Douga page each call.
        """
        yield from self._crawl_summary_page(
            self._DOUGA_JSON_URL_PREFIX, pages_to_crawl
        )

    def crawl_news_up(self, pages_to_crawl: int = 1) -> CrawlGenerator:
        """Gets all not yet crawled articles from the 'News Up' page.

        Args:
            pages_to_crawl: Number of pages to crawl of the News Up page. Each
                page is usually 20 articles.

                If this number is higher than the total number of pages
                available to crawl, will crawl all available pages instead.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the News Up page each call.
        """
        yield from self._crawl_summary_page(
            self._NEWS_UP_JSON_URL_PREFIX, pages_to_crawl
        )

    def crawl_tokushu(self, pages_to_crawl: int = 1) -> CrawlGenerator:
        """Gets all not yet crawled articles from the 'Tokushu' page.

        Args:
            pages_to_crawl: Number of pages to crawl of the Tokushu page. Each
                page is usually 20 articles.

                If this number is higher than the total number of pages
                available to crawl, will crawl all available pages instead.

        Returns:
            A generator that will yield the data for a not previously crawled
            article from the Tokushu page each call.
        """
        yield from self._crawl_summary_page(
            self._TOKUSHU_JSON_URL_PREFIX, pages_to_crawl
        )

    def get_crawls_for_most_recent(self) -> List[Crawl]:
        """Gets a list of Crawls for the most recent NHK News Web articles.

        An article will not be crawled again if it has been previously crawled
        during any previous crawl recorded in the MyakuDb.

        Only crawls the News Up and Tokushu sections of the site because
        articles in the Most Recent and Douga sections are often removed from
        the site as soon as 1-2 weeks later, so they can't be stored for long.
        """
        crawls = []
        news_up_crawl = Crawl(
            self.SOURCE_NAME, 'News Up', self.crawl_news_up()
        )
        crawls.append(news_up_crawl)

        tokushu_crawl = Crawl(
            self.SOURCE_NAME, 'Tokushu', self.crawl_tokushu()
        )
        crawls.append(tokushu_crawl)

        return crawls

    def crawl_article(
        self, article_url: str, article_meta: JpnArticle
    ) -> JpnArticle:
        """Crawls an NHK News Web article.

        Args:
            article_url: Url to a page containing an NHK News Web article.
            article_meta: Metadata for the article listed on the top level
                summary pages.

        Returns:
            Article object with the parsed data from the article + the given
            metadata.

        Raises:
            HTTPError: An error occurred making a GET request to url.
            HtmlParsingError: An error occurred while parsing the article.
        """
        soup = self._get_url_html_soup(article_url)
        article_tag = html.select_descendants_by_class(
            soup, self._ARTICLE_TAG_CLASS, 'section', 1
        )

        # Ruby tags tend to mess up Japanese processing, so strip all of them
        # from the HTML document right away.
        article_tag = html.strip_ruby_tags(article_tag)

        article = self._parse_article(article_tag, article_meta)
        article.has_video = self._has_news_video(soup)

        return article
